"""CLI for criterion-wise evidence-grounded LLM screening runs."""

from __future__ import annotations

import argparse
import atexit
import sys
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from screening.cli.run_direct_llm import (
    DEFAULT_METHOD as DIRECT_METHOD,
    DirectLlmRuntimeError,
    ExampleProcessingResult,
    OpenAICompatibleClient,
    RunLockError,
    _acquire_run_lock,
    _build_client,
    _default_run_id,
    _load_processed_ids,
    _make_error_record,
    _print_progress,
    _release_run_lock,
    _select_examples_by_ids,
    _select_provider,
    _validate_unique_prediction_records,
)
from screening.config import load_experiment_defaults, load_provider_configs
from screening.evaluation.decision import evaluate_predictions
from screening.evaluation.tables import update_automation_readiness_table
from screening.io_utils import (
    append_jsonl,
    format_validation_errors,
    parse_json_response,
    read_jsonl,
    read_model_jsonl,
    read_prediction_jsonl,
    write_json,
    write_model_jsonl,
)
from screening.paths import results_root
from screening.pipeline.aggregation import (
    aggregate_csmed_criterion_judgments,
    apply_aggregation_to_prediction,
)
from screening.prompts.criterion_wise import (
    CRITERIA_MODE_FIXED_SPECS,
    CRITERIA_MODE_HYBRID_SPECS_RAW,
    CRITERIA_MODE_RAW,
    CRITERIA_MODES,
    build_criterion_wise_prompt,
    get_criterion_wise_prompt_spec,
)
from screening.run_index import update_run_index
from screening.schemas import (
    BaseScreeningPrediction,
    CriterionOnlyResponse,
    Decision,
    InputSetting,
    RawResponseMetadata,
    RunMetadata,
    ScreeningExample,
    ScreeningPrediction,
)
from pydantic import ValidationError

DEFAULT_METHOD = "criterion_wise_evidence_grounded"
DEFAULT_TOP_K = 3
PREDICTION_SCHEMA = "criterion_wise_minimal_v1"
AGGREGATION_POLICY = "conservative_binary_with_needs_review_flag"
DEFAULT_PROMPT_BY_CRITERIA_MODE = {
    CRITERIA_MODE_RAW: "v3",
    CRITERIA_MODE_FIXED_SPECS: "fixed_v1",
    CRITERIA_MODE_HYBRID_SPECS_RAW: "hybrid_v1",
}


def _resolve_prompt_version(
    explicit_version: str | None,
    defaults: Any,
    *,
    criteria_mode: str,
) -> str:
    if explicit_version:
        candidate = explicit_version
    elif criteria_mode == CRITERIA_MODE_RAW and defaults and defaults.prompt_version:
        candidate = defaults.prompt_version
    else:
        candidate = DEFAULT_PROMPT_BY_CRITERIA_MODE[criteria_mode]

    try:
        spec = get_criterion_wise_prompt_spec(candidate)
    except ValueError:
        candidate = DEFAULT_PROMPT_BY_CRITERIA_MODE[criteria_mode]
        spec = get_criterion_wise_prompt_spec(candidate)
    if spec.criteria_mode != criteria_mode:
        raise ValueError(
            f"prompt version {candidate} is registered for criteria mode "
            f"{spec.criteria_mode}, not {criteria_mode}"
        )
    return candidate


def _build_output_paths(
    *,
    examples: list[ScreeningExample],
    output_dir: str | None,
    run_id: str,
) -> dict[str, Path]:
    benchmark = examples[0].benchmark
    split = examples[0].split
    if output_dir:
        pred_dir = Path(output_dir)
    else:
        pred_dir = results_root / "preds" / benchmark / split / DEFAULT_METHOD / run_id
    log_dir = results_root / "logs" / benchmark / split / DEFAULT_METHOD / run_id
    metric_path = results_root / "metrics" / benchmark / split / DEFAULT_METHOD / f"{run_id}.json"
    return {
        "prediction_dir": pred_dir,
        "predictions": pred_dir / "predictions.jsonl",
        "errors": pred_dir / "errors.jsonl",
        "evaluation_examples": pred_dir / "evaluation_examples.jsonl",
        "selected_evidence": pred_dir / "selected_evidence.jsonl",
        "log_dir": log_dir,
        "metadata": log_dir / "run_metadata.json",
        "metrics": metric_path,
    }


