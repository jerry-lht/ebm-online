"""I/O helpers for GRADE evaluation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from benchmark.online_pipeline.shared.jsonl import read_jsonl


def load_dataset(dataset: str | Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    dataset_dir = Path(dataset)
    instances = read_jsonl(dataset_dir / "instances.jsonl")
    gold_rows = read_jsonl(dataset_dir / "gold.jsonl")
    gold_by_id = {str(row["instance_id"]): row for row in gold_rows}
    return instances, gold_by_id
