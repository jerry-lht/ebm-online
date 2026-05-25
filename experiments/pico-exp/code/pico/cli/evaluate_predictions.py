"""Evaluate PICO predictions against prepared gold examples."""

from __future__ import annotations

import argparse
import csv
import os
import tempfile
from pathlib import Path
from typing import Any

from pico.conversions import blurb_bio_labels_to_spans
from pico.evaluate import EVALUATOR_VERSION, evaluate_all
from pico.io_utils import read_document_examples, read_jsonl, read_span_predictions, write_metrics
from pico.schemas import Span


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate PICO predictions against gold examples.")
    parser.add_argument("--gold", required=True, help="Gold document examples JSONL.")
    parser.add_argument("--pred", required=True, help="Prediction JSONL.")
    parser.add_argument("--output", required=True, help="Metrics JSON output path.")
    parser.add_argument("--pred-format", choices=("spans", "bio"), default="spans")
    parser.add_argument("--method", default="unknown")
    parser.add_argument("--setting", default="default")
    parser.add_argument("--split", default="test")
    parser.add_argument("--tables-dir", default="results/tables")
    parser.add_argument("--force", action="store_true", help="Replace existing table rows for this run key.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    gold_examples = read_document_examples(args.gold)
    gold_by_doc = {example.doc_id: example for example in gold_examples}
    if len(gold_by_doc) != len(gold_examples):
        raise ValueError("Gold examples contain duplicate doc_id values")

    bio_predictions: dict[str, list[str]] | None = None
    if args.pred_format == "spans":
        span_predictions = read_span_predictions(args.pred)
    else:
        bio_predictions = _read_bio_predictions(args.pred)
        span_predictions = _bio_predictions_to_spans(gold_by_doc, bio_predictions)

    metrics = evaluate_all(gold_examples, span_predictions, bio_predictions)
    metrics.update(
        {
            "evaluator_version": EVALUATOR_VERSION,
            "inputs": {
                "gold_path": args.gold,
                "prediction_path": args.pred,
                "prediction_format": args.pred_format,
            },
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
        prediction_path=args.pred,
        metric_path=args.output,
        force=args.force,
    )
    return 0


def _read_bio_predictions(path: str) -> dict[str, list[str]]:
    predictions: dict[str, list[str]] = {}
    for row in read_jsonl(path):
        doc_id = row.get("doc_id")
        labels = row.get("bio_labels")
        if not isinstance(doc_id, str):
            raise ValueError(f"BIO prediction row in {path} is missing string doc_id")
        if doc_id in predictions:
            raise ValueError(f"Duplicate BIO prediction doc_id: {doc_id!r}")
        if not isinstance(labels, list) or not all(isinstance(label, str) for label in labels):
            raise ValueError(f"BIO prediction for {doc_id!r} must contain string list bio_labels")
        predictions[doc_id] = labels
    return predictions


def _bio_predictions_to_spans(
    gold_by_doc: dict[str, Any],
    bio_predictions: dict[str, list[str]],
) -> list[Span]:
    spans: list[Span] = []
    for doc_id, labels in bio_predictions.items():
        example = gold_by_doc.get(doc_id)
        if example is None:
            raise ValueError(f"BIO prediction references unknown doc_id: {doc_id!r}")
        spans.extend(
            blurb_bio_labels_to_spans(
                doc_id=doc_id,
                bio_labels=labels,
                tokens=example.tokens,
                token_offsets=example.token_offsets,
                abstract=example.abstract,
            )
        )
    return spans


def _write_tables(
    tables_dir: Path,
    metrics: dict[str, Any],
    method: str,
    setting: str,
    split: str,
    prediction_path: str,
    metric_path: str,
    force: bool,
) -> None:
    tables_dir.mkdir(parents=True, exist_ok=True)
    base = {
        "method": method,
        "setting": setting,
        "split": split,
        "prediction_path": prediction_path,
        "metric_path": metric_path,
    }

    _upsert_rows(
        tables_dir / "main_blurb_token_f1.csv",
        [_metric_row(base, "blurb_token_micro_f1", metrics["blurb_token"])],
        force,
    )
    _upsert_rows(
        tables_dir / "main_span_f1.csv",
        [
            _metric_row(base, "exact_span_micro_f1", metrics["exact_span"]),
            _metric_row(base, "relaxed_span_micro_f1", metrics["relaxed_span"]),
            _metric_row(base, "overlap_subset_exact_span_micro_f1", metrics["overlap_subset"]),
        ],
        force,
    )

    per_label_rows: list[dict[str, Any]] = []
    for prefix in ("exact_span", "relaxed_span", "overlap_subset", "blurb_token"):
        for label, label_metrics in metrics[prefix]["per_label"].items():
            per_label_rows.append(_metric_row(base, f"{prefix}_{label}_f1", label_metrics))
    _upsert_rows(tables_dir / "per_label_f1.csv", per_label_rows, force)

    _upsert_rows(
        tables_dir / "run_index.csv",
        [
            {
                **base,
                "metric_name": "run",
                "precision": "",
                "recall": "",
                "f1": "",
                "tp": "",
                "fp": "",
                "fn": "",
            }
        ],
        force,
    )


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
    fieldnames = [
        "method",
        "setting",
        "split",
        "metric_name",
        "precision",
        "recall",
        "f1",
        "tp",
        "fp",
        "fn",
        "prediction_path",
        "metric_path",
    ]
    rows = _read_csv_rows(path, fieldnames)
    new_keys = {_row_key(row) for row in new_rows}
    existing_conflicts = [row for row in rows if _row_key(row) in new_keys]
    if existing_conflicts and not force:
        conflict = existing_conflicts[0]
        raise ValueError(
            "Table row already exists for "
            f"{conflict['method']}/{conflict['setting']}/{conflict['split']}/"
            f"{conflict['metric_name']}/{conflict['prediction_path']}; pass --force to replace"
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
        str(row["prediction_path"]),
    )


if __name__ == "__main__":
    raise SystemExit(main())
