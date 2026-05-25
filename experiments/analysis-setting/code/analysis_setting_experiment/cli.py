from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .canonicalization import CANONICALIZATION_VERSION, canonicalize_predictions_with_provenance
from .conditional_dataset import export_conditional_dataset
from .conditional_evaluator import (
    aggregate_conditional_results,
    build_conditional_error_analysis,
    evaluate_conditional_instance,
)
from .conditional_experiment import (
    DEFAULT_DECISION_STRATEGY,
    DEFAULT_EVIDENCE_STRATEGY,
    DECISION_STRATEGIES,
    EVIDENCE_STRATEGIES,
    conditional_result_variant,
    conditional_target_label,
    resolve_conditional_prompt_version,
    resolve_effect_measure_decision_strategy,
    resolve_effect_measure_evidence_strategy,
    build_stratified_subset,
)
from .conditional_runner import (
    build_conditional_backend,
    conditional_prediction_root,
    load_conditional_prediction_or_empty,
    run_conditional_split,
)
from .conditional_constants import CONDITIONAL_PROMPT_VERSION
from .dataset import export_prepared_dataset
from .evaluator import aggregate_review_metrics, build_error_analysis_sample, summarize_by_bucket
from .io_utils import dump_json, dump_jsonl, load_json, load_jsonl
from .judge import (
    aggregate_judge_results,
    build_judge_backend,
    build_judge_error_analysis,
    build_judge_pairs,
    build_rigid_review_result,
    judge_pair,
    summarize_judge_review,
)
from .runner import RunConfig, _load_local_api_config, build_backend, run_root, run_split



def _resolve_model_name(explicit_model_name: str) -> str:
    local_config = _load_local_api_config()
    return local_config.get("model", "") or explicit_model_name



def _conditional_run_config(args: argparse.Namespace) -> RunConfig:
    config = RunConfig(
        model_name=_resolve_model_name(args.model_name),
        model_version=args.model_version,
        split=args.split,
        output_dir=Path(args.output_dir),
        api_key=args.api_key or "",
        base_url=args.base_url or "",
        max_retries=args.max_retries,
        timeout_seconds=args.timeout_seconds,
        concurrency=args.concurrency,
        max_output_tokens=args.max_output_tokens,
        rerun_failed=args.rerun_failed,
        rerun_invalid_output=args.rerun_invalid_output,
        rerun_empty_output=args.rerun_empty_output,
        review_ids=tuple(args.review_id or ()),
    )
    decision_strategy = resolve_effect_measure_decision_strategy(args.task, getattr(args, "decision_strategy", ""))
    evidence_strategy = resolve_effect_measure_evidence_strategy(args.task, getattr(args, "evidence_strategy", ""))
    config.prompt_version = resolve_conditional_prompt_version(
        args.task,
        prompt_version=getattr(args, "prompt_version", ""),
        decision_strategy=decision_strategy,
        default_prompt_version=CONDITIONAL_PROMPT_VERSION,
    )
    config.evidence_strategy = evidence_strategy
    config.decision_strategy = decision_strategy
    config.few_shot_set = getattr(args, "few_shot_set", "") or ""
    return config



def command_prepare(args: argparse.Namespace) -> None:
    summary = export_prepared_dataset(
        benchmark_path=Path(args.benchmark_path),
        output_dir=Path(args.output_dir),
        dev_ratio=args.dev_ratio,
        seed=args.seed,
    )
    print(summary)



def command_prepare_conditional(args: argparse.Namespace) -> None:
    summary = export_conditional_dataset(
        benchmark_path=Path(args.benchmark_path),
        output_dir=Path(args.output_dir),
        dev_ratio=args.dev_ratio,
        seed=args.seed,
        evidence_mode=args.evidence_mode,
    )
    print(summary)



def command_make_conditional_subset(args: argparse.Namespace) -> None:
    rows = [
        row for row in load_jsonl(Path(args.dataset_path))
        if row["task_name"] == args.task and row["evidence_mode"] == args.evidence_mode
    ]
    labels = []
    for row in rows:
        if args.task in {"data_type", "candidate_effect_measure"}:
            labels.append(conditional_target_label(args.task, row))
        else:
            labels.append(f"{row['task_name']}::{conditional_target_label(args.task, row)}")
    subset = build_stratified_subset(rows, size=args.subset_size, stratify_labels=labels, seed=args.seed)
    metadata = {
        "dataset_path": str(Path(args.dataset_path)),
        "task": args.task,
        "evidence_mode": args.evidence_mode,
        "subset_size": len(subset),
        "requested_subset_size": args.subset_size,
        "seed": args.seed,
        "stratify_by": "gold_target_label",
        "instance_ids": [row["instance_id"] for row in subset],
        "review_ids": sorted({row["review_id"] for row in subset}),
        "label_counts": {},
    }
    for row in subset:
        label = conditional_target_label(args.task, row)
        metadata["label_counts"][label] = metadata["label_counts"].get(label, 0) + 1
    dump_jsonl(Path(args.output_path), subset)
    dump_json(Path(args.output_path).with_suffix(".metadata.json"), metadata)
    print(metadata)



