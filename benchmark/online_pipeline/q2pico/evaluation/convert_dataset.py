"""Convert Q2CRBench Clinical Questions rows into q2pico benchmark fixtures."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from benchmark.online_pipeline.shared.jsonl import write_jsonl
from benchmark.online_pipeline.shared.report_utils import write_json


def convert_q2crbench_clinical_questions(
    *,
    dataset_dir: str | Path,
    output_dir: str | Path,
    limit: int | None = None,
) -> dict[str, Any]:
    rows = _load_parquet_rows(dataset_dir)
    if limit is not None:
        rows = rows[:limit]
    instances: list[dict[str, Any]] = []
    gold_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        instance_id = _instance_id(row, index)
        instances.append({"instance_id": instance_id, "question_text": _require_str(row, "Question")})
        gold_rows.append(
            {
                "instance_id": instance_id,
                "P": _slot_from_scalar(row.get("P")),
                "I": _slot_from_scalar(row.get("I")),
                "C": _slot_from_sequence(row.get("C")),
                "O": _slot_from_scalar(row.get("O")),
            }
        )
    resolved = Path(output_dir)
    write_jsonl(resolved / "instances.jsonl", instances)
    write_jsonl(resolved / "gold.jsonl", gold_rows)
    manifest = {
        "dataset_id": "q2crbench-clinical-questions-converted",
        "module": "q2pico",
        "source": str(Path(dataset_dir)),
        "instance_count": len(instances),
        "gold_count": len(gold_rows),
        "limit": limit,
    }
    write_json(resolved / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    manifest = convert_q2crbench_clinical_questions(
        dataset_dir=args.dataset_dir,
        output_dir=args.output_dir,
        limit=args.limit,
    )
    print(manifest["instance_count"])


def _load_parquet_rows(dataset_dir: str | Path) -> list[dict[str, Any]]:
    parquet_files = sorted(Path(dataset_dir).glob("*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(f"No parquet files found under {dataset_dir}")
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError("The datasets package is required to convert Q2CRBench parquet files") from exc
    dataset = load_dataset("parquet", data_files={"train": [str(path) for path in parquet_files]}, split="train")
    return [dict(row) for row in dataset]


def _instance_id(row: dict[str, Any], fallback_index: int) -> str:
    dataset = str(row.get("Dataset") or "q2crbench").strip()
    index = str(row.get("Index") or fallback_index).strip()
    return f"{dataset}::{index}"


def _require_str(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Required string field missing: {key}")
    return value.strip()


def _slot_from_scalar(value: Any) -> list[str]:
    if value is None:
        return []
    clean = str(value).strip()
    return [clean] if clean else []


def _slot_from_sequence(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return _slot_from_scalar(value)


if __name__ == "__main__":
    main()
