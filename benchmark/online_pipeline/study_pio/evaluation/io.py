"""I/O helpers for Study PIO evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from benchmark.online_pipeline.shared.jsonl import read_jsonl


def load_dataset(dataset_dir: str | Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    resolved = Path(dataset_dir)
    instances = read_jsonl(resolved / "instances.jsonl")
    gold_rows = read_jsonl(resolved / "gold.jsonl")
    article_index_rows = read_jsonl(resolved / "article_index.jsonl")
    dataset_root = _dataset_root_from_split(resolved)
    articles = {}
    for row in article_index_rows:
        article_id = str(row["article_id"])
        article_path = dataset_root / str(row["article_path"])
        articles[article_id] = json.loads(article_path.read_text(encoding="utf-8"))
    return instances, {str(row["instance_id"]): row for row in gold_rows}, articles


def _dataset_root_from_split(dataset_dir: Path) -> Path:
    if dataset_dir.parent.name == "splits":
        return dataset_dir.parent.parent
    return dataset_dir
