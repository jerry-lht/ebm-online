"""Validate raw q2pico LLM outputs into normalized slot predictions."""

from __future__ import annotations

import argparse
import csv
import os
import tempfile
from pathlib import Path
from typing import Any

from q2pico.io_utils import read_jsonl, read_question_examples, write_metrics, write_slot_predictions
from q2pico.schemas import parse_label_scope
from q2pico.slot_validate import LLM_VALIDATOR_VERSION, validate_slot_predictions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate raw Question-to-PICO slot predictions.")
    parser.add_argument("--examples", required=True, help="Prepared question examples JSONL.")
    parser.add_argument("--raw", required=True, help="Raw LLM response JSONL.")
    parser.add_argument("--valid-output", required=True, help="Validated slot JSONL output path.")
    parser.add_argument("--quality-output", required=True, help="Validation quality JSON output path.")
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

    examples = read_question_examples(args.examples)
    raw_rows = list(read_jsonl(args.raw))
    labels = parse_label_scope(args.labels)
    predictions, quality = validate_slot_predictions(examples, raw_rows, labels=labels)
    quality.update(
        {
            "validator_version": LLM_VALIDATOR_VERSION,
            "inputs": {"examples_path": args.examples, "raw_path": args.raw},
            "method": args.method,
            "setting": args.setting,
            "split": args.split,
            "labels": list(labels),
        }
    )
    write_slot_predictions(args.valid_output, predictions)
    write_metrics(args.quality_output, quality)
    _write_quality_table(
        tables_dir=Path(args.tables_dir),
        quality=quality,
        method=args.method,
        setting=args.setting,
        split=args.split,
        raw_path=args.raw,
        valid_path=args.valid_output,
        quality_path=args.quality_output,
        force=args.force,
    )
    return 0


def _write_quality_table(
    *,
    tables_dir: Path,
    quality: dict[str, Any],
    method: str,
    setting: str,
    split: str,
    raw_path: str,
    valid_path: str,
    quality_path: str,
    force: bool,
) -> None:
    base = {
        "method": method,
        "setting": setting,
        "split": split,
        "raw_path": raw_path,
        "valid_path": valid_path,
        "quality_path": quality_path,
        "validator_version": quality["validator_version"],
    }
    rows = []
    for metric_name in (
        "invalid_json_rate",
        "schema_invalid_rate",
        "non_list_slot_rate",
        "non_string_item_rate",
        "duplicate_value_rate",
        "empty_value_rate",
    ):
        rows.append({**base, "metric_name": metric_name, "metric_value": quality[metric_name]})
    for metric_name in ("raw_rows", "response_items", "written_values"):
        rows.append({**base, "metric_name": metric_name, "metric_value": quality["counts"][metric_name]})
    _upsert_rows(tables_dir / "llm_quality.csv", rows, force)


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
