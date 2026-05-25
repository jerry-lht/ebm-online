from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest

from pico.ebm_data import (
    EBMDataError,
    build_document_manifest_row,
    build_split_summary_rows,
    count_overlap_tokens,
    count_positive_runs,
    has_label_overlap,
    load_ebm_nlp_archive,
    parse_binary_ann,
    prepare_ebm_nlp_data,
)
from pico.io_utils import read_document_examples, read_json, read_jsonl


def test_parse_binary_ann_rejects_invalid_values() -> None:
    assert parse_binary_ann("0\n1\n\n0\n", "toy.ann") == [0, 1, 0]
    with pytest.raises(EBMDataError, match="Invalid annotation value"):
        parse_binary_ann("0\n2\n", "toy.ann")


def test_count_positive_runs() -> None:
    assert count_positive_runs([]) == 0
    assert count_positive_runs([0, 0, 0]) == 0
    assert count_positive_runs([1, 1, 1]) == 1
    assert count_positive_runs([0, 1, 1, 0, 1, 0, 1, 1]) == 3


def test_has_label_overlap() -> None:
    assert not has_label_overlap({"P": [1, 0], "I": [0, 1], "O": [0, 0]})
    assert has_label_overlap({"P": [1, 0], "I": [1, 0], "O": [0, 0]})
    assert count_overlap_tokens({"P": [1, 0], "I": [1, 1], "O": [0, 1]}) == 2


def test_manifest_and_summary_rows() -> None:
    labels = {"P": [1, 1, 0], "I": [0, 1, 0], "O": [0, 0, 1]}
    row = build_document_manifest_row("1", "train", 3, labels)
    assert row.p_span_count == 1
    assert row.i_span_count == 1
    assert row.o_span_count == 1
    assert row.total_span_count == 3
    assert row.has_overlap
    assert row.overlap_token_count == 1

    summary = build_split_summary_rows([row])
    assert summary[0] == {
        "split": "train",
        "doc_count": 1,
        "token_count": 3,
        "p_span_count": 1,
        "i_span_count": 1,
        "o_span_count": 1,
        "overlap_doc_count": 1,
        "overlap_token_count": 1,
    }
    assert summary[1]["split"] == "test"
    assert summary[1]["doc_count"] == 0


def test_load_tiny_synthetic_tar_end_to_end(tmp_path: Path) -> None:
    tar_path = tmp_path / "ebm_nlp_2_00.tar.gz"
    _write_synthetic_tar(tar_path)

    loaded = load_ebm_nlp_archive(tar_path)
    assert [example.doc_id for example in loaded["examples"]["train"]] == ["100"]
    assert [example.doc_id for example in loaded["examples"]["test"]] == ["200"]
    train_example = loaded["examples"]["train"][0]
    assert train_example.token_offsets == [(0, 5), (6, 10), (11, 16)]
    assert [(span.label, span.start_token, span.end_token, span.text) for span in train_example.gold_spans] == [
        ("P", 0, 1, "alpha"),
        ("I", 1, 2, "beta"),
        ("O", 2, 3, "gamma"),
    ]
    assert train_example.bio_labels == ["I-PAR", "I-INT", "I-OUT"]
    assert train_example.metadata["pico_token_labels"]["P"] == [1, 0, 0]
    assert train_example.metadata["multi_label_token_coverage"] == train_example.metadata["pico_token_labels"]
    assert train_example.metadata["overlap_conflict"]["has_conflict"] is False
    assert train_example.metadata["overlap_conflict"]["conflict_token_count"] == 0
    assert train_example.metadata["span_counts"]["total"] == 3
    assert loaded["offset_failures"] == []

    output_dir = tmp_path / "results" / "data"
    summary = prepare_ebm_nlp_data(tar_path, output_dir)
    assert summary["splits"]["train"]["doc_count"] == 1
    assert summary["splits"]["test"]["doc_count"] == 1
    assert (output_dir / "train.examples.jsonl").exists()
    assert (output_dir / "test.examples.jsonl").exists()
    assert (output_dir / "offset_failures.jsonl").exists()
    assert (output_dir / "manifests" / "document_manifest.csv").exists()
    assert (tmp_path / "results" / "tables" / "dataset_summary.csv").exists()
    summary_json = read_json(output_dir / "data_summary.json")
    assert summary_json["phase"] == "phase4_gold_span_bio_conversion"
    assert summary_json["offset_failure_count"] == 0
    assert summary_json["splits"]["train"]["overlap_token_count"] == 0
    assert read_document_examples(output_dir / "train.examples.jsonl")[0].token_offsets == [
        (0, 5),
        (6, 10),
        (11, 16),
    ]
    assert list(read_jsonl(output_dir / "offset_failures.jsonl")) == []

    with pytest.raises(EBMDataError, match="Output files already exist"):
        prepare_ebm_nlp_data(tar_path, output_dir)


