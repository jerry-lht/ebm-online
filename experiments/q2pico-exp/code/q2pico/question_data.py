"""Data loading and split preparation for clinical question PICO slots."""

from __future__ import annotations

import csv
import os
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from random import Random
from typing import Any

from q2pico.io_utils import write_json, write_question_examples
from q2pico.schemas import PICO_LABELS, QuestionPICOExample, normalize_slot_values

DEFAULT_SPLIT_SEED = 20260516
DEFAULT_SPLIT_SIZES: dict[str, int] = {
    "fewshot20": 20,
    "dev20": 20,
    "test59": 59,
}
SPLIT_MANIFEST_VERSION = "question_split_v1"


class QuestionDataError(ValueError):
    """Raised when the clinical questions dataset violates q2pico assumptions."""


def load_clinical_questions(dataset_dir: str | Path) -> list[QuestionPICOExample]:
    rows = _load_rows_from_parquet_dir(dataset_dir)
    examples = [row_to_question_example(row) for row in rows]
    _validate_unique_question_ids(examples)
    return examples


def row_to_question_example(row: dict[str, Any]) -> QuestionPICOExample:
    if not isinstance(row, dict):
        raise QuestionDataError("Clinical question row must be an object")
    source_index = _require_string(row, "Index")
    source_dataset = _optional_string(row.get("Dataset")) or "unknown"
    question_id = f"{source_dataset}::{source_index}"
    question_text = _require_string(row, "Question")
    gold_slots = {
        "P": _slot_list_from_scalar(row.get("P")),
        "I": _slot_list_from_scalar(row.get("I")),
        "C": _slot_list_from_sequence(row.get("C")),
        "O": _slot_list_from_scalar(row.get("O")),
    }
    metadata = {
        "source_dataset": source_dataset,
        "source_index": source_index,
        "aspect": _optional_string(row.get("Aspect")),
        "s": _optional_string(row.get("S")),
        "source_row": row,
    }
    return QuestionPICOExample(
        question_id=question_id,
        split="full",
        question_text=question_text,
        gold_slots=gold_slots,
        metadata=metadata,
    )


def build_split_manifest(
    examples: list[QuestionPICOExample],
    *,
    seed: int = DEFAULT_SPLIT_SEED,
    split_sizes: dict[str, int] | None = None,
) -> dict[str, Any]:
    sizes = dict(DEFAULT_SPLIT_SIZES if split_sizes is None else split_sizes)
    if tuple(sizes) != tuple(DEFAULT_SPLIT_SIZES):
        raise QuestionDataError(f"Split keys must be {tuple(DEFAULT_SPLIT_SIZES)}")
    total_examples = len(examples)
    if sum(sizes.values()) != total_examples:
        raise QuestionDataError(
            f"Split sizes {sizes} sum to {sum(sizes.values())}, expected {total_examples}"
        )

    grouped: dict[str, list[QuestionPICOExample]] = defaultdict(list)
    for example in examples:
        dataset_name = str(example.metadata.get("source_dataset") or "unknown")
        grouped[dataset_name].append(example)

    shuffled_by_group: dict[str, list[QuestionPICOExample]] = {}
    for group_name in sorted(grouped):
        group_examples = sorted(grouped[group_name], key=lambda item: item.question_id)
        group_rng = Random(f"{seed}:{group_name}")
        group_rng.shuffle(group_examples)
        shuffled_by_group[group_name] = group_examples

    remaining_by_group = {group: list(items) for group, items in shuffled_by_group.items()}
    remaining_sizes = {group: len(items) for group, items in remaining_by_group.items()}
    remaining_total = total_examples
    assignments: dict[str, list[QuestionPICOExample]] = {split: [] for split in sizes}
    split_names = list(sizes)
    for split_name in split_names[:-1]:
        target = sizes[split_name]
        allocations = _allocate_group_counts(remaining_sizes, target, remaining_total)
        for group_name in sorted(remaining_by_group):
            take = allocations[group_name]
            assignments[split_name].extend(remaining_by_group[group_name][:take])
            remaining_by_group[group_name] = remaining_by_group[group_name][take:]
            remaining_sizes[group_name] -= take
        remaining_total -= target
    last_split = split_names[-1]
    for group_name in sorted(remaining_by_group):
        assignments[last_split].extend(remaining_by_group[group_name])

    manifest_splits: dict[str, dict[str, Any]] = {}
    for split_name, assigned_examples in assignments.items():
        manifest_splits[split_name] = {
            "question_ids": [example.question_id for example in assigned_examples],
            "question_count": len(assigned_examples),
            "dataset_counts": _dataset_counts(assigned_examples),
        }

    return {
        "version": SPLIT_MANIFEST_VERSION,
        "seed": seed,
        "split_sizes": sizes,
        "total_questions": total_examples,
        "splits": manifest_splits,
    }


