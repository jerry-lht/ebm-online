"""Shared I/O helpers for GRADE domain evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from benchmark.online_pipeline.grade.builder import ALIGNMENT_BUILDER_VERSION_V3, BUILDER_VERSION_V3, SOURCE_V3
from benchmark.online_pipeline.shared.jsonl import read_jsonl


def load_domain_dataset(dataset: str | Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    dataset_dir = Path(dataset)
    _validate_dataset_manifest(dataset_dir)
    instances = read_jsonl(dataset_dir / "instances.jsonl")
    gold_rows = read_jsonl(dataset_dir / "gold.jsonl")
    gold_by_id = {str(row["instance_id"]): row for row in gold_rows}
    return instances, gold_by_id


def _validate_dataset_manifest(dataset_dir: Path) -> None:
    root = dataset_dir.parent.parent if dataset_dir.parent.name == "splits" else dataset_dir
    if root.name != SOURCE_V3:
        return
    manifest_path = root / "source_manifest.json"
    analysis_path = root / "dataset_analysis.json"
    if not manifest_path.exists() or not analysis_path.exists():
        raise RuntimeError(f"{SOURCE_V3} dataset is missing source_manifest.json or dataset_analysis.json: {root}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    if manifest.get("source") != SOURCE_V3 or manifest.get("builder_version") != BUILDER_VERSION_V3:
        raise RuntimeError(f"{SOURCE_V3} dataset has invalid source manifest: {manifest_path}")
    if analysis.get("builder_version") != ALIGNMENT_BUILDER_VERSION_V3 or analysis.get("mode") != "llm":
        raise RuntimeError(
            f"{SOURCE_V3} dataset must come from {ALIGNMENT_BUILDER_VERSION_V3} with mode='llm': {analysis_path}"
        )
