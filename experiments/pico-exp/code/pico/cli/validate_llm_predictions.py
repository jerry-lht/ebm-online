"""Validate raw LLM PICO responses into span predictions."""

from __future__ import annotations

import argparse
import csv
import os
import tempfile
from pathlib import Path
from typing import Any

from pico.io_utils import read_document_examples, read_jsonl, write_metrics, write_span_predictions
from pico.validate_llm import LLM_VALIDATOR_VERSION, validate_llm_predictions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate raw LLM responses into PICO span JSONL.")
    parser.add_argument("--examples", required=True, help="Prepared document examples JSONL.")
    parser.add_argument("--raw", required=True, help="Raw LLM response JSONL.")
    parser.add_argument("--valid-output", required=True, help="Validated span JSONL output path.")
    parser.add_argument("--quality-output", required=True, help="Validator quality metrics JSON output path.")
    parser.add_argument("--tables-dir", default="results/tables")
    parser.add_argument("--method", default="llm")
    parser.add_argument("--setting", default="default")
    parser.add_argument("--split", default="test")
    parser.add_argument("--force", action="store_true", help="Replace existing table rows for this run key.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    examples = read_document_examples(args.examples)
    raw_rows = list(read_jsonl(args.raw))
    valid_spans, quality = validate_llm_predictions(examples, raw_rows)
    quality.update(
        {
            "inputs": {
                "examples_path": args.examples,
                "raw_path": args.raw,
            },
            "outputs": {
                "valid_output": args.valid_output,
                "quality_output": args.quality_output,
            },
            "method": args.method,
            "setting": args.setting,
            "split": args.split,
        }
    )

    write_span_predictions(args.valid_output, valid_spans)
    write_metrics(args.quality_output, quality)
    _write_quality_table(
        tables_dir=Path(args.tables_dir),
        quality=quality,
        method=args.method,
        setting=args.setting,
        split=args.split,
        raw_path=args.raw,
        quality_path=args.quality_output,
        valid_path=args.valid_output,
        force=args.force,
    )
    return 0


def _write_quality_table(
    tables_dir: Path,
    quality: dict[str, Any],
    method: str,
    setting: str,
    split: str,
    raw_path: str,
    quality_path: str,
    valid_path: str,
    force: bool,
) -> None:
    tables_dir.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "method": method,
            "setting": setting,
            "split": split,
            "raw_path": raw_path,
            "quality_path": quality_path,
            "valid_path": valid_path,
            "validator_version": LLM_VALIDATOR_VERSION,
            "invalid_json_rate": quality["invalid_json_rate"],
            "schema_invalid_rate": quality["schema_invalid_rate"],
            "non_extractive_span_rate": quality["non_extractive_span_rate"],
            "invalid_offset_rate": quality["invalid_offset_rate"],
            "ambiguous_match_rate": quality["ambiguous_match_rate"],
            "duplicate_span_rate": quality["duplicate_span_rate"],
            "overlap_conflict_document_rate": quality["overlap_conflict_document_rate"],
            "overlap_conflict_token_rate": quality["overlap_conflict_token_rate"],
            "raw_rows": quality["counts"]["raw_rows"],
            "response_items": quality["counts"]["response_items"],
            "written_spans": quality["counts"]["written_spans"],
        }
    ]
    _upsert_rows(tables_dir / "llm_quality.csv", rows, force)


def _upsert_rows(path: Path, new_rows: list[dict[str, Any]], force: bool) -> None:
    fieldnames = [
        "method",
        "setting",
        "split",
        "raw_path",
        "quality_path",
        "valid_path",
        "validator_version",
        "invalid_json_rate",
        "schema_invalid_rate",
        "non_extractive_span_rate",
        "invalid_offset_rate",
        "ambiguous_match_rate",
        "duplicate_span_rate",
        "overlap_conflict_document_rate",
        "overlap_conflict_token_rate",
        "raw_rows",
        "response_items",
        "written_spans",
    ]
    rows = _read_csv_rows(path, fieldnames)
    new_keys = {_row_key(row) for row in new_rows}
    existing_conflicts = [row for row in rows if _row_key(row) in new_keys]
    if existing_conflicts and not force:
        conflict = existing_conflicts[0]
        raise ValueError(
            "Table row already exists for "
            f"{conflict['method']}/{conflict['setting']}/{conflict['split']}/{conflict['raw_path']}; "
            "pass --force to replace"
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


def _row_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row["method"]),
        str(row["setting"]),
        str(row["split"]),
        str(row["raw_path"]),
    )


if __name__ == "__main__":
    raise SystemExit(main())
