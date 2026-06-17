"""I/O helpers for Meta Analysis evaluation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from benchmark.online_pipeline.shared.jsonl import read_jsonl


def load_dataset(dataset_dir: str | Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    resolved = Path(dataset_dir)
    instances = read_jsonl(resolved / "instances.jsonl")
    gold_rows = read_jsonl(resolved / "gold.jsonl")
    return instances, {str(row["instance_id"]): row for row in gold_rows}
