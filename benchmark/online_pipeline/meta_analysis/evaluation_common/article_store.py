"""Shared article loading for Meta Analysis Subtask 2 evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from benchmark.online_pipeline.shared.jsonl import read_jsonl


def load_article_index(dataset_dir: str | Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    resolved = Path(dataset_dir)
    root = _dataset_root(resolved)
    rows = read_jsonl(root / "shared" / "article_index.jsonl")
    by_article_id = {str(row["article_id"]): row for row in rows}
    by_study_id = {str(row["study_id"]): row for row in rows}
    return by_article_id, by_study_id


def load_articles_for_instance(*, dataset_dir: str | Path, instance: dict[str, Any]) -> list[dict[str, Any]]:
    root = _dataset_root(Path(dataset_dir))
    article_index, _ = load_article_index(root)
    payloads: list[dict[str, Any]] = []
    for article_id in instance.get("article_ids") or []:
        row = article_index.get(str(article_id))
        if not row:
            continue
        payload_path = root / row["relative_path"]
        if not payload_path.exists():
            continue
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        payloads.append(payload)
    return payloads


def _dataset_root(dataset_dir: Path) -> Path:
    if dataset_dir.parent.name == "splits":
        return dataset_dir.parent.parent
    if dataset_dir.name == "splits":
        return dataset_dir.parent
    return dataset_dir
