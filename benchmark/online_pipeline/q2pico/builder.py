"""Build Q2PICO benchmark datasets."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from benchmark.online_pipeline.shared.building import (
    DEFAULT_SEED,
    download_or_resolve_source,
    length_bucket,
    select_records,
    sha256_file,
    source_manifest,
    stable_order,
    slot_list,
    write_dataset_artifacts,
)
from benchmark.online_pipeline.shared.jsonl import read_jsonl


MODULE = "q2pico"
Q2CRBENCH3_HF_DATASET_ID = "somewordstoolate/Q2CRBench-3"
Q2CRBENCH3_HF_ENDPOINT = "https://hf-mirror.com"
Q2CRBENCH3_CLINICAL_QUESTIONS_PARQUET = "Clinical_Questions/train-00000-of-00001.parquet"
Q2CRBENCH3_CLINICAL_QUESTIONS_CONFIGS = ("Clinical_Questions", "clinical_questions")


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
        split_strategy=split_strategy(),
        seed=seed,
        sample_size=sample_size,
        source_record_count=len(records),
        dataset_analysis=dataset_analysis(selected),
    )


def load_source(*, source: str, source_url: str | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if source == "builtin_smoke":
        records = builtin_records()
        return records, source_manifest(source=source, records=records, source_url=None, raw_sha256=None)
    if source == "q2crbench3" and not source_url:
        records, hf_manifest = load_q2crbench3_clinical_questions_from_hf()
        return records, source_manifest(
            source=source,
            records=records,
            source_url=f"hf://datasets/{Q2CRBENCH3_HF_DATASET_ID}/Clinical_Questions",
            raw_sha256=None,
            extra=hf_manifest,
        )
    if source_url:
        raw_path = download_or_resolve_source(source=source, source_url=source_url)
        records = records_from_path(raw_path)
        return records, source_manifest(source=source, records=records, source_url=source_url, raw_sha256=sha256_file(raw_path))
    raise ValueError(f"Unsupported q2pico source: {source}")


def builtin_records() -> list[dict[str, Any]]:
    questions = [
        "In adults with catheter-related bladder discomfort after surgery, does duloxetine reduce discomfort compared with placebo?",
        "For adults after surgery with catheter-related bladder discomfort, does duloxetine versus placebo reduce bladder discomfort?",
        "Among surgical adults at risk of catheter-related bladder discomfort, is duloxetine better than placebo for discomfort?",
        "Does duloxetine reduce catheter-related bladder discomfort compared with placebo in adults after surgery?",
        "In postoperative adults with catheter-related bladder discomfort, does duloxetine improve discomfort versus placebo?",
        "For adults undergoing surgery who develop catheter-related bladder discomfort, does duloxetine reduce discomfort compared with placebo?",
        "Among adults with postoperative catheter-related bladder discomfort, is duloxetine more effective than placebo?",
        "In adults after catheterization for surgery, does duloxetine reduce catheter-related bladder discomfort compared to placebo?",
        "Does perioperative duloxetine lower catheter-related bladder discomfort in adults compared with placebo?",
        "In adults with postoperative catheter-related bladder discomfort, duloxetine versus placebo: does it reduce discomfort?",
    ]
    records = []
    for index, question in enumerate(questions, start=1):
        instance_id = f"q2pico-builtin-{index:03d}"
        records.append(
            {
                "source_id": instance_id,
                "source_split": None,
                "strata": {"source_dataset": "builtin", "slot_pattern": "PICO", "length_bucket": length_bucket(question)},
                "instance": {
                    "instance_id": instance_id,
                    "question_text": question,
                    "source": {"dataset": "builtin", "index": str(index), "split": None},
                    "metadata": {"aspect": None, "s": None},
                },
                "gold": {
                    "instance_id": instance_id,
                    "P": ["adults with catheter-related bladder discomfort after surgery"],
                    "I": ["duloxetine"],
                    "C": ["placebo"],
                    "O": ["catheter-related bladder discomfort"],
                    "source": {"dataset": "builtin", "index": str(index)},
                },
            }
        )
    return records


def records_from_path(path: Path) -> list[dict[str, Any]]:
    if path.is_dir() or path.suffix == ".parquet":
        return records_from_parquet(path)
    if path.suffix == ".jsonl":
        rows = read_jsonl(path)
    else:
        raise ValueError("q2pico source-url must resolve to a parquet file, parquet directory, or JSONL")
    return records_from_generic_rows(rows, default_source_dataset="source")


def records_from_parquet(path: Path) -> list[dict[str, Any]]:
    return records_from_rows(parquet_rows(path))


def parquet_rows(path: Path) -> list[dict[str, Any]]:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError("The pyarrow package is required for Q2CRBench parquet sources") from exc
    parquet_files = sorted(path.glob("*.parquet")) if path.is_dir() else [path]
    if not parquet_files:
        raise FileNotFoundError(f"No parquet files found under {path}")
    rows: list[dict[str, Any]] = []
    for parquet_file in parquet_files:
        table = pq.read_table(parquet_file)
        rows.extend(table.to_pylist())
    return rows


def load_q2crbench3_clinical_questions_from_hf() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    mirror_url = (
        f"{Q2CRBENCH3_HF_ENDPOINT}/datasets/{Q2CRBENCH3_HF_DATASET_ID}/resolve/main/"
        f"{Q2CRBENCH3_CLINICAL_QUESTIONS_PARQUET}"
    )
    try:
        raw_path = download_or_resolve_source(source="q2crbench3_clinical_questions", source_url=mirror_url)
        records = records_from_parquet(raw_path)
        return records, {
            "hf_dataset_id": Q2CRBENCH3_HF_DATASET_ID,
            "hf_endpoint": Q2CRBENCH3_HF_ENDPOINT,
            "hf_config": "Clinical_Questions",
            "hf_split": "train",
            "hf_file": Q2CRBENCH3_CLINICAL_QUESTIONS_PARQUET,
            "raw_sha256": sha256_file(raw_path),
            "loader": "hf_mirror_parquet",
        }
    except Exception as mirror_error:
        fallback_records, fallback_manifest = load_q2crbench3_clinical_questions_with_datasets()
        fallback_manifest["mirror_error"] = str(mirror_error)
        return fallback_records, fallback_manifest


def load_q2crbench3_clinical_questions_with_datasets() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        from datasets import get_dataset_config_names, load_dataset
    except ImportError as exc:
        raise RuntimeError(
            "The `datasets` package is required to build q2pico from Hugging Face fallback loader. "
            "Install it, or pass --source-url pointing at a local Q2CRBench-3 Clinical_Questions parquet/JSONL file."
        ) from exc

    dataset_id = Q2CRBENCH3_HF_DATASET_ID
    attempted_configs: list[str | None] = []
    try:
        available_configs = list(get_dataset_config_names(dataset_id))
    except Exception:
        available_configs = []
    config_candidates: list[str | None] = [
        *[config for config in Q2CRBENCH3_CLINICAL_QUESTIONS_CONFIGS if not available_configs or config in available_configs],
        None,
    ]

    last_error: Exception | None = None
    for config_name in config_candidates:
        if config_name in attempted_configs:
            continue
        attempted_configs.append(config_name)
        try:
            if config_name:
                dataset = load_dataset(dataset_id, config_name, split="train")
            else:
                dataset = load_dataset(dataset_id, data_dir="Clinical_Questions", split="train")
            rows = [dict(row) for row in dataset]
            records = records_from_rows(rows)
            return records, {
                "hf_dataset_id": dataset_id,
                "hf_endpoint": "datasets_default",
                "hf_config": config_name,
                "hf_data_dir": None if config_name else "Clinical_Questions",
                "hf_available_configs": available_configs,
                "hf_split": "train",
                "loader": "datasets_load_dataset",
            }
        except Exception as exc:
            last_error = exc

    raise RuntimeError(
        "Failed to load Q2CRBench-3 Clinical_Questions from Hugging Face dataset "
        f"{dataset_id!r}. Tried configs/data_dir: {attempted_configs}."
    ) from last_error


def records_from_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return records_from_generic_rows(rows, default_source_dataset="Q2CRBench-3")


def records_from_generic_rows(rows: list[dict[str, Any]], *, default_source_dataset: str) -> list[dict[str, Any]]:
    records = []
    for index, row in enumerate(rows, start=1):
        source_dataset = str(row.get("Dataset") or row.get("source_dataset") or default_source_dataset)
        source_index = str(row.get("Index") or row.get("source_index") or index)
        instance_id = str(row.get("instance_id") or row.get("question_id") or f"{source_dataset}::{source_index}")
        question = str(row.get("question_text") or row.get("Question") or "")
        gold = {
            "instance_id": instance_id,
            "P": slot_list(row.get("P")),
            "I": slot_list(row.get("I")),
            "C": slot_list(row.get("C")),
            "O": slot_list(row.get("O")),
            "source": {"dataset": source_dataset, "index": source_index},
        }
        records.append(
            {
                "source_id": instance_id,
                "source_split": row.get("split") or row.get("Split"),
                "strata": {
                    "source_dataset": source_dataset,
                    "slot_pattern": slot_pattern(gold),
                    "length_bucket": length_bucket(question),
                },
                "instance": {
                    "instance_id": instance_id,
                    "question_text": question,
                    "source": {
                        "dataset": source_dataset,
                        "index": source_index,
                        "split": row.get("split") or row.get("Split"),
                    },
                    "metadata": {
                        "aspect": row.get("Aspect") or row.get("aspect"),
                        "s": row.get("S") or row.get("s"),
                    },
                },
                "gold": gold,
            }
        )
    return records


def build_splits(records: list[dict[str, Any]], *, seed: str = DEFAULT_SEED) -> dict[str, list[dict[str, Any]]]:
    mapped = seeded_stratified_dev_test(records, seed=seed, dev_fraction=0.4)
    smoke_pool = mapped["dev"] or mapped["test"]
    smoke = stable_order(smoke_pool, seed=f"{seed}:q2pico:smoke", module=MODULE)[: min(10, len(smoke_pool))]
    return {"smoke": smoke, "dev": mapped["dev"], "test": mapped["test"]}


def seeded_stratified_dev_test(
    records: list[dict[str, Any]],
    *,
    seed: str,
    dev_fraction: float,
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        dataset_name = str((record.get("strata") or {}).get("source_dataset") or "all")
        grouped[dataset_name].append(record)
    dev: list[dict[str, Any]] = []
    test: list[dict[str, Any]] = []
    for group_name in sorted(grouped):
        items = stable_order(grouped[group_name], seed=f"{seed}:q2pico:split:{group_name}", module=MODULE)
        dev_count = max(1, round(len(items) * dev_fraction)) if items else 0
        if len(items) > 1:
            dev_count = min(dev_count, len(items) - 1)
        dev.extend(items[:dev_count])
        test.extend(items[dev_count:])
    return {
        "dev": sorted(dev, key=lambda record: record["source_id"]),
        "test": sorted(test, key=lambda record: record["source_id"]),
    }


def split_strategy() -> str:
    return "seeded_stratified_by_dataset_dev40_test60_smoke_from_dev"


def dataset_analysis(records: list[dict[str, Any]]) -> dict[str, Any]:
    dataset_counts: dict[str, int] = defaultdict(int)
    slot_patterns: dict[str, int] = defaultdict(int)
    length_buckets: dict[str, int] = defaultdict(int)
    for record in records:
        strata = record.get("strata") or {}
        dataset_counts[str(strata.get("source_dataset") or "unknown")] += 1
        slot_patterns[str(strata.get("slot_pattern") or "unknown")] += 1
        length_buckets[str(strata.get("length_bucket") or "unknown")] += 1
    return {
        "record_count": len(records),
        "dataset_counts": dict(sorted(dataset_counts.items())),
        "slot_pattern_counts": dict(sorted(slot_patterns.items())),
        "question_length_bucket_counts": dict(sorted(length_buckets.items())),
    }


def slot_pattern(gold: dict[str, Any]) -> str:
    return "".join(slot for slot in ("P", "I", "C", "O") if gold.get(slot)) or "empty"