def assign_splits(
    examples: list[QuestionPICOExample],
    manifest: dict[str, Any],
) -> dict[str, list[QuestionPICOExample]]:
    examples_by_id = {example.question_id: example for example in examples}
    assigned: dict[str, list[QuestionPICOExample]] = {}
    for split_name, split_info in manifest["splits"].items():
        split_examples: list[QuestionPICOExample] = []
        for question_id in split_info["question_ids"]:
            example = examples_by_id[question_id]
            split_examples.append(
                QuestionPICOExample(
                    question_id=example.question_id,
                    split=split_name,
                    question_text=example.question_text,
                    gold_slots=example.gold_slots,
                    metadata=example.metadata,
                )
            )
        assigned[split_name] = split_examples
    return assigned


def prepare_question_data(
    dataset_dir: str | Path,
    output_dir: str | Path,
    *,
    seed: int = DEFAULT_SPLIT_SEED,
    force: bool = False,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    paths = {
        "full_examples": output_path / "questions.full.examples.jsonl",
        "fewshot_examples": output_path / "questions.fewshot20.examples.jsonl",
        "dev_examples": output_path / "questions.dev20.examples.jsonl",
        "test_examples": output_path / "questions.test59.examples.jsonl",
        "split_manifest": output_path / "manifests" / "question_split_v1.json",
        "dataset_summary": output_path.parent / "tables" / "dataset_summary.csv",
        "split_summary": output_path.parent / "tables" / "question_split_summary.csv",
    }
    existing = [path for path in paths.values() if path.exists()]
    if existing and not force:
        existing_list = ", ".join(str(path) for path in existing)
        raise QuestionDataError(f"Output files already exist; pass --force to overwrite: {existing_list}")

    examples = load_clinical_questions(dataset_dir)
    manifest = build_split_manifest(examples, seed=seed)
    assigned = assign_splits(examples, manifest)

    write_question_examples(paths["full_examples"], examples)
    write_question_examples(paths["fewshot_examples"], assigned["fewshot20"])
    write_question_examples(paths["dev_examples"], assigned["dev20"])
    write_question_examples(paths["test_examples"], assigned["test59"])
    write_json(paths["split_manifest"], manifest)
    _write_csv(paths["dataset_summary"], _dataset_summary_rows(examples), _dataset_summary_fields())
    _write_csv(paths["split_summary"], _split_summary_rows(assigned), _split_summary_fields())

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_dir": str(Path(dataset_dir)),
        "manifest_version": SPLIT_MANIFEST_VERSION,
        "seed": seed,
        "total_questions": len(examples),
        "outputs": {key: str(path) for key, path in paths.items()},
    }


def _load_rows_from_parquet_dir(dataset_dir: str | Path) -> list[dict[str, Any]]:
    parquet_dir = Path(dataset_dir)
    parquet_files = sorted(str(path) for path in parquet_dir.glob("*.parquet"))
    if not parquet_files:
        raise QuestionDataError(f"No parquet files found under {parquet_dir}")
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError("The datasets package is required to load Clinical_Questions parquet files") from exc
    dataset = load_dataset("parquet", data_files={"train": parquet_files}, split="train")
    return [dict(row) for row in dataset]