def command_run(args: argparse.Namespace) -> None:
    config = RunConfig(
        model_name=_resolve_model_name(args.model_name),
        model_version=args.model_version,
        split=args.split,
        output_dir=Path(args.output_dir),
        api_key=args.api_key or "",
        base_url=args.base_url or "",
        max_retries=args.max_retries,
        timeout_seconds=args.timeout_seconds,
        concurrency=args.concurrency,
        max_output_tokens=args.max_output_tokens,
        rerun_failed=args.rerun_failed,
        rerun_invalid_output=args.rerun_invalid_output,
        rerun_empty_output=args.rerun_empty_output,
        review_ids=tuple(args.review_id or ()),
    )
    backend = build_backend(args.backend, json_source=Path(args.json_source) if args.json_source else None)
    summary = run_split(Path(args.dataset_path), config, backend)
    print(summary)



def command_run_conditional(args: argparse.Namespace) -> None:
    config = _conditional_run_config(args)
    backend = build_conditional_backend(args.backend, json_source=Path(args.json_source) if args.json_source else None)
    summary = run_conditional_split(
        Path(args.dataset_path),
        config,
        backend,
        task_name=args.task,
        evidence_mode=args.evidence_mode,
    )
    print(summary)



def _load_prediction_or_empty(output_dir: Path, model_name: str, split: str, review_id: str) -> dict[str, Any]:
    path = output_dir / "runs" / model_name / split / review_id / "latest_prediction.json"
    if not path.exists():
        return {
            "parsed_prediction_json": [],
            "schema_valid": False,
            "parse_status": "missing_prediction",
        }
    return load_json(path)



def _prediction_path(output_dir: Path, model_name: str, split: str, review_id: str) -> Path:
    return output_dir / "runs" / model_name / split / review_id / "latest_prediction.json"



def command_recanonicalize(args: argparse.Namespace) -> None:
    dataset_rows = load_jsonl(Path(args.dataset_path))
    updated_review_ids: list[str] = []
    skipped_review_ids: list[str] = []
    for row in dataset_rows:
        review_id = row["review_id"]
        if args.review_id and review_id not in set(args.review_id):
            continue
        path = _prediction_path(Path(args.output_dir), args.model_name, args.split, review_id)
        if not path.exists():
            skipped_review_ids.append(review_id)
            continue
        payload = load_json(path)
        if payload.get("parse_status") != "success":
            skipped_review_ids.append(review_id)
            continue
        raw_candidates = payload.get("raw_parsed_prediction_json")
        if raw_candidates is None:
            raw_candidates = payload.get("parsed_prediction_json", [])
            payload["raw_parsed_prediction_json"] = raw_candidates
        canonicalization_result = canonicalize_predictions_with_provenance(row, raw_candidates)
        payload["canonicalized_prediction_json"] = canonicalization_result["canonicalized_candidates"]
        payload["parsed_prediction_json"] = canonicalization_result["canonicalized_candidates"]
        payload["canonicalization_version"] = CANONICALIZATION_VERSION
        payload["canonicalization_provenance"] = canonicalization_result["provenance"]
        dump_json(path, payload)
        updated_review_ids.append(review_id)
    summary = {
        "updated_review_count": len(updated_review_ids),
        "skipped_review_count": len(skipped_review_ids),
        "canonicalization_version": CANONICALIZATION_VERSION,
        "updated_review_ids": updated_review_ids,
        "skipped_review_ids": skipped_review_ids,
    }
    print(summary)



