"""Build study screening benchmark datasets."""

from __future__ import annotations

import csv
import json
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from benchmark.online_pipeline.shared.building import (
    DEFAULT_SEED,
    download_github_base64_blob,
    download_or_resolve_source,
    normalize_split_name,
    select_records,
    sha256_file,
    source_manifest,
    stable_order,
    slot_list,
    write_dataset_artifacts,
)
from benchmark.online_pipeline.shared.jsonl import read_jsonl


MODULE = "study_screening"
CSMED_FT_REPO = "WojciechKusa/systematic-review-datasets"
CSMED_FT_ZIP_PATH = "data/CSMeD/CSMeD-FT.zip"
CSMED_FT_GIT_MIRROR_URL = "https://gh.llkk.cc/https://github.com/WojciechKusa/systematic-review-datasets.git"
CSMED_FT_RAW_URL = f"https://raw.githubusercontent.com/{CSMED_FT_REPO}/main/{CSMED_FT_ZIP_PATH}"
CSMED_FT_MIRROR_RAW_URL = f"https://gh.llkk.cc/{CSMED_FT_RAW_URL}"
CSMED_FT_URL = CSMED_FT_MIRROR_RAW_URL
CSMED_FT_BLOB_URL = "https://api.github.com/repos/WojciechKusa/systematic-review-datasets/git/blobs/48f43ba30d860170f0f022d1dcd1510e1cf9c7af"
STUDY_SCREENING_SMOKE_SIZE = 5


def build_dataset(
    *,
    source: str,
    dataset_name: str,
    sample_size: int | None = None,
    seed: str = DEFAULT_SEED,
    source_url: str | None = None,
) -> dict[str, Any]:
    records, manifest = load_source(source=source, source_url=source_url)
    selected = select_records(records, sample_size=sample_size, seed=seed, module=MODULE)
    return write_dataset_artifacts(
        module=MODULE,
        source=source,
        dataset_name=dataset_name,
        records=selected,
        source_manifest=manifest,
        splits=build_splits(selected, seed=seed),
        split_strategy=split_strategy(selected),
        seed=seed,
        sample_size=sample_size,
        source_record_count=len(records),
        dataset_analysis=dataset_analysis(selected),
    )


