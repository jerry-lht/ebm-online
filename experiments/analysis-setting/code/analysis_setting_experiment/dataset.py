from __future__ import annotations

import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from .constants import DEFAULT_DEV_RATIO, DEFAULT_SPLIT_SEED, SPLIT_VERSION
from .io_utils import dump_json, dump_jsonl, load_jsonl


def gold_candidate_count_bucket(count: int) -> str:
    if count <= 10:
        return "1-10"
    if count <= 25:
        return "11-25"
    return "26+"


def abstract_study_count_bucket(count: int) -> str:
    if count <= 3:
        return "0-3"
    if count <= 10:
        return "4-10"
    if count <= 20:
        return "11-20"
    return "21+"


def _clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def build_review_record(review: dict[str, Any]) -> dict[str, Any]:
    abstract_studies: list[dict[str, str]] = []
    for study in review.get("included_studies", []):
        abstract = _clean_text(study.get("abstract"))
        title = _clean_text(study.get("primary_report", {}).get("title"))
        if not abstract:
            continue
        abstract_studies.append(
            {
                "title": title,
                "abstract": abstract,
            }
        )

    gold_candidates = list(review.get("gold_partial_analysis_settings", []))
    coverage_level = review.get("evidence_coverage", {}).get("coverage_level", "")
    record = {
        "review_id": review["review_id"],
        "sr_title": _clean_text(review.get("sr_title")),
        "sr_pico": review.get("sr_pico", {}),
        "studies": abstract_studies,
        "metadata": {
            "review_id": review["review_id"],
            "abstract_study_count": len(abstract_studies),
            "abstract_study_count_bucket": abstract_study_count_bucket(len(abstract_studies)),
            "gold_candidate_count": len(gold_candidates),
            "gold_candidate_count_bucket": gold_candidate_count_bucket(len(gold_candidates)),
            "coverage_level": coverage_level,
        },
        "gold_partial_analysis_settings": gold_candidates,
    }
    return record


def load_benchmark_records(benchmark_path: Path) -> list[dict[str, Any]]:
    rows = load_jsonl(benchmark_path)
    return [build_review_record(row) for row in rows]


def make_dev_test_split(
    records: list[dict[str, Any]],
    *,
    dev_ratio: float = DEFAULT_DEV_RATIO,
    seed: int = DEFAULT_SPLIT_SEED,
) -> dict[str, list[dict[str, Any]]]:
    rng = random.Random(seed)
    strata: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        meta = record["metadata"]
        key = f'{meta["coverage_level"]}::{meta["gold_candidate_count_bucket"]}'
        strata[key].append(record)

    dev: list[dict[str, Any]] = []
    test: list[dict[str, Any]] = []
    for key in sorted(strata):
        group = list(strata[key])
        rng.shuffle(group)
        dev_count = round(len(group) * dev_ratio)
        if len(group) > 1 and dev_count == 0:
            dev_count = 1
        if dev_count >= len(group) and len(group) > 1:
            dev_count = len(group) - 1
        dev.extend(group[:dev_count])
        test.extend(group[dev_count:])

    dev.sort(key=lambda row: row["review_id"])
    test.sort(key=lambda row: row["review_id"])
    return {"dev": dev, "test": test}


def export_prepared_dataset(
    benchmark_path: Path,
    output_dir: Path,
    *,
    dev_ratio: float = DEFAULT_DEV_RATIO,
    seed: int = DEFAULT_SPLIT_SEED,
) -> dict[str, Any]:
    records = load_benchmark_records(benchmark_path)
    splits = make_dev_test_split(records, dev_ratio=dev_ratio, seed=seed)
    for split_name, split_rows in splits.items():
        dump_jsonl(output_dir / "splits" / f"{split_name}.jsonl", split_rows)

    summary = {
        "split_version": SPLIT_VERSION,
        "seed": seed,
        "dev_ratio": dev_ratio,
        "review_count": len(records),
        "split_counts": {key: len(value) for key, value in splits.items()},
    }
    dump_json(output_dir / "splits" / "metadata.json", summary)
    return summary

