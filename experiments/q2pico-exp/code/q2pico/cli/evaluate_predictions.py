"""Evaluate validated q2pico slot predictions."""

from __future__ import annotations

import argparse
import csv
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from q2pico.io_utils import read_question_examples, read_slot_predictions, write_metrics
from q2pico.schemas import parse_label_scope
from q2pico.slot_evaluate import SLOT_EVALUATOR_VERSION, evaluate_slot_predictions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate Question-to-PICO slot predictions.")
    parser.add_argument("--gold", required=True, help="Gold question examples JSONL.")
    parser.add_argument("--pred", required=True, help="Validated slot prediction JSONL.")
    parser.add_argument("--output", required=True, help="Metrics JSON output path.")
    parser.add_argument("--method", default="llm")
    parser.add_argument("--setting", default="default")
    parser.add_argument("--split", default="test59")
    parser.add_argument("--labels", default="P,I,C,O", help="Comma-separated label scope, e.g. P,I")
    parser.add_argument("--tables-dir", default="results/tables")
    parser.add_argument("--force", action="store_true", help="Replace existing table rows for this run key.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    gold_examples = read_question_examples(args.gold)
    predictions = read_slot_predictions(args.pred)
    labels = parse_label_scope(args.labels)
    metrics = evaluate_slot_predictions(gold_examples, predictions, labels=labels)
    metrics.update(
        {
            "slot_evaluator_version": SLOT_EVALUATOR_VERSION,
            "inputs": {"gold_path": args.gold, "pred_path": args.pred},
            "method": args.method,
            "setting": args.setting,
            "split": args.split,
            "labels": list(labels),
        }
    )
    write_metrics(args.output, metrics)
    _write_tables(
        tables_dir=Path(args.tables_dir),
        metrics=metrics,
        method=args.method,
        setting=args.setting,
        split=args.split,
        pred_path=args.pred,
        metric_path=args.output,
        force=args.force,
    )
    return 0


def _write_tables(
    *,
    tables_dir: Path,
    metrics: dict[str, Any],
    method: str,
    setting: str,
    split: str,
    pred_path: str,
    metric_path: str,
    force: bool,
) -> None:
    base = {
        "method": method,
        "setting": setting,
        "split": split,
        "pred_path": pred_path,
        "metric_path": metric_path,
    }
    f1_rows = [
        _metric_row(base, "slot_exact_micro_f1", metrics["slot_exact"]),
        _metric_row(base, "slot_normalized_micro_f1", metrics["slot_normalized"]),
    ]
    for prefix in ("slot_exact", "slot_normalized"):
        for label, label_metrics in metrics[prefix]["per_label"].items():
            f1_rows.append(_metric_row(base, f"{prefix}_{label}_f1", label_metrics))
    _upsert_rows(tables_dir / "llm_slot_f1.csv", f1_rows, force)

    completeness = metrics["pico_completeness"]
    completeness_rows = [
        {
            **base,
            "metric_name": "pico_complete_question_rate",
            "label": "PICO",
            "questions_with_gold": completeness["questions_with_any_gold"],
            "complete_questions": completeness["complete_questions"],
            "complete_rate": completeness["pico_complete_question_rate"],
        }
    ]
    for label, values in completeness["per_label"].items():
        completeness_rows.append(
            {
                **base,
                "metric_name": "label_complete_question_rate",
                "label": label,
                "questions_with_gold": values["questions_with_gold"],
                "complete_questions": values["complete_questions"],
                "complete_rate": values["complete_rate"],
            }
        )
    _upsert_rows(tables_dir / "llm_slot_completeness.csv", completeness_rows, force)

    run_index_rows = [
        {
            "method": method,
            "setting": setting,
            "split": split,
            "pred_path": pred_path,
            "metric_path": metric_path,
            "evaluation_type": "slot_metrics",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ]
    _upsert_rows(tables_dir / "run_index.csv", run_index_rows, force)


def _metric_row(base: dict[str, str], metric_name: str, metric: dict[str, Any]) -> dict[str, Any]:
    return {
        **base,
        "metric_name": metric_name,
        "precision": metric["precision"],
        "recall": metric["recall"],
        "f1": metric["f1"],
        "tp": metric["tp"],
        "fp": metric["fp"],
        "fn": metric["fn"],
    }


def _upsert_rows(path: Path, new_rows: list[dict[str, Any]], force: bool) -> None:
    if not new_rows:
        return
    fieldnames = list(new_rows[0].keys())
    rows = _read_csv_rows(path, fieldnames)
    new_keys = {_row_key(row) for row in new_rows}
    existing_conflicts = [row for row in rows if _row_key(row) in new_keys]
    if existing_conflicts and not force:
        conflict = existing_conflicts[0]
        raise ValueError(
            "Table row already exists for "
            f"{conflict['method']}/{conflict['setting']}/{conflict['split']}/"
            f"{conflict.get('metric_name', conflict.get('evaluation_type'))}/{conflict['pred_path']}; pass --force to replace"
        )
    rows = [row for row in rows if _row_key(row) not in new_keys]
    rows.extend(new_rows)
    _atomic_write_csv(path, fieldnames, rows)


def _read_csv_rows(path: Path, fieldnames: list[str]) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != fieldnames:
            raise ValueError(f"Unexpected CSV header in {path}: {reader.fieldnames}")
        return list(reader)


def _atomic_write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="",
        dir=path.parent,
        delete=False,
    ) as handle:
        temp_name = handle.name
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temp_name, path)


def _row_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row["method"]),
        str(row["setting"]),
        str(row["split"]),
        str(row.get("metric_name", row.get("evaluation_type"))),
        str(row["pred_path"]),
    )


if __name__ == "__main__":
    raise SystemExit(main())