def load_source(*, source: str, source_url: str | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if source == "builtin_smoke":
        records = builtin_records()
        return records, source_manifest(source=source, records=records, source_url=None, raw_sha256=None)
    if source == "csmed_ft" and not source_url:
        raw_path = download_or_resolve_source(
            source="csmed_ft",
            source_url=CSMED_FT_URL,
            fallback=lambda target: download_github_base64_blob(blob_url=CSMED_FT_BLOB_URL, target=target),
        )
        records = csmed_ft_records_from_zip(raw_path)
        return records, source_manifest(
            source=source,
            records=records,
            source_url=CSMED_FT_URL,
            raw_sha256=sha256_file(raw_path),
            extra={
                "repo": CSMED_FT_REPO,
                "repo_path": CSMED_FT_ZIP_PATH,
                "git_mirror_url": CSMED_FT_GIT_MIRROR_URL,
                "raw_mirror_url": CSMED_FT_MIRROR_RAW_URL,
                "loader": "raw_mirror_zip",
                "official_splits": ["train", "dev", "test", "sample"],
            },
        )
    if source_url:
        raw_path = download_or_resolve_source(source=source, source_url=source_url)
        records = csmed_ft_records_from_zip(raw_path) if raw_path.suffix == ".zip" else records_from_path(raw_path)
        return records, source_manifest(source=source, records=records, source_url=source_url, raw_sha256=sha256_file(raw_path))
    raise ValueError(f"Unsupported study_screening source: {source}")


def builtin_records() -> list[dict[str, Any]]:
    records = []
    for index in range(1, 11):
        study_id = "mock-study-1" if index % 2 else "mock-study-2"
        instance_id = f"screening-builtin-{index:03d}"
        records.append(
            {
                "source_id": instance_id,
                "source_split": None,
                "strata": {"source_dataset": "builtin", "decision": "include", "has_full_text": "yes"},
                "instance": {
                    "instance_id": instance_id,
                    "question_text": (
                        "In adults with catheter-related bladder discomfort after surgery, does duloxetine "
                        "reduce discomfort compared with placebo?"
                    ),
                    "question_pico": {
                        "P": ["adults with catheter-related bladder discomfort after surgery"],
                        "I": ["duloxetine"],
                        "C": ["placebo"],
                        "O": ["catheter-related bladder discomfort"],
                    },
                    "screening_criteria": {
                        "inclusion": [
                            "Randomized controlled trials",
                            "Adults with catheter-related bladder discomfort after surgery",
                            "Duloxetine compared with placebo",
                        ],
                        "exclusion": ["Non-randomized studies", "Non-human studies", "Reviews or guidelines"],
                    },
                    "articles": [
                        {
                            "study_id": study_id,
                            "metadata": {
                                "title": f"Duloxetine for catheter-related bladder discomfort randomized trial {index}",
                                "source_type": "builtin_smoke",
                            },
                            "xml_content": {
                                "sections": [
                                    {
                                        "section": "Abstract",
                                        "text": "Randomized controlled trial comparing duloxetine with placebo in adults after surgery.",
                                    },
                                    {
                                        "section": "Full Text",
                                        "text": "Participants were adults undergoing surgery with catheter-related bladder discomfort risk.",
                                    },
                                ]
                            },
                            "source": {"database": "builtin_smoke", "raw_record_id": study_id},
                        }
                    ],
                },
                "gold": {
                    "instance_id": instance_id,
                    "study_id": study_id,
                    "gold_decision": "include",
                    "gold_reason": "Builtin RCT matches population, intervention, and comparator.",
                },
            }
        )
    return records


def records_from_path(path: Path) -> list[dict[str, Any]]:
    if path.is_dir() or path.suffix == ".parquet":
        return records_from_generic_rows(parquet_rows(path))
    if path.suffix == ".jsonl":
        rows = read_jsonl(path)
    elif path.suffix == ".csv":
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
    else:
        raise ValueError("study_screening source-url must resolve to parquet, JSONL, or CSV")
    return records_from_generic_rows(rows)


def parquet_rows(path: Path) -> list[dict[str, Any]]:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError("The pyarrow package is required for parquet screening sources") from exc
    parquet_files = sorted(path.glob("*.parquet")) if path.is_dir() else [path]
    if not parquet_files:
        raise FileNotFoundError(f"No parquet files found under {path}")
    rows: list[dict[str, Any]] = []
    for parquet_file in parquet_files:
        table = pq.read_table(parquet_file)
        rows.extend(table.to_pylist())
    return rows


def records_from_generic_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = []
    for index, row in enumerate(rows, start=1):
        instance_id = str(row.get("instance_id") or row.get("study_id") or f"screening-source-{index:06d}")
        study_id = str(row.get("study_id") or instance_id)
        decision = str(row.get("gold_decision") or row.get("decision") or "").strip().lower()
        full_text_sections = row.get("full_text_sections") or []
        if isinstance(full_text_sections, str):
            full_text_sections = [{"section": "Full Text", "text": full_text_sections}]
        instance = {
            "instance_id": instance_id,
            "question_text": str(row.get("question") or row.get("question_text") or ""),
            "screening_criteria": {
                "inclusion": slot_list(row.get("criteria.inclusion") or row.get("inclusion")),
                "exclusion": slot_list(row.get("criteria.exclusion") or row.get("exclusion")),
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
        records.append(
            {
                "source_id": instance_id,
                "source_split": row.get("split"),
                "strata": {
                    "source_dataset": str(row.get("source") or row.get("review_id") or "source"),
                    "decision": decision,
                    "has_full_text": "yes" if full_text_sections else "no",
                },
                "instance": instance,
                "gold": {
                    "instance_id": instance_id,
                    "study_id": study_id,
                    "gold_decision": decision,
                    "gold_reason": str(row.get("gold_reason") or row.get("reason") or ""),
                },
            }
        )
    return records


def csmed_ft_records_from_zip(path: Path) -> list[dict[str, Any]]:
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("The pandas package is required to build study_screening from CSMeD-FT") from exc

    records: list[dict[str, Any]] = []
    with zipfile.ZipFile(path) as archive:
        for split in ("train", "dev", "test"):
            csv_name = f"CSMeD-FT/CSMeD-FT-{split}.csv"
            metadata_name = f"CSMeD-FT/CSMeD-FT-{split}_reviews_metadata.json"
            with archive.open(metadata_name) as handle:
                review_metadata = json.load(handle)
            with archive.open(csv_name) as handle:
                rows = pd.read_csv(handle).to_dict(orient="records")
            for row_index, row in enumerate(rows, start=1):
                records.append(csmed_ft_record_from_row(row=row, row_index=row_index, split=split, review_metadata=review_metadata))
    return records


def csmed_ft_record_from_row(
    *,
    row: dict[str, Any],
    row_index: int,
    split: str,
    review_metadata: dict[str, Any],
) -> dict[str, Any]:
    review_id = required_text(row.get("review_id"), field="review_id")
    document_id = required_text(row.get("document_id"), field="document_id")
    review = review_metadata.get(review_id)
    if not review:
        raise ValueError(f"Missing CSMeD-FT review metadata for review_id={review_id!r}")

    study_id = document_id
    instance_id = f"csmed-ft::{split}::{review_id}::{document_id}"
    decision = screening_decision_from_csmed(row.get("decision"))
    criteria_text = clean_text(review.get("criteria_text"))
    review_title = clean_text(review.get("title"))
    review_abstract = clean_text(review.get("abstract"))
    article_title = clean_text(row.get("title"))
    abstract = clean_text(row.get("abstract"))
    main_text = clean_text(row.get("main_text"))
    reason = clean_text(row.get("reason_for_exclusion"))
    pmid = optional_text(row.get("PubMed ID"))
    doi = optional_text(row.get("doi"))
    year = optional_text(row.get("year"))
    sections = [{"section": "Abstract", "text": abstract}]
    if main_text:
        sections.append({"section": "Full Text", "text": main_text})
    return {
        "source_id": instance_id,
        "source_split": split,
        "strata": {
            "source_dataset": "CSMeD-FT",
            "review_id": review_id,
            "decision": decision,
            "has_full_text": "yes" if main_text else "no",
        },
        "instance": {
            "instance_id": instance_id,
            "question_text": review_title,
            "screening_criteria": {
                "inclusion": [criteria_text] if criteria_text else [],
                "exclusion": [],
                "rationale": "CSMeD-FT provides a single review-level eligibility criteria text.",
            },
            "articles": [
                {
                    "study_id": study_id,
                    "metadata": {
                        "title": article_title,
                        "pmid": pmid,
                        "source_type": "CSMeD-FT",
                        "publication_year": publication_year(year),
                        "doi": doi,
                    },
                    "xml_content": {"sections": sections, "tables": []},
                    "source": {
                        "database": "CSMeD-FT",
                        "raw_record_id": study_id,
                        "raw_source_url": None,
                    },
                }
            ],
            "source": {
                "dataset": "CSMeD-FT",
                "split": split,
                "review_id": review_id,
                "document_id": document_id,
                "row_index": row_index,
                "review_abstract": review_abstract,
            },
        },
        "gold": {
            "instance_id": instance_id,
            "study_id": study_id,
            "gold_decision": decision,
            "gold_reason": reason,
            "source": {
                "dataset": "CSMeD-FT",
                "split": split,
                "review_id": review_id,
                "document_id": document_id,
                "raw_decision": clean_text(row.get("decision")),
                "reason_for_exclusion": reason,
            },
        },
    }


def build_splits(records: list[dict[str, Any]], *, seed: str = DEFAULT_SEED) -> dict[str, list[dict[str, Any]]]:
    source_splits = {record.get("source_split") for record in records if record.get("source_split")}
    if source_splits:
        mapped: dict[str, list[dict[str, Any]]] = {"dev": [], "test": [], "smoke": []}
        train_records: list[dict[str, Any]] = []
        for record in records:
            source_split = str(record.get("source_split") or "")
            split = normalize_split_name(source_split)
            if source_split == "train":
                train_records.append(record)
            elif split in {"dev", "test"}:
                mapped[split].append(record)
        smoke_pool = mapped["dev"] or train_records or mapped["test"]
        mapped["smoke"] = screening_smoke_sample(
            smoke_pool,
            seed=seed,
            sample_size=min(STUDY_SCREENING_SMOKE_SIZE, len(smoke_pool)),
        )
        return {key: sorted(value, key=lambda record: record["source_id"]) for key, value in mapped.items()}

    mapped = seeded_stratified_screening_dev_test(records, seed=seed, dev_fraction=0.4)
    smoke_pool = mapped["dev"] or mapped["test"]
    smoke = screening_smoke_sample(smoke_pool, seed=seed, sample_size=min(STUDY_SCREENING_SMOKE_SIZE, len(smoke_pool)))
    return {"smoke": smoke, "dev": mapped["dev"], "test": mapped["test"]}


def seeded_stratified_screening_dev_test(
    records: list[dict[str, Any]],
    *,
    seed: str,
    dev_fraction: float,
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        strata = record.get("strata") or {}
        key = "|".join(
            [
                str(strata.get("source_dataset") or "all"),
                str(strata.get("decision") or "unknown"),
                str(strata.get("has_full_text") or "unknown"),
            ]
        )
        grouped[key].append(record)
    dev: list[dict[str, Any]] = []
    test: list[dict[str, Any]] = []
    for group_name in sorted(grouped):
        items = stable_order(grouped[group_name], seed=f"{seed}:study_screening:split:{group_name}", module=MODULE)
        dev_count = max(1, round(len(items) * dev_fraction)) if items else 0
        if len(items) > 1:
            dev_count = min(dev_count, len(items) - 1)
        dev.extend(items[:dev_count])
        test.extend(items[dev_count:])
    return {
        "dev": sorted(dev, key=lambda record: record["source_id"]),
        "test": sorted(test, key=lambda record: record["source_id"]),
    }


def screening_smoke_sample(records: list[dict[str, Any]], *, seed: str, sample_size: int) -> list[dict[str, Any]]:
    if sample_size <= 0:
        return []
    by_decision: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        decision = str((record.get("strata") or {}).get("decision") or "unknown")
        by_decision[decision].append(record)
    selected: list[dict[str, Any]] = []
    decision_quota = max(1, sample_size // max(1, len(by_decision)))
    for decision in sorted(by_decision):
        ordered = stable_order(
            by_decision[decision],
            seed=f"{seed}:study_screening:smoke:{decision}",
            module=MODULE,
        )
        selected.extend(ordered[: min(decision_quota, len(ordered))])
    selected_ids = {record["source_id"] for record in selected}
    if len(selected) < sample_size:
        remainder = [record for record in records if record["source_id"] not in selected_ids]
        selected.extend(
            stable_order(remainder, seed=f"{seed}:study_screening:smoke:fill", module=MODULE)[
                : sample_size - len(selected)
            ]
        )
    return sorted(selected[:sample_size], key=lambda record: record["source_id"])


def split_strategy(selected: list[dict[str, Any]]) -> str:
    if any(record.get("source_split") for record in selected):
        return "preserve_csmed_ft_official_dev_test_smoke5_from_dev_seed42"
    return "seeded_stratified_by_dataset_decision_dev40_test60_smoke5_from_dev"


def dataset_analysis(records: list[dict[str, Any]]) -> dict[str, Any]:
    dataset_counts: dict[str, int] = defaultdict(int)
    decision_counts: dict[str, int] = defaultdict(int)
    review_counts: dict[str, int] = defaultdict(int)
    for record in records:
        strata = record.get("strata") or {}
        dataset_counts[str(strata.get("source_dataset") or "unknown")] += 1
        decision_counts[str(strata.get("decision") or "unknown")] += 1
        review_counts[str(strata.get("review_id") or "unknown")] += 1
    return {
        "record_count": len(records),
        "dataset_counts": dict(sorted(dataset_counts.items())),
        "decision_counts": dict(sorted(decision_counts.items())),
        "review_id_counts": dict(sorted(review_counts.items())),
    }


def screening_decision_from_csmed(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"included", "include"}:
        return "include"
    if normalized in {"excluded", "exclude"}:
        return "exclude"
    raise ValueError(f"Unsupported CSMeD-FT decision value: {value!r}")


def publication_year(value: str | None) -> str | None:
    if not value:
        return None
    return value[:4] if len(value) >= 4 else value


def optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def clean_text(value: Any) -> str:
    return optional_text(value) or ""


def required_text(value: Any, *, field: str) -> str:
    text = optional_text(value)
    if text is None:
        raise ValueError(f"Missing required field: {field}")
    return text