def _validate_unique_question_ids(examples: list[QuestionPICOExample]) -> None:
    seen: set[str] = set()
    for example in examples:
        if example.question_id in seen:
            raise QuestionDataError(f"Duplicate question_id: {example.question_id!r}")
        seen.add(example.question_id)


def _require_string(row: dict[str, Any], field_name: str) -> str:
    value = row.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise QuestionDataError(f"Field {field_name!r} must be a non-empty string")
    return value.strip()


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        clean = value.strip()
        return clean or None
    return str(value)


def _slot_list_from_scalar(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, str):
        raise QuestionDataError(f"Expected scalar string slot value, got {type(value).__name__}")
    return normalize_slot_values([value])


def _slot_list_from_sequence(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return normalize_slot_values([value])
    if not isinstance(value, list):
        raise QuestionDataError(f"Expected list comparator slot value, got {type(value).__name__}")
    return normalize_slot_values(value)


def _allocate_group_counts(
    group_sizes: dict[str, int],
    target_total: int,
    remaining_total: int,
) -> dict[str, int]:
    if target_total > remaining_total:
        raise QuestionDataError("Target split size exceeds remaining pool")
    allocations = {group: 0 for group in group_sizes}
    if target_total == 0:
        return allocations
    remainders: list[tuple[float, str]] = []
    assigned = 0
    for group, size in group_sizes.items():
        if size == 0:
            continue
        exact = size * target_total / remaining_total
        base = min(size, int(exact))
        allocations[group] = base
        assigned += base
        remainders.append((exact - base, group))
    for _fraction, group in sorted(remainders, key=lambda item: (-item[0], item[1])):
        if assigned >= target_total:
            break
        if allocations[group] >= group_sizes[group]:
            continue
        allocations[group] += 1
        assigned += 1
    if assigned != target_total:
        raise QuestionDataError(f"Could not allocate exactly {target_total} questions across groups")
    return allocations


def _dataset_counts(examples: list[QuestionPICOExample]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for example in examples:
        counts[str(example.metadata.get("source_dataset") or "unknown")] += 1
    return dict(sorted(counts.items()))


def _dataset_summary_rows(examples: list[QuestionPICOExample]) -> list[dict[str, Any]]:
    rows = [_summary_row("all", "all", examples)]
    for dataset_name in sorted({str(example.metadata.get("source_dataset") or "unknown") for example in examples}):
        subset = [
            example
            for example in examples
            if str(example.metadata.get("source_dataset") or "unknown") == dataset_name
        ]
        rows.append(_summary_row("dataset", dataset_name, subset))
    return rows


def _split_summary_rows(assigned: dict[str, list[QuestionPICOExample]]) -> list[dict[str, Any]]:
    return [_summary_row("split", split_name, examples) for split_name, examples in assigned.items()]


def _summary_row(scope: str, name: str, examples: list[QuestionPICOExample]) -> dict[str, Any]:
    return {
        "scope": scope,
        "name": name,
        "question_count": len(examples),
        "source_dataset_count": len({str(example.metadata.get("source_dataset") or "unknown") for example in examples}),
        "p_non_empty_rate": _slot_non_empty_rate(examples, "P"),
        "i_non_empty_rate": _slot_non_empty_rate(examples, "I"),
        "c_non_empty_rate": _slot_non_empty_rate(examples, "C"),
        "o_non_empty_rate": _slot_non_empty_rate(examples, "O"),
    }


def _slot_non_empty_rate(examples: list[QuestionPICOExample], label: str) -> float:
    if not examples:
        return 0.0
    non_empty = sum(1 for example in examples if example.gold_slots[label])
    return non_empty / len(examples)


def _dataset_summary_fields() -> list[str]:
    return [
        "scope",
        "name",
        "question_count",
        "source_dataset_count",
        "p_non_empty_rate",
        "i_non_empty_rate",
        "c_non_empty_rate",
        "o_non_empty_rate",
    ]


def _split_summary_fields() -> list[str]:
    return _dataset_summary_fields()


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="",
        dir=path.parent,
        delete=False,
    ) as handle:
        temp_name = handle.name
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temp_name, path)
