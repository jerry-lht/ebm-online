"""Evaluate LLM PICO text/content predictions."""

from __future__ import annotations

import argparse
import csv
import os
import tempfile
from pathlib import Path
from typing import Any

from pico.io_utils import read_document_examples, read_jsonl, write_metrics
from pico.text_evaluate import TEXT_EVALUATOR_VERSION, evaluate_text_predictions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate LLM PICO text/content predictions.")
    parser.add_argument("--gold", required=True, help="Gold document examples JSONL.")
    parser.add_argument("--raw", required=True, help="Raw LLM response JSONL.")
    parser.add_argument("--output", required=True, help="Text metrics JSON output path.")
    parser.add_argument("--method", default="llm")
    parser.add_argument("--setting", default="default")
    parser.add_argument("--split", default="test")
    parser.add_argument("--tables-dir", default="results/tables")
    parser.add_argument("--force", action="store_true", help="Replace existing table rows for this run key.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    gold_examples = read_document_examples(args.gold)
    raw_rows = list(read_jsonl(args.raw))
    metrics = evaluate_text_predictions(gold_examples, raw_rows)
    metrics.update(
        {
            "text_evaluator_version": TEXT_EVALUATOR_VERSION,
            "inputs": {"gold_path": args.gold, "raw_path": args.raw},
            "method": args.method,
            "setting": args.setting,
            "split": args.split,
        }
    )
    write_metrics(args.output, metrics)
    _write_tables(
        tables_dir=Path(args.tables_dir),
        metrics=metrics,
        method=args.method,
        setting=args.setting,
        split=args.split,
        raw_path=args.raw,
        metric_path=args.output,
        force=args.force,
    )
    return 0


def _write_tables(
    tables_dir: Path,
    metrics: dict[str, Any],
    method: str,
    setting: str,
    split: str,
    raw_path: str,
    metric_path: str,
    force: bool,
) -> None:
    base = {
        "method": method,
        "setting": setting,
        "split": split,
        "raw_path": raw_path,
        "metric_path": metric_path,
    }
    f1_rows = [
        _metric_row(base, "text_exact_micro_f1", metrics["text_exact"]),
        _metric_row(base, "text_normalized_micro_f1", metrics["text_normalized"]),
    ]
    for prefix in ("text_exact", "text_normalized"):
        for label, label_metrics in metrics[prefix]["per_label"].items():
            f1_rows.append(_metric_row(base, f"{prefix}_{label}_f1", label_metrics))
    _upsert_rows(tables_dir / "llm_text_f1.csv", f1_rows, force)

    completeness = metrics["pio_completeness"]
    completeness_rows = [
        {
            **base,
            "metric_name": "pio_complete_document_rate",
            "label": "PIO",
            "docs_with_gold": completeness["docs_with_any_pio_gold"],
            "complete_docs": completeness["pio_complete_docs"],
            "complete_rate": completeness["pio_complete_document_rate"],
        }
    ]
    for label, values in completeness["per_label"].items():
        completeness_rows.append(
            {
                **base,
                "metric_name": "label_complete_document_rate",
                "label": label,
                "docs_with_gold": values["docs_with_gold"],
                "complete_docs": values["complete_docs"],
                "complete_rate": values["complete_rate"],
            }
        )
    _upsert_rows(tables_dir / "llm_pio_completeness.csv", completeness_rows, force)


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
            f"{conflict['metric_name']}/{conflict['raw_path']}; pass --force to replace"
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
        str(row["metric_name"]),
        str(row["raw_path"]),
    )


if __name__ == "__main__":
    raise SystemExit(main())