def command_evaluate(args: argparse.Namespace) -> None:
    dataset_rows = load_jsonl(Path(args.dataset_path))
    review_results: list[dict[str, Any]] = []
    raw_fallback_review_count = 0
    for row in dataset_rows:
        prediction = _load_prediction_or_empty(Path(args.output_dir), args.model_name, args.split, row["review_id"])
        review_result = build_rigid_review_result(
            row,
            prediction,
            split=args.split,
            threshold=args.match_threshold,
            prediction_mode=args.prediction_mode,
        )
        if review_result.get("raw_prediction_fallback_used"):
            raw_fallback_review_count += 1
        review_results.append(review_result)
    aggregate = aggregate_review_metrics(review_results)
    aggregate["prediction_mode"] = args.prediction_mode
    aggregate["raw_prediction_fallback_review_count"] = raw_fallback_review_count
    stratified = {
        "coverage_level": summarize_by_bucket(review_results, "coverage_level"),
        "abstract_study_count_bucket": summarize_by_bucket(review_results, "abstract_study_count_bucket"),
        "gold_candidate_count_bucket": summarize_by_bucket(review_results, "gold_candidate_count_bucket"),
    }
    error_sample = build_error_analysis_sample(review_results, sample_size=args.error_sample_size, seed=args.seed)
    eval_root = Path(args.output_dir) / "evaluations" / args.model_name / args.split / args.prediction_mode
    dump_jsonl(eval_root / "review_results.jsonl", review_results)
    dump_json(eval_root / "aggregate.json", aggregate)
    dump_json(eval_root / "stratified.json", stratified)
    dump_jsonl(eval_root / "error_analysis_sample.jsonl", error_sample)
    print(aggregate)



def command_evaluate_conditional(args: argparse.Namespace) -> None:
    resolved_model_name = _resolve_model_name(args.model_name)
    evidence_strategy = resolve_effect_measure_evidence_strategy(args.task, getattr(args, "evidence_strategy", ""))
    decision_strategy = resolve_effect_measure_decision_strategy(args.task, getattr(args, "decision_strategy", ""))
    resolved_prompt_version = resolve_conditional_prompt_version(
        args.task,
        prompt_version=getattr(args, "prompt_version", ""),
        decision_strategy=decision_strategy,
        default_prompt_version=CONDITIONAL_PROMPT_VERSION,
    )
    few_shot_set = getattr(args, "few_shot_set", "") or ""
    dataset_rows = [
        row
        for row in load_jsonl(Path(args.dataset_path))
        if row["task_name"] == args.task and row["evidence_mode"] == args.evidence_mode
    ]
    review_results: list[dict[str, Any]] = []
    output_dir = Path(args.output_dir)
    for row in dataset_rows:
        prediction = load_conditional_prediction_or_empty(
            output_dir,
            resolved_model_name,
            args.split,
            args.task,
            args.evidence_mode,
            row["instance_id"],
            evidence_strategy=evidence_strategy,
            decision_strategy=decision_strategy,
            few_shot_set=few_shot_set,
            prompt_version=resolved_prompt_version,
        )
        if args.task == "candidate_effect_measure" and args.cascade_data_type_source == "predicted":
            linked_id = row.get("task_metadata", {}).get("linked_data_type_instance_id", "")
            if linked_id:
                linked_prediction = load_conditional_prediction_or_empty(
                    output_dir,
                    args.model_name,
                    args.split,
                    "data_type",
                    args.evidence_mode,
                    linked_id,
                )
                linked_value = linked_prediction.get("parsed_prediction_json", {}).get("data_type", "")
                prediction = dict(prediction)
                parsed_json = dict(prediction.get("parsed_prediction_json", {}))
                parsed_json["condition_data_type"] = linked_value
                prediction["parsed_prediction_json"] = parsed_json
        review_results.append(
            evaluate_conditional_instance(
                row,
                prediction,
                cascade_data_type_source=args.cascade_data_type_source,
            )
        )
    aggregate = aggregate_conditional_results(
        args.task,
        review_results,
        cascade_data_type_source=args.cascade_data_type_source,
    )
    aggregate["task_name"] = args.task
    aggregate["evidence_mode"] = args.evidence_mode
    aggregate["evidence_strategy"] = evidence_strategy
    aggregate["decision_strategy"] = decision_strategy
    aggregate["prompt_version"] = resolved_prompt_version
    aggregate["few_shot_set"] = few_shot_set
    aggregate["model_name"] = resolved_model_name
    eval_root = Path(args.output_dir) / "evaluations" / resolved_model_name / args.split / args.task / args.evidence_mode
    variant = conditional_result_variant(
        args.task,
        evidence_strategy=evidence_strategy,
        decision_strategy=decision_strategy,
        few_shot_set=few_shot_set,
        prompt_version=resolved_prompt_version,
    )
    if variant:
        eval_root = eval_root / variant
    dump_jsonl(eval_root / "instance_results.jsonl", review_results)
    dump_json(eval_root / "aggregate.json", aggregate)
    dump_jsonl(
        eval_root / "error_analysis_sample.jsonl",
        build_conditional_error_analysis(
            args.task,
            review_results,
            sample_size=args.error_sample_size,
            seed=args.seed,
        ),
    )
    print(aggregate)