def _prediction_from_criterion_only_response(
    *,
    example: ScreeningExample,
    raw_response: str,
    provider: str,
    model: str,
    request_id: str | None,
    metadata: dict[str, Any],
    expected_criterion_ids: list[str] | None = None,
) -> tuple[ScreeningPrediction | None, dict[str, Any], list[str]]:
    parsed, parse_errors = parse_json_response(raw_response)
    response_metadata = RawResponseMetadata(
        raw_response=raw_response,
        parsed_json=parsed,
        validation_errors=parse_errors.copy(),
        provider=provider,
        model=model,
        request_id=request_id,
        metadata=metadata,
    )
    if parsed is None:
        return None, response_metadata.model_dump(mode="json"), list(response_metadata.validation_errors)

    try:
        payload = CriterionOnlyResponse.model_validate(parsed)
        if expected_criterion_ids:
            expected = set(expected_criterion_ids)
            actual = set(payload.criterion_judgments)
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            if missing or extra:
                details: list[str] = []
                if missing:
                    details.append("missing criterion ids: " + ", ".join(missing))
                if extra:
                    details.append("unexpected criterion ids: " + ", ".join(extra))
                response_metadata.validation_errors.extend(details)
                return (
                    None,
                    response_metadata.model_dump(mode="json"),
                    list(response_metadata.validation_errors),
                )
        prediction = ScreeningPrediction(
            example_id=example.example_id,
            decision=Decision.include,
            criterion_judgments={
                criterion_id: {
                    "text": judgment.text,
                    "judgment": judgment.judgment,
                }
                for criterion_id, judgment in payload.criterion_judgments.items()
            },
        )
    except ValidationError as exc:
        response_metadata.validation_errors.extend(format_validation_errors(exc))
        return None, response_metadata.model_dump(mode="json"), list(response_metadata.validation_errors)

    prediction.raw_response_metadata = response_metadata
    return prediction, response_metadata.model_dump(mode="json"), list(response_metadata.validation_errors)


def _invoke_one_example(
    *,
    example: ScreeningExample,
    input_setting: InputSetting,
    prompt_version: str,
    provider_config: Any,
    max_retries: int,
    client: OpenAICompatibleClient,
    top_k: int,
    run_id: str,
    criteria_mode: str,
) -> ExampleProcessingResult:
    prompt, prompt_metadata = build_criterion_wise_prompt(
        example,
        setting=input_setting,
        prompt_version=prompt_version,
        criteria_mode=criteria_mode,
    )
    expected_criterion_ids = [
        item.strip()
        for item in prompt_metadata.get("expected_criterion_ids", "").split(",")
        if item.strip()
    ]

    attempt = 0
    request_metadata = {
        "prompt_version": prompt_version,
        "input_setting": input_setting.value,
        "prediction_schema": PREDICTION_SCHEMA,
        "criterion_mode": criteria_mode,
        "criteria_input_mode": criteria_mode,
        "text_source": prompt_metadata["text_source"],
        "criteria_source": prompt_metadata["criteria_source"],
        "criteria_probe_limit": top_k,
    }
    if prompt_metadata.get("fixed_criteria_source"):
        request_metadata["fixed_criteria_source"] = prompt_metadata["fixed_criteria_source"]
    if expected_criterion_ids:
        request_metadata["expected_criterion_ids"] = expected_criterion_ids

    while True:
        attempt += 1
        try:
            raw_response, request_id = client.invoke(prompt)
            prediction, response_metadata_dict, validation_errors = _prediction_from_criterion_only_response(
                example=example,
                raw_response=raw_response,
                provider=provider_config.provider,
                model=provider_config.model,
                request_id=request_id,
                metadata=request_metadata,
                expected_criterion_ids=expected_criterion_ids,
            )
            if prediction is None:
                return ExampleProcessingResult(
                    example_id=example.example_id,
                    error_record=_make_error_record(
                        example_id=example.example_id,
                        error_type="prediction_validation_error",
                        error_message="prediction failed schema validation",
                        provider=provider_config.provider,
                        model=provider_config.model,
                        request_id=request_id,
                        raw_response=response_metadata_dict.get("raw_response"),
                        parsed_json=response_metadata_dict.get("parsed_json"),
                        validation_errors=validation_errors,
                        attempt_count=attempt,
                        metadata=request_metadata,
                    ),
                )

            prediction.metadata.update(request_metadata)
            aggregation_result = aggregate_csmed_criterion_judgments(prediction, [])
            finalized = apply_aggregation_to_prediction(prediction, aggregation_result)
            finalized.metadata.update(
                {
                    "aggregation_status": aggregation_result.aggregation_status,
                    "criterion_mode": criteria_mode,
                }
            )
            return ExampleProcessingResult(
                example_id=example.example_id,
                prediction_record=finalized.model_dump(mode="json"),
            )
        except DirectLlmRuntimeError as exc:
            if exc.retryable and attempt <= max_retries:
                continue
            return ExampleProcessingResult(
                example_id=example.example_id,
                error_record=_make_error_record(
                    example_id=example.example_id,
                    error_type=exc.error_type,
                    error_message=str(exc),
                    provider=provider_config.provider,
                    model=provider_config.model,
                    request_id=exc.request_id,
                    raw_response=exc.raw_response,
                    parsed_json=exc.parsed_json,
                    validation_errors=exc.validation_errors,
                    attempt_count=attempt,
                    metadata=request_metadata,
                ),
            )


