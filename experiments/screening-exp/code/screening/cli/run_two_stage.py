"""CLI for composing existing predictions into a two-stage screening run."""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from screening.evaluation.decision import evaluate_predictions
from screening.evaluation.tables import update_automation_readiness_table
from screening.io_utils import (
    read_json,
    read_model_jsonl,
    read_prediction_jsonl,
    write_json,
    write_jsonl,
    write_model_jsonl,
)
from screening.paths import results_root
from screening.pipeline.two_stage import TWO_STAGE_POLICY_NAME, combine_two_stage_predictions
from screening.run_index import update_run_index
from screening.schemas import RunMetadata, ScreeningExample

DEFAULT_METHOD = "two_stage"

COMPARISON_COLUMNS = [
    "pipeline",
    "run_id",
    "TP",
    "TN",
    "FP",
    "FN",
    "Total",
    "Sensitivity",
    "Specificity",
    "Precision",
    "Balanced Accuracy",
    "Macro F1",
    "Stage 2 workload",
    "workload reduction",
    "prediction path",
    "metric path",
]


def _default_output_dir(*, examples: list[ScreeningExample], run_id: str) -> Path:
    benchmark = examples[0].benchmark
    split = examples[0].split
    return results_root / "preds" / benchmark / split / DEFAULT_METHOD / run_id


def _metrics_path(*, examples: list[ScreeningExample], run_id: str) -> Path:
    benchmark = examples[0].benchmark
    split = examples[0].split
    return results_root / "metrics" / benchmark / split / DEFAULT_METHOD / f"{run_id}.json"


def _table_value(value: Any) -> Any:
    return "" if value is None else value


def _comparison_row(
    *,
    pipeline: str,
    metrics: dict[str, Any],
    prediction_path: str | None,
    metric_path: str,
) -> dict[str, Any]:
    counts = metrics.get("counts", {})
    decision_metrics = metrics.get("decision_metrics", {})
    workload_metrics = metrics.get("workload_metrics", {})
    metadata = metrics.get("metadata", {})
    return {
        "pipeline": pipeline,
        "run_id": metadata.get("run_id"),
        "TP": _table_value(counts.get("tp")),
        "TN": _table_value(counts.get("tn")),
        "FP": _table_value(counts.get("fp")),
        "FN": _table_value(counts.get("fn")),
        "Total": _table_value(counts.get("total")),
        "Sensitivity": _table_value(decision_metrics.get("sensitivity")),
        "Specificity": _table_value(decision_metrics.get("specificity")),
        "Precision": _table_value(decision_metrics.get("precision")),
        "Balanced Accuracy": _table_value(decision_metrics.get("balanced_accuracy")),
        "Macro F1": _table_value(decision_metrics.get("macro_f1")),
        "Stage 2 workload": _table_value(workload_metrics.get("full_text_workload")),
        "workload reduction": _table_value(workload_metrics.get("full_text_workload_reduction")),
        "prediction path": prediction_path or metadata.get("predictions_path") or "",
        "metric path": metric_path,
    }


def _upsert_comparison_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_rows: list[dict[str, Any]] = []
    if path.exists():
        with path.open("r", encoding="utf-8", newline="") as handle:
            existing_rows.extend(csv.DictReader(handle))

    by_run_id: dict[str, dict[str, Any]] = {
        row.get("run_id", ""): {column: row.get(column, "") for column in COMPARISON_COLUMNS}
        for row in existing_rows
        if row.get("run_id")
    }
    for row in rows:
        run_id = row.get("run_id")
        if not run_id:
            raise ValueError("comparison table rows require run_id")
        by_run_id[str(run_id)] = {column: row.get(column, "") for column in COMPARISON_COLUMNS}

    ordered = sorted(by_run_id.values(), key=lambda row: (row.get("pipeline", ""), row.get("run_id", "")))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COMPARISON_COLUMNS)
        writer.writeheader()
        writer.writerows(ordered)


def _pipeline_label_for_reference(metrics: dict[str, Any], fallback_method: str) -> str:
    metadata = metrics.get("metadata", {})
    method = metadata.get("method") or fallback_method
    run_id = metadata.get("run_id") or ""
    if method == "direct_criteria_aware" or "direct" in run_id:
        return "one-step direct abs+full"
    if method == "criterion_wise_evidence_grounded" or "criterion" in run_id:
        return "one-step criteria raw v3"
    return f"one-step {method}"


