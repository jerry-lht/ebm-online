"""Helpers for maintaining the run index table."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

RUN_INDEX_COLUMNS = [
    "run_id",
    "method",
    "benchmark",
    "split",
    "input_setting",
    "provider",
    "model",
    "prompt_version",
    "examples_path",
    "prediction_path",
    "metric_path",
    "config_path",
    "provider_config_path",
    "started_at",
    "ended_at",
    "sample_count",
    "success_count",
    "error_count",
    "is_real_llm_run",
]


def _row_from_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {column: metadata.get(column) for column in RUN_INDEX_COLUMNS}


def update_run_index(path: str | Path, metadata: dict[str, Any]) -> None:
    """Upsert one run metadata row keyed by run_id into run_index.csv."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    row = _row_from_metadata(metadata)
    run_id = row.get("run_id")
    if not run_id:
        raise ValueError("run index row requires run_id")

    rows: list[dict[str, Any]] = []
    if target.exists():
        with target.open("r", encoding="utf-8", newline="") as handle:
            rows.extend(csv.DictReader(handle))

    normalized_rows: list[dict[str, Any]] = []
    replaced = False
    for existing in rows:
        if existing.get("run_id") == run_id:
            normalized_rows.append({column: row.get(column) for column in RUN_INDEX_COLUMNS})
            replaced = True
        else:
            normalized_rows.append(
                {column: existing.get(column, "") for column in RUN_INDEX_COLUMNS}
            )
    if not replaced:
        normalized_rows.append({column: row.get(column) for column in RUN_INDEX_COLUMNS})

    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RUN_INDEX_COLUMNS)
        writer.writeheader()
        writer.writerows(normalized_rows)
