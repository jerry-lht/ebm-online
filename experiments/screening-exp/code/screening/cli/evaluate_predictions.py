"""CLI for evaluation of screening predictions against gold labels."""

from __future__ import annotations

import argparse
from pathlib import Path

from screening.evaluation.decision import evaluate_predictions
from screening.evaluation.tables import update_automation_readiness_table
from screening.io_utils import read_json, read_model_jsonl, read_prediction_jsonl, write_json
from screening.paths import results_root
from screening.schemas import ScreeningExample


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m screening.cli.evaluate_predictions",
        description="Evaluate screening predictions against gold labels.",
    )
    parser.add_argument(
        "--predictions",
        required=True,
        help="Path to prediction JSONL (minimal abstract-only or richer schema).",
    )
    parser.add_argument(
        "--gold",
        required=True,
        help="Path to ScreeningExample JSONL with gold_decision populated.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path for metrics JSON.",
    )
    parser.add_argument(
        "--defaults-config",
        help="Optional experiment defaults YAML.",
    )
    parser.add_argument(
        "--high-confidence-threshold",
        type=float,
        help="Deprecated compatibility flag. Ignored by the binary-only evaluator.",
    )
    parser.add_argument(
        "--method",
        required=True,
        help="Method name written into metrics metadata.",
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Run identifier written into metrics metadata and readiness table.",
    )
    parser.add_argument(
        "--readiness-profile",
        choices=("stage1", "full_text", "two_stage", "none"),
        default="none",
        help="Automation-readiness profile to evaluate.",
    )
    parser.add_argument(
        "--workload-mode",
        choices=("auto", "zero", "one", "from_predictions"),
        default="auto",
        help="How to resolve full-text workload metrics.",
    )
    parser.add_argument(
        "--reference-metrics",
        help="Optional metrics JSON path for the full-text one-step reference used by two_stage readiness.",
    )
    parser.add_argument(
        "--append-readiness-table",
        dest="append_readiness_table",
        action="store_true",
        default=True,
        help="Append or update results/tables/automation_readiness.csv using the computed metrics.",
    )
    parser.add_argument(
        "--no-append-readiness-table",
        dest="append_readiness_table",
        action="store_false",
        help="Skip updating results/tables/automation_readiness.csv.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    predictions = read_prediction_jsonl(args.predictions)
    examples = read_model_jsonl(args.gold, ScreeningExample)
    reference_metrics = read_json(args.reference_metrics) if args.reference_metrics else None
    metrics = evaluate_predictions(
        predictions=predictions,
        examples=examples,
        run_id=args.run_id,
        method=args.method,
        predictions_path=args.predictions,
        gold_path=args.gold,
        readiness_profile=args.readiness_profile,
        workload_mode=args.workload_mode,
        reference_metrics=reference_metrics,
    )
    write_json(args.output, metrics)
    if args.append_readiness_table:
        readiness_path = results_root / "tables" / "automation_readiness.csv"
        update_automation_readiness_table(readiness_path, metrics)

    print(f"metrics_json: {Path(args.output)}")
    if args.append_readiness_table:
        print(f"automation_readiness_csv: {results_root / 'tables' / 'automation_readiness.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