def _pipeline_label_for_two_stage(stage2_method: str) -> str:
    if stage2_method == "direct_criteria_aware" or "direct" in stage2_method:
        return "two-stage abstract-only -> direct abs+full"
    if stage2_method == "criterion_wise_evidence_grounded" or "criteria" in stage2_method:
        return "two-stage abstract-only -> criteria raw v3"
    return f"two-stage abstract-only -> {stage2_method}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m screening.cli.run_two_stage",
        description="Compose abstract-only stage1 predictions with stage2 full-text predictions.",
    )
    parser.add_argument("--stage1-examples", required=True, help="Stage 1 ScreeningExample JSONL.")
    parser.add_argument("--stage1-predictions", required=True, help="Stage 1 prediction JSONL.")
    parser.add_argument("--stage2-examples", required=True, help="Stage 2 ScreeningExample JSONL.")
    parser.add_argument("--stage2-predictions", required=True, help="Stage 2 prediction JSONL.")
    parser.add_argument("--stage2-method", required=True, help="Method name for Stage 2 predictions.")
    parser.add_argument("--run-id", required=True, help="Two-stage run identifier.")
    parser.add_argument("--output-dir", help="Output directory for two-stage prediction artifacts.")
    parser.add_argument("--reference-metrics", help="One-step Stage 2 reference metrics JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    started_at = datetime.now(timezone.utc)
    stage1_examples = read_model_jsonl(args.stage1_examples, ScreeningExample)
    stage2_examples = read_model_jsonl(args.stage2_examples, ScreeningExample)
    stage1_predictions = read_prediction_jsonl(args.stage1_predictions)
    stage2_predictions = read_prediction_jsonl(args.stage2_predictions)
    if not stage2_examples:
        raise ValueError("stage2 examples must not be empty")
    stage2_input_setting = stage2_examples[0].input_setting

    output_dir = Path(args.output_dir) if args.output_dir else _default_output_dir(
        examples=stage2_examples,
        run_id=args.run_id,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = output_dir / "predictions.jsonl"
    stage1_actions_path = output_dir / "stage1_actions.jsonl"
    stage2_inputs_path = output_dir / "stage2_inputs.jsonl"
    missing_stage2_path = output_dir / "missing_stage2_predictions.jsonl"
    metadata_path = output_dir / "run_metadata.json"
    metric_path = _metrics_path(examples=stage2_examples, run_id=args.run_id)

    artifacts = combine_two_stage_predictions(
        stage1_examples=stage1_examples,
        stage1_predictions=stage1_predictions,
        stage2_examples=stage2_examples,
        stage2_predictions=stage2_predictions,
        stage2_method=args.stage2_method,
        run_id=args.run_id,
        stage1_examples_path=args.stage1_examples,
        stage1_predictions_path=args.stage1_predictions,
        stage2_examples_path=args.stage2_examples,
        stage2_predictions_path=args.stage2_predictions,
    )

    write_model_jsonl(predictions_path, artifacts.predictions)
    write_jsonl(stage1_actions_path, artifacts.stage1_actions)
    write_model_jsonl(stage2_inputs_path, artifacts.stage2_inputs)
    write_jsonl(missing_stage2_path, artifacts.missing_stage2_predictions)

    reference_metrics = read_json(args.reference_metrics) if args.reference_metrics else None
    metrics = evaluate_predictions(
        predictions=artifacts.predictions,
        examples=stage2_examples,
        run_id=args.run_id,
        method=DEFAULT_METHOD,
        predictions_path=str(predictions_path),
        gold_path=args.stage2_examples,
        benchmark=stage2_examples[0].benchmark,
        split=stage2_examples[0].split,
        input_setting=stage2_input_setting.value if stage2_input_setting is not None else None,
        readiness_profile="two_stage",
        workload_mode="from_predictions",
        reference_metrics=reference_metrics,
    )
    write_json(metric_path, metrics)
    update_automation_readiness_table(results_root / "tables" / "automation_readiness.csv", metrics)

    ended_at = datetime.now(timezone.utc)
    metadata = RunMetadata(
        run_id=args.run_id,
        method=DEFAULT_METHOD,
        benchmark=stage2_examples[0].benchmark,
        split=stage2_examples[0].split,
        input_setting=stage2_input_setting,
        provider=None,
        model=None,
        prompt_version=None,
        examples_path=Path(args.stage2_examples),
        prediction_path=predictions_path,
        metric_path=metric_path,
        command=[sys.executable, "-m", "screening.cli.run_two_stage", *(argv or sys.argv[1:])],
        started_at=started_at,
        ended_at=ended_at,
        sample_count=len(stage2_examples),
        success_count=len(artifacts.predictions),
        error_count=0,
        is_real_llm_run=False,
        metadata={
            "output_dir": str(output_dir),
            "policy": TWO_STAGE_POLICY_NAME,
            "stage1_examples_path": args.stage1_examples,
            "stage1_predictions_path": args.stage1_predictions,
            "stage2_examples_path": args.stage2_examples,
            "stage2_predictions_path": args.stage2_predictions,
            "stage2_method": args.stage2_method,
            "stage2_input_count": len(artifacts.stage2_inputs),
            "missing_stage2_prediction_count": len(artifacts.missing_stage2_predictions),
            "workload_mode": "from_predictions",
            "reference_metrics_path": args.reference_metrics,
        },
    )
    write_json(metadata_path, metadata.model_dump(mode="json"))
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

    comparison_rows = [
        _comparison_row(
            pipeline=_pipeline_label_for_two_stage(args.stage2_method),
            metrics=metrics,
            prediction_path=str(predictions_path),
            metric_path=str(metric_path),
        )
    ]
    if reference_metrics is not None and args.reference_metrics:
        comparison_rows.append(
            _comparison_row(
                pipeline=_pipeline_label_for_reference(reference_metrics, args.stage2_method),
                metrics=reference_metrics,
                prediction_path=reference_metrics.get("metadata", {}).get("predictions_path"),
                metric_path=args.reference_metrics,
            )
        )
    comparison_path = results_root / "tables" / "one_step_vs_two_stage.csv"
    _upsert_comparison_rows(comparison_path, comparison_rows)

    print(f"predictions_jsonl: {predictions_path}")
    print(f"stage1_actions_jsonl: {stage1_actions_path}")
    print(f"stage2_inputs_jsonl: {stage2_inputs_path}")
    print(f"missing_stage2_predictions_jsonl: {missing_stage2_path}")
    print(f"run_metadata_json: {metadata_path}")
    print(f"metrics_json: {metric_path}")
    print(f"one_step_vs_two_stage_csv: {comparison_path}")
    print(f"run_index_csv: {results_root / 'tables' / 'run_index.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