def command_judge_evaluate(args: argparse.Namespace) -> None:
    dataset_rows = load_jsonl(Path(args.dataset_path))
    dataset_by_review_id = {row["review_id"]: row for row in dataset_rows}
    rigid_root = Path(args.output_dir) / "evaluations" / args.model_name / args.split / args.prediction_mode
    review_results = load_jsonl(rigid_root / "review_results.jsonl")
    backend = build_judge_backend(args.backend, json_source=Path(args.json_source) if args.json_source else None)
    config = RunConfig(
        model_name=args.judge_model_name or args.model_name,
        model_version=args.judge_model_version or args.model_version or "",
        split=args.split,
        output_dir=Path(args.output_dir),
        api_key=args.api_key or "",
        base_url=args.base_url or "",
        timeout_seconds=args.timeout_seconds,
        max_output_tokens=args.max_output_tokens,
        concurrency=max(1, args.concurrency),
    )
    judge_root = Path(args.output_dir) / "judge_evaluations" / args.model_name / args.split / args.prediction_mode

    def _evaluate_review(review_result: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        review_row = dataset_by_review_id[review_result["review_id"]]
        pairs = build_judge_pairs(review_result)
        pair_results = [judge_pair(backend, config, review_row, pair) for pair in pairs]
        return summarize_judge_review(review_result, pair_results), pair_results

    review_summaries: list[dict[str, Any]] = []
    pair_artifacts: list[dict[str, Any]] = []
    total = len(review_results)
    completed = 0
    with ThreadPoolExecutor(max_workers=config.concurrency) as executor:
        futures = [executor.submit(_evaluate_review, review_result) for review_result in review_results]
        for future in as_completed(futures):
            review_summary, pair_results = future.result()
            review_summaries.append(review_summary)
            pair_artifacts.extend(pair_results)
            completed += 1
            print(f"[judge] {completed}/{total} reviews completed", flush=True)
            dump_jsonl(judge_root / "pair_results.partial.jsonl", pair_artifacts)
            dump_jsonl(judge_root / "review_summaries.partial.jsonl", review_summaries)

    review_summaries.sort(key=lambda item: item["review_id"])
    pair_artifacts.sort(key=lambda item: (item["review_id"], item["pred_index"], item["gold_index"]))
    aggregate = aggregate_judge_results(review_summaries)
    aggregate["prediction_mode"] = args.prediction_mode
    aggregate["judge_model_name"] = config.model_name
    aggregate["judge_model_version"] = config.model_version
    dump_jsonl(judge_root / "pair_results.jsonl", pair_artifacts)
    dump_jsonl(judge_root / "review_summaries.jsonl", review_summaries)
    dump_json(judge_root / "aggregate.json", aggregate)
    dump_jsonl(judge_root / "error_analysis_sample.jsonl", build_judge_error_analysis(review_summaries))
    print(aggregate)



def command_report_runs(args: argparse.Namespace) -> None:
    run_dir = run_root(
        RunConfig(
            model_name=args.model_name,
            model_version=args.model_version,
            split=args.split,
            output_dir=Path(args.output_dir),
        )
    )
    review_rows: list[dict[str, Any]] = []
    if run_dir.exists():
        for review_dir in sorted(path for path in run_dir.iterdir() if path.is_dir()):
            state_file = review_dir / "state.json"
            if state_file.exists():
                review_rows.append(load_json(state_file))
    summary = {
        "total_task_count": len(review_rows),
        "success_count": sum(1 for row in review_rows if row.get("status") == "success"),
        "failed_count": sum(1 for row in review_rows if row.get("status") == "failed"),
        "invalid_output_count": sum(1 for row in review_rows if row.get("status") == "invalid_output"),
        "rerun_recovered_count": sum(
            1 for row in review_rows if row.get("attempt_count", 0) > 1 and row.get("status") == "success"
        ),
    }
    dump_json(Path(args.output_dir) / "evaluations" / args.model_name / args.split / "run_status_summary.json", summary)
    print(summary)



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Abstract + SR-info analysis setting experiment")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare-data")
    prepare_parser.add_argument("--benchmark-path", required=True)
    prepare_parser.add_argument("--output-dir", required=True)
    prepare_parser.add_argument("--dev-ratio", type=float, default=0.2)
    prepare_parser.add_argument("--seed", type=int, default=20260519)
    prepare_parser.set_defaults(func=command_prepare)

    prepare_conditional_parser = subparsers.add_parser("prepare-conditional-data")
    prepare_conditional_parser.add_argument("--benchmark-path", required=True)
    prepare_conditional_parser.add_argument("--output-dir", required=True)
    prepare_conditional_parser.add_argument("--dev-ratio", type=float, default=0.2)
    prepare_conditional_parser.add_argument("--seed", type=int, default=20260519)
    prepare_conditional_parser.add_argument("--evidence-mode", choices=("abstract-only", "full-text"), required=True)
    prepare_conditional_parser.set_defaults(func=command_prepare_conditional)

    subset_conditional_parser = subparsers.add_parser("make-conditional-subset")
    subset_conditional_parser.add_argument("--dataset-path", required=True)
    subset_conditional_parser.add_argument("--output-path", required=True)
    subset_conditional_parser.add_argument("--task", choices=("data_type", "candidate_effect_measure", "comparisons", "arm_pairs", "comparisons_and_arm_pairs"), required=True)
    subset_conditional_parser.add_argument("--evidence-mode", choices=("abstract-only", "full-text"), required=True)
    subset_conditional_parser.add_argument("--subset-size", type=int, required=True)
    subset_conditional_parser.add_argument("--seed", type=int, default=20260519)
    subset_conditional_parser.set_defaults(func=command_make_conditional_subset)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--dataset-path", required=True)
    run_parser.add_argument("--output-dir", required=True)
    run_parser.add_argument("--backend", choices=("mock", "json_file", "openai"), default="mock")
    run_parser.add_argument("--json-source")
    run_parser.add_argument("--api-key")
    run_parser.add_argument("--base-url")
    run_parser.add_argument("--model-name", default="gpt-5-mini")
    run_parser.add_argument("--model-version", default="")
    run_parser.add_argument("--split", required=True)
    run_parser.add_argument("--concurrency", type=int, default=16)
    run_parser.add_argument("--timeout-seconds", type=int, default=120)
    run_parser.add_argument("--max-retries", type=int, default=0)
    run_parser.add_argument("--max-output-tokens", type=int, default=4000)
    run_parser.add_argument("--rerun-failed", action="store_true")
    run_parser.add_argument("--rerun-invalid-output", action="store_true")
    run_parser.add_argument("--rerun-empty-output", action="store_true")
    run_parser.add_argument("--review-id", action="append")
    run_parser.set_defaults(func=command_run)

    run_conditional_parser = subparsers.add_parser("run-conditional")
    run_conditional_parser.add_argument("--dataset-path", required=True)
    run_conditional_parser.add_argument("--output-dir", required=True)
    run_conditional_parser.add_argument("--backend", choices=("mock", "json_file", "openai"), default="mock")
    run_conditional_parser.add_argument("--json-source")
    run_conditional_parser.add_argument("--api-key")
    run_conditional_parser.add_argument("--base-url")
    run_conditional_parser.add_argument("--model-name", default="gpt-5-mini")
    run_conditional_parser.add_argument("--model-version", default="")
    run_conditional_parser.add_argument("--split", required=True)
    run_conditional_parser.add_argument("--task", choices=("data_type", "candidate_effect_measure", "comparisons", "arm_pairs", "comparisons_and_arm_pairs"), required=True)
    run_conditional_parser.add_argument("--evidence-mode", choices=("abstract-only", "full-text"), required=True)
    run_conditional_parser.add_argument("--evidence-strategy", choices=EVIDENCE_STRATEGIES, default=DEFAULT_EVIDENCE_STRATEGY)
    run_conditional_parser.add_argument("--decision-strategy", choices=DECISION_STRATEGIES, default=DEFAULT_DECISION_STRATEGY)
    run_conditional_parser.add_argument("--few-shot-set", default="")
    run_conditional_parser.add_argument("--concurrency", type=int, default=16)
    run_conditional_parser.add_argument("--timeout-seconds", type=int, default=120)
    run_conditional_parser.add_argument("--max-retries", type=int, default=0)
    run_conditional_parser.add_argument("--max-output-tokens", type=int, default=4000)
    run_conditional_parser.add_argument("--rerun-failed", action="store_true")
    run_conditional_parser.add_argument("--rerun-invalid-output", action="store_true")
    run_conditional_parser.add_argument("--rerun-empty-output", action="store_true")
    run_conditional_parser.add_argument("--review-id", action="append")
    run_conditional_parser.add_argument("--prompt-version", default="")
    run_conditional_parser.set_defaults(func=command_run_conditional)

    recanonicalize_parser = subparsers.add_parser("recanonicalize")
    recanonicalize_parser.add_argument("--dataset-path", required=True)
    recanonicalize_parser.add_argument("--output-dir", required=True)
    recanonicalize_parser.add_argument("--model-name", required=True)
    recanonicalize_parser.add_argument("--split", required=True)
    recanonicalize_parser.add_argument("--review-id", action="append")
    recanonicalize_parser.set_defaults(func=command_recanonicalize)

    eval_parser = subparsers.add_parser("evaluate")
    eval_parser.add_argument("--dataset-path", required=True)
    eval_parser.add_argument("--output-dir", required=True)
    eval_parser.add_argument("--model-name", required=True)
    eval_parser.add_argument("--split", required=True)
    eval_parser.add_argument("--prediction-mode", choices=("raw", "canonicalized"), default="canonicalized")
    eval_parser.add_argument("--match-threshold", type=float, default=0.65)
    eval_parser.add_argument("--error-sample-size", type=int, default=50)
    eval_parser.add_argument("--seed", type=int, default=20260519)
    eval_parser.set_defaults(func=command_evaluate)

    eval_conditional_parser = subparsers.add_parser("evaluate-conditional")
    eval_conditional_parser.add_argument("--dataset-path", required=True)
    eval_conditional_parser.add_argument("--output-dir", required=True)
    eval_conditional_parser.add_argument("--model-name", required=True)
    eval_conditional_parser.add_argument("--split", required=True)
    eval_conditional_parser.add_argument("--task", choices=("data_type", "candidate_effect_measure", "comparisons", "arm_pairs", "comparisons_and_arm_pairs"), required=True)
    eval_conditional_parser.add_argument("--evidence-mode", choices=("abstract-only", "full-text"), required=True)
    eval_conditional_parser.add_argument("--evidence-strategy", choices=EVIDENCE_STRATEGIES, default=DEFAULT_EVIDENCE_STRATEGY)
    eval_conditional_parser.add_argument("--decision-strategy", choices=DECISION_STRATEGIES, default=DEFAULT_DECISION_STRATEGY)
    eval_conditional_parser.add_argument("--few-shot-set", default="")
    eval_conditional_parser.add_argument("--prompt-version", default="")
    eval_conditional_parser.add_argument("--cascade-data-type-source", choices=("gold", "predicted"), default="gold")
    eval_conditional_parser.add_argument("--error-sample-size", type=int, default=50)
    eval_conditional_parser.add_argument("--seed", type=int, default=20260519)
    eval_conditional_parser.set_defaults(func=command_evaluate_conditional)

    judge_parser = subparsers.add_parser("judge-evaluate")
    judge_parser.add_argument("--dataset-path", required=True)
    judge_parser.add_argument("--output-dir", required=True)
    judge_parser.add_argument("--model-name", required=True)
    judge_parser.add_argument("--model-version", default="")
    judge_parser.add_argument("--split", required=True)
    judge_parser.add_argument("--prediction-mode", choices=("raw", "canonicalized"), default="canonicalized")
    judge_parser.add_argument("--backend", choices=("mock", "json_file", "openai"), default="mock")
    judge_parser.add_argument("--json-source")
    judge_parser.add_argument("--api-key")
    judge_parser.add_argument("--base-url")
    judge_parser.add_argument("--judge-model-name", default="")
    judge_parser.add_argument("--judge-model-version", default="")
    judge_parser.add_argument("--timeout-seconds", type=int, default=120)
    judge_parser.add_argument("--max-output-tokens", type=int, default=1200)
    judge_parser.add_argument("--concurrency", type=int, default=8)
    judge_parser.set_defaults(func=command_judge_evaluate)

    report_parser = subparsers.add_parser("report-runs")
    report_parser.add_argument("--output-dir", required=True)
    report_parser.add_argument("--model-name", required=True)
    report_parser.add_argument("--model-version", default="")
    report_parser.add_argument("--split", required=True)
    report_parser.set_defaults(func=command_report_runs)
    return parser



def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
