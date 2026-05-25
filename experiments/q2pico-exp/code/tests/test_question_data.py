from __future__ import annotations

import json

import pytest

from q2pico.question_data import (
    DEFAULT_SPLIT_SEED,
    build_split_manifest,
    prepare_question_data,
    row_to_question_example,
)


def _row(index: int, dataset: str = "A", comparator: list[str] | None = None) -> dict[str, object]:
    return {
        "Aspect": "therapy",
        "Index": f"q{index}",
        "Question": f"Question {index}",
        "P": f"Population {index}",
        "I": f"Intervention {index}",
        "C": comparator if comparator is not None else [f"Comparator {index}"],
        "O": f"Outcome {index}",
        "S": "SLOT",
        "Dataset": dataset,
    }


def test_row_to_question_example_handles_null_and_multivalue_comparator() -> None:
    example = row_to_question_example(_row(1, comparator=[" A ", "", "B", "A"]))
    assert example.question_id == "A::q1"
    assert example.gold_slots["C"] == ["A", "B"]


def test_row_to_question_example_converts_nulls_to_empty_lists() -> None:
    row = _row(2)
    row["P"] = None
    row["C"] = None
    example = row_to_question_example(row)
    assert example.metadata["source_index"] == "q2"
    assert example.gold_slots["P"] == []
    assert example.gold_slots["C"] == []


def test_build_split_manifest_is_deterministic_and_matches_sizes() -> None:
    examples = [
        row_to_question_example(_row(i, dataset="A" if i < 34 else ("B" if i < 67 else "C")))
        for i in range(99)
    ]
    manifest1 = build_split_manifest(examples, seed=DEFAULT_SPLIT_SEED)
    manifest2 = build_split_manifest(examples, seed=DEFAULT_SPLIT_SEED)
    assert manifest1 == manifest2
    assert manifest1["splits"]["fewshot20"]["question_count"] == 20
    assert manifest1["splits"]["dev20"]["question_count"] == 20
    assert manifest1["splits"]["test59"]["question_count"] == 59


def test_prepare_question_data_writes_expected_outputs(tmp_path, monkeypatch) -> None:
    dataset_dir = tmp_path / "Clinical_Questions"
    dataset_dir.mkdir()
    (dataset_dir / "train-00000-of-00001.parquet").write_text("placeholder", encoding="utf-8")
    fake_rows = [_row(i, dataset="A" if i < 50 else "B") for i in range(99)]

    monkeypatch.setattr("q2pico.question_data._load_rows_from_parquet_dir", lambda _path: fake_rows)
    summary = prepare_question_data(dataset_dir, tmp_path / "results" / "data", force=True)

    manifest_path = tmp_path / "results" / "data" / "manifests" / "question_split_v1.json"
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["splits"]["test59"]["question_count"] == 59
    assert (tmp_path / "results" / "tables" / "dataset_summary.csv").exists()
    assert (tmp_path / "results" / "tables" / "question_split_summary.csv").exists()
    assert summary["manifest_version"] == "question_split_v1"