def test_missing_label_annotation_file_is_empty_label_set(tmp_path: Path) -> None:
    tar_path = tmp_path / "ebm_nlp_2_00.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        for doc_id, split_subdir in (("100", "train"), ("101", "train"), ("200", "test/gold")):
            _add_text(tar, f"ebm_nlp_2_00/documents/{doc_id}.txt", "alpha beta\n")
            _add_text(tar, f"ebm_nlp_2_00/documents/{doc_id}.tokens", "alpha\nbeta\n")
            for directory in ("participants", "outcomes"):
                _add_text(
                    tar,
                    "ebm_nlp_2_00/annotations/aggregated/starting_spans/"
                    f"{directory}/{split_subdir}/{doc_id}.AGGREGATED.ann",
                    "0\n0\n",
                )
            if doc_id != "100":
                _add_text(
                    tar,
                    "ebm_nlp_2_00/annotations/aggregated/starting_spans/"
                    f"interventions/{split_subdir}/{doc_id}.AGGREGATED.ann",
                    "0\n1\n",
                )

    loaded = load_ebm_nlp_archive(tar_path)
    train_example = loaded["examples"]["train"][0]
    assert train_example.metadata["pico_token_labels"]["I"] == [0, 0]
    assert train_example.metadata["source_paths"]["I"] is None


def test_offset_alignment_failures_are_recorded_without_stopping_prepare_data(
    tmp_path: Path,
) -> None:
    tar_path = tmp_path / "ebm_nlp_2_00.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        _add_text(tar, "ebm_nlp_2_00/documents/100.txt", "alpha beta\n")
        _add_text(tar, "ebm_nlp_2_00/documents/100.tokens", "alpha\ngamma\n")
        for directory in ("participants", "interventions", "outcomes"):
            _add_text(
                tar,
                "ebm_nlp_2_00/annotations/aggregated/starting_spans/"
                f"{directory}/train/100.AGGREGATED.ann",
                "0\n0\n",
            )

        _add_text(tar, "ebm_nlp_2_00/documents/200.txt", "alpha beta\n")
        _add_text(tar, "ebm_nlp_2_00/documents/200.tokens", "alpha\nbeta\n")
        for directory in ("participants", "interventions", "outcomes"):
            _add_text(
                tar,
                "ebm_nlp_2_00/annotations/aggregated/starting_spans/"
                f"{directory}/test/gold/200.AGGREGATED.ann",
                "0\n0\n",
            )

    loaded = load_ebm_nlp_archive(tar_path)
    assert loaded["examples"]["train"][0].token_offsets == []
    assert loaded["offset_failures"] == [
        {
            "doc_id": "100",
            "split": "train",
            "token_index": 1,
            "token": "gamma",
            "cursor": 5,
            "reason": "Token not found after cursor",
            "source_paths": {
                "text": "ebm_nlp_2_00/documents/100.txt",
                "tokens": "ebm_nlp_2_00/documents/100.tokens",
                "P": "ebm_nlp_2_00/annotations/aggregated/starting_spans/participants/train/100.AGGREGATED.ann",
                "I": "ebm_nlp_2_00/annotations/aggregated/starting_spans/interventions/train/100.AGGREGATED.ann",
                "O": "ebm_nlp_2_00/annotations/aggregated/starting_spans/outcomes/train/100.AGGREGATED.ann",
            },
        }
    ]

    output_dir = tmp_path / "results" / "data"
    summary = prepare_ebm_nlp_data(tar_path, output_dir)
    data_summary = read_json(output_dir / "data_summary.json")
    failures = list(read_jsonl(output_dir / "offset_failures.jsonl"))

    assert summary["offset_failure_count"] == 1
    assert data_summary["warning_count"] == 1
    assert data_summary["offset_failure_count"] == 1
    assert data_summary["offset_failure_path"].endswith("offset_failures.jsonl")
    assert failures[0]["doc_id"] == "100"
    assert failures[0]["reason"] == "Token not found after cursor"


def _write_synthetic_tar(path: Path) -> None:
    with tarfile.open(path, "w:gz") as tar:
        for doc_id, split_subdir in (("100", "train"), ("200", "test/gold")):
            _add_text(tar, f"ebm_nlp_2_00/documents/{doc_id}.txt", "alpha beta gamma\n")
            _add_text(tar, f"ebm_nlp_2_00/documents/{doc_id}.tokens", "alpha\nbeta\ngamma\n")
            labels = {
                "participants": "1\n0\n0\n",
                "interventions": "0\n1\n0\n",
                "outcomes": "0\n0\n1\n",
            }
            for directory, content in labels.items():
                _add_text(
                    tar,
                    "ebm_nlp_2_00/annotations/aggregated/starting_spans/"
                    f"{directory}/{split_subdir}/{doc_id}.AGGREGATED.ann",
                    content,
                )


def _add_text(tar: tarfile.TarFile, name: str, content: str) -> None:
    data = content.encode("utf-8")
    info = tarfile.TarInfo(name)
    info.size = len(data)
    tar.addfile(info, io.BytesIO(data))