def _load_prediction_models(path: Path) -> list[BaseScreeningPrediction]:
    if not path.exists():
        return []
    return read_prediction_jsonl(path)


def _evaluate_and_write_outputs(
    *,
    predictions_path: Path,
    examples: list[ScreeningExample],
    evaluation_examples_path: Path,
    output_metrics_path: Path,
    run_id: str,
    method: str,
) -> dict[str, Any]:
    predictions = _load_prediction_models(predictions_path)
    write_model_jsonl(evaluation_examples_path, examples)
    metrics = evaluate_predictions(
        predictions=predictions,
        examples=examples,
        run_id=run_id,
        method=method,
        predictions_path=str(predictions_path),
        benchmark=examples[0].benchmark,
        split=examples[0].split,
        input_setting=examples[0].input_setting.value if examples[0].input_setting else None,
        readiness_profile="full_text",
        workload_mode="auto",
    )
    write_json(output_metrics_path, metrics)
    update_automation_readiness_table(results_root / "tables" / "automation_readiness.csv", metrics)
    return metrics


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m screening.cli.run_criterion_wise",
        description="Run the criterion-wise evidence-grounded screening method.",
    )
    parser.add_argument("--examples", required=True, help="Path to ScreeningExample JSONL.")
    parser.add_argument("--provider-config", required=True, help="Path to provider YAML config.")
    parser.add_argument("--defaults-config", help="Optional experiment defaults YAML.")
    parser.add_argument("--provider", help="Optional provider override.")
    parser.add_argument("--model", help="Optional model override.")
    parser.add_argument(
        "--input-setting",
        choices=[InputSetting.full_text_only.value, InputSetting.abstract_plus_full_text.value],
        required=True,
        help="Criterion-wise Phase 8 input setting.",
    )
    parser.add_argument("--prompt-version", help="Optional prompt version override.")
    parser.add_argument("--run-id", help="Optional run identifier.")
    parser.add_argument("--limit", type=int, help="Optional example limit.")
    parser.add_argument("--resume", action="store_true", help="Skip completed example_ids.")
    parser.add_argument("--output-dir", help="Optional output directory for predictions and errors.")
    parser.add_argument("--temperature", type=float, help="Optional temperature override.")
    parser.add_argument("--max-tokens", type=int, help="Optional max tokens override.")
    parser.add_argument("--workers", type=int, default=1, help="Number of concurrent workers.")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="Retrieved chunks per criterion.")
    parser.add_argument(
        "--criteria-mode",
        choices=list(CRITERIA_MODES),
        default=CRITERIA_MODE_RAW,
        help="How review criteria are supplied to the criterion-wise prompt.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    examples = read_model_jsonl(args.examples, ScreeningExample)
    if not examples:
        raise ValueError("examples must not be empty")

    input_setting = InputSetting(args.input_setting)
    filtered_examples = [example for example in examples if example.input_setting == input_setting]
    if len(filtered_examples) != len(examples):
        raise ValueError("all examples must match --input-setting")
    if args.limit is not None:
        if args.limit <= 0:
            raise ValueError("--limit must be positive")
        filtered_examples = filtered_examples[: args.limit]
    if args.workers <= 0:
        raise ValueError("--workers must be positive")
    if args.top_k <= 0:
        raise ValueError("--top-k must be positive")
    criteria_mode = args.criteria_mode

    defaults = load_experiment_defaults(args.defaults_config) if args.defaults_config else None
    providers = load_provider_configs(args.provider_config)
    provider_config = _select_provider(
        providers,
        provider_name=args.provider,
        model_name=args.model,
        default_provider_name=defaults.default_provider if defaults else providers[0].provider,
    )
    run_id = args.run_id or _default_run_id(DEFAULT_METHOD)
    temperature = (
        args.temperature
        if args.temperature is not None
        else provider_config.temperature
        if provider_config.temperature is not None
        else defaults.default_temperature
        if defaults
        else 0.0
    )
    max_tokens = (
        args.max_tokens
        if args.max_tokens is not None
        else provider_config.max_tokens
        if provider_config.max_tokens is not None
        else defaults.default_max_tokens
        if defaults
        else 1200
    )
    max_retries = (
        provider_config.max_retries
        if provider_config.max_retries is not None
        else defaults.default_max_retries
        if defaults
        else 2
    )
    client = _build_client(
        provider_config=provider_config,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    paths = _build_output_paths(examples=filtered_examples, output_dir=args.output_dir, run_id=run_id)
    paths["prediction_dir"].mkdir(parents=True, exist_ok=True)
    paths["log_dir"].mkdir(parents=True, exist_ok=True)
    lock_path = paths["log_dir"] / ".run.lock"
    lock_fd = _acquire_run_lock(lock_path)
    atexit.register(_release_run_lock, lock_path, lock_fd)

    processed_ids: set[str] = set()
    if args.resume:
        processed_ids |= _load_processed_ids(paths["predictions"])
        processed_ids |= _load_processed_ids(paths["errors"])

    started_at = datetime.now(timezone.utc)
    success_count = 0
    error_count = 0
    total = len(filtered_examples)
    error_examples: list[str] = []
    prompt_version = _resolve_prompt_version(
        args.prompt_version,
        defaults,
        criteria_mode=criteria_mode,
    )
    pending_examples = [
        example
        for example in filtered_examples
        if not (args.resume and example.example_id in processed_ids)
    ]

    completed = len(processed_ids) if args.resume else 0
    if total:
        _print_progress(
            completed=completed,
            total=total,
            success_count=success_count,
            error_count=error_count,
        )

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        in_flight: dict[Future[ExampleProcessingResult], ScreeningExample] = {}
        pending_iter = iter(pending_examples)

        while len(in_flight) < args.workers:
            try:
                example = next(pending_iter)
            except StopIteration:
                break
            future = executor.submit(
                _invoke_one_example,
                example=example,
                input_setting=input_setting,
                prompt_version=prompt_version,
                provider_config=provider_config,
                max_retries=max_retries,
                client=client,
                top_k=args.top_k,
                run_id=run_id,
                criteria_mode=criteria_mode,
            )
            in_flight[future] = example

        while in_flight:
            done, _ = wait(in_flight.keys(), return_when=FIRST_COMPLETED)
            for future in done:
                example = in_flight.pop(future)
                try:
                    result = future.result()
                except Exception as exc:  # pragma: no cover - defensive safeguard
                    result = ExampleProcessingResult(
                        example_id=example.example_id,
                        error_record=_make_error_record(
                            example_id=example.example_id,
                            error_type="worker_exception",
                            error_message=str(exc),
                            provider=provider_config.provider,
                            model=provider_config.model,
                            request_id=None,
                            raw_response=None,
                            parsed_json=None,
                            validation_errors=[],
                            attempt_count=1,
                            metadata={
                                "run_id": run_id,
                                "prompt_version": prompt_version,
                                "input_setting": input_setting.value,
                                "prediction_schema": PREDICTION_SCHEMA,
                                "criterion_mode": criteria_mode,
                                "criteria_input_mode": criteria_mode,
                                "criteria_probe_limit": args.top_k,
                            },
                        ),
                    )
                completed += 1
                if result.is_success:
                    prediction_record = dict(result.prediction_record or {})
                    prediction_record.setdefault("metadata", {})
                    prediction_record["metadata"].update({"run_id": run_id})
                    append_jsonl(paths["predictions"], [prediction_record])
                    success_count += 1
                else:
                    error_record = dict(result.error_record or {})
                    error_record.setdefault("metadata", {})
                    error_record["metadata"].update({"run_id": run_id})
                    append_jsonl(paths["errors"], [error_record])
                    error_count += 1
                    error_examples.append(example.example_id)
                _print_progress(
                    completed=completed,
                    total=total,
                    success_count=success_count,
                    error_count=error_count,
                )

                try:
                    next_example = next(pending_iter)
                except StopIteration:
                    continue
                next_future = executor.submit(
                    _invoke_one_example,
                    example=next_example,
                    input_setting=input_setting,
                    prompt_version=prompt_version,
                    provider_config=provider_config,
                    max_retries=max_retries,
                    client=client,
                    top_k=args.top_k,
                    run_id=run_id,
                    criteria_mode=criteria_mode,
                )
                in_flight[next_future] = next_example

    ended_at = datetime.now(timezone.utc)
    _validate_unique_prediction_records(paths["predictions"])
    final_predictions = _load_prediction_models(paths["predictions"])
    prediction_ids = {prediction.example_id for prediction in final_predictions}
    evaluation_examples = _select_examples_by_ids(filtered_examples, prediction_ids)
    final_errors = read_jsonl(paths["errors"]) if paths["errors"].exists() else []
    final_error_ids = [
        record["example_id"]
        for record in final_errors
        if isinstance(record.get("example_id"), str) and record["example_id"].strip()
    ]
    metrics = None
    if final_predictions:
        metrics = _evaluate_and_write_outputs(
            predictions_path=paths["predictions"],
            examples=evaluation_examples,
            evaluation_examples_path=paths["evaluation_examples"],
            output_metrics_path=paths["metrics"],
            run_id=run_id,
            method=DEFAULT_METHOD,
        )

    metadata = RunMetadata(
        run_id=run_id,
        method=DEFAULT_METHOD,
        benchmark=filtered_examples[0].benchmark,
        split=filtered_examples[0].split,
        input_setting=input_setting,
        provider=provider_config.provider,
        model=provider_config.model,
        prompt_version=prompt_version,
        temperature=temperature,
        max_tokens=max_tokens,
        config_path=Path(args.defaults_config) if args.defaults_config else None,
        provider_config_path=Path(args.provider_config),
        examples_path=Path(args.examples),
        prediction_path=paths["predictions"] if paths["predictions"].exists() else None,
        metric_path=paths["metrics"] if metrics is not None else None,
        command=[sys.executable, "-m", "screening.cli.run_criterion_wise", *(argv or sys.argv[1:])],
        started_at=started_at,
        ended_at=ended_at,
        sample_count=total,
        success_count=len(final_predictions),
        error_count=len(final_errors),
        is_real_llm_run=True,
        error_examples=final_error_ids,
        metadata={
            "output_dir": str(paths["prediction_dir"]),
            "evaluated_sample_count": len(evaluation_examples),
            "skipped_by_resume_count": len(processed_ids),
            "new_success_count": success_count,
            "new_error_count": error_count,
            "prediction_schema": PREDICTION_SCHEMA,
            "workers": args.workers,
            "lock_path": str(lock_path),
            "criteria_input_mode": criteria_mode,
            "criteria_probe_limit": args.top_k,
            "aggregation_policy": AGGREGATION_POLICY,
            "criterion_mode": criteria_mode,
            "method_parent_reference": DIRECT_METHOD,
        },
    )
    write_json(paths["metadata"], metadata.model_dump(mode="json"))
    update_run_index(
        results_root / "tables" / "run_index.csv",
        {
            **metadata.model_dump(mode="json"),
            "examples_path": str(metadata.examples_path) if metadata.examples_path else None,
            "prediction_path": str(metadata.prediction_path) if metadata.prediction_path else None,
            "metric_path": str(metadata.metric_path) if metadata.metric_path else None,
            "config_path": str(metadata.config_path) if metadata.config_path else None,
            "provider_config_path": (
                str(metadata.provider_config_path) if metadata.provider_config_path else None
            ),
        },
    )

    print(f"predictions_jsonl: {paths['predictions']}")
    print(f"errors_jsonl: {paths['errors']}")
    print(f"run_metadata_json: {paths['metadata']}")
    if metrics is not None:
        print(f"metrics_json: {paths['metrics']}")
        print(f"automation_readiness_csv: {results_root / 'tables' / 'automation_readiness.csv'}")
    print(f"run_index_csv: {results_root / 'tables' / 'run_index.csv'}")
    _release_run_lock(lock_path, lock_fd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
