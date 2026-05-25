"""CLI for direct criteria-aware LLM screening runs."""

from __future__ import annotations

import argparse
import atexit
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from screening.config import ProviderConfig, load_experiment_defaults, load_provider_configs
from screening.evaluation.decision import evaluate_predictions
from screening.evaluation.tables import update_automation_readiness_table
from screening.io_utils import (
    append_jsonl,
    normalize_prediction_response,
    read_jsonl,
    read_model_jsonl,
    read_prediction_jsonl,
    write_json,
    write_model_jsonl,
)
from screening.paths import results_root
from screening.prompts.direct import build_direct_prompt
from screening.run_index import update_run_index
from screening.schemas import (
    AbstractScreeningPrediction,
    BaseScreeningPrediction,
    InputSetting,
    RunMetadata,
    ScreeningExample,
    ScreeningPrediction,
)


DEFAULT_METHOD = "direct_criteria_aware"


class DirectLlmRuntimeError(RuntimeError):
    """Raised when a provider request fails before a valid prediction is produced."""

    def __init__(
        self,
        message: str,
        *,
        error_type: str,
        request_id: str | None = None,
        raw_response: str | None = None,
        parsed_json: dict[str, Any] | None = None,
        validation_errors: list[str] | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.request_id = request_id
        self.raw_response = raw_response
        self.parsed_json = parsed_json
        self.validation_errors = validation_errors or []
        self.retryable = retryable


class RunLockError(RuntimeError):
    """Raised when a run output directory is already locked by another process."""


class ResultConflictError(RuntimeError):
    """Raised when written prediction records contain duplicate/conflicting example_ids."""


class OpenAICompatibleClient:
    """Minimal OpenAI-compatible chat completions client."""

    def __init__(
        self,
        *,
        provider_config: ProviderConfig,
        api_key: str,
        temperature: float,
        max_tokens: int,
    ) -> None:
        self.provider_config = provider_config
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        base_url = (provider_config.base_url or "https://api.openai.com/v1").rstrip("/")
        self.endpoint = f"{base_url}/chat/completions"

    def invoke(self, prompt: str) -> tuple[str, str | None]:
        payload = {
            "model": self.provider_config.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a careful evidence screening assistant. "
                        "Return exactly one JSON object and no markdown."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        timeout = float(self.provider_config.timeout_seconds or 60)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
                request_id = response.headers.get("x-request-id")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            request_id = exc.headers.get("x-request-id")
            retryable = exc.code == 429 or 500 <= exc.code < 600
            raise DirectLlmRuntimeError(
                f"provider returned HTTP {exc.code}",
                error_type="http_error",
                request_id=request_id,
                raw_response=body,
                retryable=retryable,
            ) from exc
        except urllib.error.URLError as exc:
            raise DirectLlmRuntimeError(
                f"provider request failed: {exc.reason}",
                error_type="network_error",
                retryable=True,
            ) from exc
        except TimeoutError as exc:
            raise DirectLlmRuntimeError(
                "provider request timed out",
                error_type="timeout_error",
                retryable=True,
            ) from exc

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise DirectLlmRuntimeError(
                f"provider response was not valid JSON: {exc.msg}",
                error_type="provider_invalid_json",
                raw_response=body,
            ) from exc

        if not isinstance(parsed, dict):
            raise DirectLlmRuntimeError(
                "provider response JSON must be an object",
                error_type="provider_invalid_shape",
                raw_response=body,
                parsed_json=None,
            )
        try:
            content = parsed["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise DirectLlmRuntimeError(
                "provider response missing choices[0].message.content",
                error_type="provider_invalid_shape",
                raw_response=body,
                parsed_json=parsed,
            ) from exc
        if not isinstance(content, str) or not content.strip():
            raise DirectLlmRuntimeError(
                "provider content was empty",
                error_type="provider_empty_content",
                raw_response=body,
                parsed_json=parsed,
            )
        return content, request_id


class ExampleProcessingResult:
    """One processed example outcome ready to be written to disk."""

    def __init__(
        self,
        *,
        example_id: str,
        prediction_record: dict[str, Any] | None = None,
        error_record: dict[str, Any] | None = None,
    ) -> None:
        self.example_id = example_id
        self.prediction_record = prediction_record
        self.error_record = error_record

    @property
    def is_success(self) -> bool:
        return self.prediction_record is not None


def _default_run_id(method: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{method}_{timestamp}"


def _select_provider(
    providers: list[ProviderConfig],
    *,
    provider_name: str | None,
    model_name: str | None,
    default_provider_name: str,
) -> ProviderConfig:
    target_provider = provider_name or default_provider_name
    candidates = [item for item in providers if item.provider == target_provider]
    if model_name:
        candidates = [item for item in candidates if item.model == model_name]
    if not candidates:
        raise ValueError(
            f"no provider config found for provider={target_provider!r}, model={model_name!r}"
        )
    return candidates[0]


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
        pred_dir = (
            results_root / "preds" / benchmark / split / DEFAULT_METHOD / run_id
        )
    log_dir = results_root / "logs" / benchmark / split / DEFAULT_METHOD / run_id
    metric_path = results_root / "metrics" / benchmark / split / DEFAULT_METHOD / f"{run_id}.json"
    return {
        "prediction_dir": pred_dir,
        "predictions": pred_dir / "predictions.jsonl",
        "errors": pred_dir / "errors.jsonl",
        "evaluation_examples": pred_dir / "evaluation_examples.jsonl",
        "log_dir": log_dir,
        "metadata": log_dir / "run_metadata.json",
        "metrics": metric_path,
    }


def _load_processed_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    processed: set[str] = set()
    for record in read_jsonl(path):
        example_id = record.get("example_id")
        if isinstance(example_id, str) and example_id.strip():
            processed.add(example_id)
    return processed


def _print_progress(*, completed: int, total: int, success_count: int, error_count: int) -> None:
    message = (
        f"\rprogress {completed}/{total} | success={success_count} | error={error_count}"
    )
    print(message, end="", flush=True)
    if completed == total:
        print("", flush=True)


def _acquire_run_lock(lock_path: Path) -> int:
    """Acquire an exclusive run-level lock for one output directory."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(lock_path, flags, 0o644)
    except FileExistsError as exc:
        raise RunLockError(f"run lock already exists: {lock_path}") from exc
    payload = {
        "pid": os.getpid(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    os.write(fd, json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    os.write(fd, b"\n")
    return fd


def _release_run_lock(lock_path: Path, fd: int | None) -> None:
    """Release a previously acquired run-level lock."""
    if fd is not None:
        try:
            os.close(fd)
        except OSError:
            pass
    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass


def _validate_unique_prediction_records(predictions_path: Path) -> None:
    """Ensure predictions.jsonl contains exactly one record per example_id."""
    if not predictions_path.exists():
        return

    records = read_jsonl(predictions_path)
    seen: dict[str, dict[str, Any]] = {}
    duplicate_ids: list[str] = []
    conflicting_ids: list[str] = []
    for record in records:
        example_id = record.get("example_id")
        if not isinstance(example_id, str) or not example_id.strip():
            continue
        previous = seen.get(example_id)
        if previous is None:
            seen[example_id] = record
            continue
        duplicate_ids.append(example_id)
        if previous != record:
            conflicting_ids.append(example_id)

    if conflicting_ids:
        unique_conflicts = sorted(set(conflicting_ids))
        sample = ", ".join(unique_conflicts[:5])
        raise ResultConflictError(
            "conflicting duplicate predictions detected for example_ids: "
            f"{sample} (total={len(unique_conflicts)})"
        )
    if duplicate_ids:
        unique_duplicates = sorted(set(duplicate_ids))
        sample = ", ".join(unique_duplicates[:5])
        raise ResultConflictError(
            "duplicate predictions detected for example_ids: "
            f"{sample} (total={len(unique_duplicates)})"
        )


def _make_error_record(
    *,
    example_id: str,
    error_type: str,
    error_message: str,
    provider: str,
    model: str,
    request_id: str | None,
    raw_response: str | None,
    parsed_json: dict[str, Any] | None,
    validation_errors: list[str],
    attempt_count: int,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "example_id": example_id,
        "error_type": error_type,
        "error_message": error_message,
        "provider": provider,
        "model": model,
        "request_id": request_id,
        "raw_response": raw_response,
        "parsed_json": parsed_json,
        "validation_errors": validation_errors,
        "attempt_count": attempt_count,
        "metadata": metadata,
    }


def _build_client(
    *,
    provider_config: ProviderConfig,
    temperature: float,
    max_tokens: int,
) -> OpenAICompatibleClient:
    api_key = provider_config.api_key
    api_key_env = provider_config.api_key_env
    if api_key is None and api_key_env:
        if api_key_env.startswith("sk-"):
            api_key = api_key_env
        else:
            api_key = os.environ.get(api_key_env)
            if not api_key:
                raise ValueError(
                    f"environment variable {api_key_env} is required for provider access"
                )
    if not api_key:
        raise ValueError("provider config requires api_key or api_key_env")
    if provider_config.provider not in {"openai", "openai-compatible"}:
        raise ValueError(f"unsupported provider for Phase 7: {provider_config.provider}")
    return OpenAICompatibleClient(
        provider_config=provider_config,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _invoke_one_example(
    *,
    example: ScreeningExample,
    input_setting: InputSetting,
    prompt_version: str,
    provider_config: ProviderConfig,
    max_retries: int,
    client: OpenAICompatibleClient,
) -> ExampleProcessingResult:
    prediction_schema = (
        "abstract_only_v3"
        if input_setting == InputSetting.abstract_only and prompt_version == "v3"
        else "screening_prediction_v0"
    )
    prediction_model: type[BaseScreeningPrediction] = (
        AbstractScreeningPrediction
        if prediction_schema == "abstract_only_v3"
        else ScreeningPrediction
    )
    prompt, prompt_metadata = build_direct_prompt(
        example,
        setting=input_setting,
        prompt_version=prompt_version,
    )
    attempt = 0
    while True:
        attempt += 1
        try:
            raw_response, request_id = client.invoke(prompt)
            prediction, response_metadata = normalize_prediction_response(
                example_id=example.example_id,
                raw_response=raw_response,
                provider=provider_config.provider,
                model=provider_config.model,
                request_id=request_id,
                metadata={
                    "prompt_version": prompt_version,
                    "input_setting": input_setting.value,
                    "prediction_schema": prediction_schema,
                    **prompt_metadata,
                },
                prediction_model=prediction_model,
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
                        raw_response=response_metadata.raw_response,
                        parsed_json=response_metadata.parsed_json,
                        validation_errors=response_metadata.validation_errors,
                        attempt_count=attempt,
                        metadata={
                            "prompt_version": prompt_version,
                            "input_setting": input_setting.value,
                            "prediction_schema": prediction_schema,
                            **prompt_metadata,
                        },
                    ),
                )
            prediction.metadata.update(
                {
                    "prompt_version": prompt_version,
                    "input_setting": input_setting.value,
                    "prediction_schema": prediction_schema,
                    "text_source": prompt_metadata["text_source"],
                }
            )
            return ExampleProcessingResult(
                example_id=example.example_id,
                prediction_record=prediction.model_dump(mode="json"),
            )
        except DirectLlmRuntimeError as exc:
            if exc.retryable and attempt <= max_retries:
                time.sleep(provider_config.retry_backoff_seconds)
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
                    metadata={
                        "prompt_version": prompt_version,
                        "input_setting": input_setting.value,
                        **prompt_metadata,
                    },
                ),
            )


def _load_prediction_models(path: Path) -> list[BaseScreeningPrediction]:
    if not path.exists():
        return []
    return read_prediction_jsonl(path)


def _select_examples_by_ids(
    examples: list[ScreeningExample], prediction_ids: set[str]
) -> list[ScreeningExample]:
    return [example for example in examples if example.example_id in prediction_ids]


def _evaluate_and_write_outputs(
    *,
    predictions_path: Path,
    examples: list[ScreeningExample],
    evaluation_examples_path: Path,
    output_metrics_path: Path,
    defaults_config: str | None,
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
        readiness_profile="stage1" if examples[0].input_setting == InputSetting.abstract_only else "full_text",
        workload_mode="auto",
    )
    write_json(output_metrics_path, metrics)
    update_automation_readiness_table(results_root / "tables" / "automation_readiness.csv", metrics)
    return metrics


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m screening.cli.run_direct_llm",
        description="Run the direct LLM baseline for screening experiments.",
    )
    parser.add_argument(
        "--examples",
        required=True,
        help="Path to ScreeningExample JSONL.",
    )
    parser.add_argument(
        "--provider-config",
        required=True,
        help="Path to provider YAML config.",
    )
    parser.add_argument(
        "--defaults-config",
        help="Optional experiment defaults YAML.",
    )
    parser.add_argument(
        "--provider",
        help="Optional provider override.",
    )
    parser.add_argument(
        "--model",
        help="Optional model override.",
    )
    parser.add_argument(
        "--input-setting",
        choices=[setting.value for setting in InputSetting if setting != InputSetting.evidence_profile],
        required=True,
        help="Input setting to enforce for prompt construction.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional example limit.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip example_ids already present in predictions.jsonl or errors.jsonl.",
    )
    parser.add_argument(
        "--output-dir",
        help="Optional output directory for predictions and errors.",
    )
    parser.add_argument(
        "--run-id",
        help="Optional run identifier. Defaults to a UTC timestamped ID.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        help="Optional temperature override.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        help="Optional max tokens override.",
    )
    parser.add_argument(
        "--prompt-version",
        help="Optional prompt version override.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of concurrent request workers. Default: 1.",
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
    error_examples: list[str] = []
    total = len(filtered_examples)
    prompt_version = args.prompt_version or (defaults.prompt_version if defaults else "v0")
    prediction_schema = (
        "abstract_only_v3"
        if input_setting == InputSetting.abstract_only and prompt_version == "v3"
        else "screening_prediction_v0"
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
                                "prediction_schema": prediction_schema,
                            },
                        ),
                    )
                completed += 1
                if result.is_success:
                    prediction_record = dict(result.prediction_record or {})
                    prediction_record.setdefault("metadata", {})
                    prediction_record["metadata"].update(
                        {
                            "run_id": run_id,
                        }
                    )
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
            defaults_config=args.defaults_config,
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
        command=[sys.executable, "-m", "screening.cli.run_direct_llm", *(argv or sys.argv[1:])],
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
            "prediction_schema": prediction_schema,
            "workers": args.workers,
            "lock_path": str(lock_path),
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
