"""Convert canonical CSMeD-FT-style rows into study screening benchmark fixtures."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from benchmark.online_pipeline.shared.jsonl import write_jsonl
from benchmark.online_pipeline.shared.report_utils import write_json


def convert_csmed_rows(*, input_path: str | Path, output_dir: str | Path, limit: int | None = None) -> dict[str, Any]:
    rows = _read_rows(input_path)
    if limit is not None:
        rows = rows[:limit]
    instances: list[dict[str, Any]] = []
    gold_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        instance_id = str(row.get("instance_id") or row.get("study_id") or f"csmed-ft-smoke-{index:03d}")
        study_id = str(row.get("study_id") or instance_id)
        full_text_sections = row.get("full_text_sections") or []
        if isinstance(full_text_sections, str):
            full_text_sections = [{"section": "Full Text", "text": full_text_sections}]
        instances.append(
            {
                "instance_id": instance_id,
                "question_text": str(row.get("question") or row.get("question_text") or ""),
                "screening_criteria": {
                    "inclusion": _list_field(row.get("criteria.inclusion") or row.get("inclusion")),
                    "exclusion": _list_field(row.get("criteria.exclusion") or row.get("exclusion")),
                },
                "articles": [
                    {
                        "study_id": study_id,
                        "metadata": {"title": str(row.get("title") or "")},
                        "xml_content": {
                            "sections": [
                                {"section": "Abstract", "text": str(row.get("abstract") or "")},
                                *list(full_text_sections),
                            ]
                        },
                        "source": {"database": "CSMeD-FT", "raw_record_id": study_id},
                    }
                ],
            }
        )
        gold_rows.append(
            {
                "instance_id": instance_id,
                "study_id": study_id,
                "gold_decision": str(row.get("gold_decision") or row.get("decision") or "").lower(),
                "gold_reason": str(row.get("gold_reason") or row.get("reason") or ""),
            }
        )
    resolved = Path(output_dir)
    write_jsonl(resolved / "instances.jsonl", instances)
    write_jsonl(resolved / "gold.jsonl", gold_rows)
    manifest = {
        "dataset_id": "csmed-ft-converted",
        "module": "study_screening",
        "source": str(Path(input_path)),
        "instance_count": len(instances),
        "gold_count": len(gold_rows),
        "limit": limit,
    }
    write_json(resolved / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-path", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    manifest = convert_csmed_rows(input_path=args.input_path, output_dir=args.output_dir, limit=args.limit)
    print(manifest["instance_count"])


def _read_rows(path: str | Path) -> list[dict[str, Any]]:
    resolved = Path(path)
    if resolved.suffix == ".jsonl":
        rows = []
        for line in resolved.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows
    if resolved.suffix == ".csv":
        with resolved.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    raise ValueError("CSMeD-FT converter input must be .jsonl or .csv")


def _list_field(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return [text]
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    return [text]


if __name__ == "__main__":
    main()
