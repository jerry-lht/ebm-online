from __future__ import annotations

import json

import pytest

from pico.cli.validate_llm_predictions import main
from pico.io_utils import read_span_predictions, write_document_examples, write_jsonl
from pico.schemas import DocumentExample
from pico.validate_llm import LLM_VALIDATOR_VERSION, validate_llm_predictions


def _example(doc_id: str = "d1", abstract: str = "alpha beta alpha gamma") -> DocumentExample:
    return DocumentExample(
        doc_id=doc_id,
        split="test",
        abstract=abstract,
        tokens=["alpha", "beta", "alpha", "gamma"],
        token_offsets=[(0, 5), (6, 10), (11, 16), (17, 22)],
        gold_spans=[],
        bio_labels=["O", "O", "O", "O"],
    )


def _raw(doc_id: str, items: object) -> dict[str, object]:
    return {"doc_id": doc_id, "response": json.dumps(items), "metadata": {}}


def test_valid_json_response_generates_evaluator_compatible_span() -> None:
    spans, quality = validate_llm_predictions(
        [_example()],
        [_raw("d1", [{"label": "P", "text": "beta", "char_start": 6, "char_end": 10}])],
    )

    assert len(spans) == 1
    assert spans[0].doc_id == "d1"
    assert spans[0].label == "P"
    assert spans[0].start_token == 1
    assert spans[0].end_token == 2
    assert spans[0].char_start == 6
    assert spans[0].char_end == 10
    assert spans[0].metadata["validator_version"] == LLM_VALIDATOR_VERSION
    assert quality["counts"]["written_spans"] == 1
    assert quality["invalid_json_rate"] == 0
    assert quality["per_doc"]["d1"]["invalid_json_rate"] == 0
    assert quality["per_doc"]["d1"]["schema_invalid_rate"] == 0


def test_invalid_json_does_not_stop_batch_and_counts_rate() -> None:
    rows = [
        {"doc_id": "d1", "response": "[not json]"},
        _raw("d1", [{"label": "I", "text": "gamma", "char_start": 17, "char_end": 22}]),
    ]

    spans, quality = validate_llm_predictions([_example()], rows)

    assert len(spans) == 1
    assert quality["counts"]["invalid_json_responses"] == 1
    assert quality["invalid_json_rate"] == 0.5


def test_schema_missing_field_illegal_label_and_unknown_doc_id_count_invalid_items() -> None:
    rows = [
        _raw("d1", [{"label": "P", "char_start": 0, "char_end": 5}]),
        _raw("d1", [{"label": "X", "text": "alpha", "char_start": 0, "char_end": 5}]),
        _raw("missing", [{"label": "P", "text": "alpha", "char_start": 0, "char_end": 5}]),
    ]

    spans, quality = validate_llm_predictions([_example()], rows)

    assert spans == []
    assert quality["counts"]["response_items"] == 3
    assert quality["counts"]["schema_invalid_items"] == 3
    assert quality["counts"]["unknown_doc_items"] == 1
    assert quality["schema_invalid_rate"] == 1


def test_offset_out_of_bounds_and_substring_mismatch_are_counted_separately() -> None:
    rows = [
        _raw("d1", [{"label": "P", "text": "alpha", "char_start": -1, "char_end": 5}]),
        _raw("d1", [{"label": "P", "text": "wrong", "char_start": 0, "char_end": 5}]),
    ]

    spans, quality = validate_llm_predictions([_example()], rows)

    assert spans == []
    assert quality["counts"]["invalid_offset_items"] == 1
    assert quality["counts"]["non_extractive_items"] == 1
    assert quality["invalid_offset_rate"] == 0.5
    assert quality["non_extractive_span_rate"] == 0.5


def test_char_offsets_must_map_to_official_token_boundaries() -> None:
    spans, quality = validate_llm_predictions(
        [_example()],
        [_raw("d1", [{"label": "P", "text": "lph", "char_start": 1, "char_end": 4}])],
    )

    assert spans == []
    assert quality["counts"]["token_boundary_invalid_items"] == 1
    assert quality["counts"]["invalid_offset_items"] == 1


def test_text_only_missing_offsets_counts_unambiguous_and_ambiguous_matches() -> None:
    rows = [
        _raw("d1", [{"label": "P", "text": "beta"}]),
        _raw("d1", [{"label": "P", "text": "alpha"}]),
        _raw("d1", [{"label": "P", "text": "missing"}]),
    ]

    spans, quality = validate_llm_predictions([_example()], rows)

    assert len(spans) == 1
    assert spans[0].text == "beta"
    assert spans[0].char_start == 6
    assert spans[0].char_end == 10
    assert spans[0].metadata["validation_mode"] == "text_unique_match"
    assert quality["counts"]["missing_offset_items"] == 3
    assert quality["counts"]["unambiguous_text_only_items"] == 1
    assert quality["counts"]["ambiguous_match_items"] == 1
    assert quality["ambiguous_match_rate"] == 1 / 3
    assert quality["counts"]["non_extractive_items"] == 1


def test_duplicate_span_is_deduped_and_counted() -> None:
    item = {"label": "O", "text": "beta", "char_start": 6, "char_end": 10}
    spans, quality = validate_llm_predictions([_example()], [_raw("d1", [item, item])])

    assert len(spans) == 1
    assert quality["counts"]["valid_spans"] == 2
    assert quality["counts"]["duplicate_spans"] == 1
    assert quality["duplicate_span_rate"] == 0.5


def test_overlap_conflict_document_and_token_rates() -> None:
    rows = [
        _raw(
            "d1",
            [
                {"label": "P", "text": "alpha beta", "char_start": 0, "char_end": 10},
                {"label": "I", "text": "beta alpha", "char_start": 6, "char_end": 16},
            ],
        )
    ]

    spans, quality = validate_llm_predictions([_example()], rows)

    assert len(spans) == 2
    assert quality["counts"]["overlap_conflict_documents"] == 1
    assert quality["counts"]["overlap_conflict_tokens"] == 1
    assert quality["overlap_conflict_document_rate"] == 1
    assert quality["overlap_conflict_token_rate"] == 1 / 4
    assert quality["per_doc"]["d1"]["overlap_conflict_document_rate"] == 1
    assert quality["per_doc"]["d1"]["overlap_conflict_token_rate"] == 1 / 4


def test_cli_writes_validated_spans_quality_json_and_quality_csv(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    raw_path = tmp_path / "raw.jsonl"
    spans_path = tmp_path / "validated.spans.jsonl"
    quality_path = tmp_path / "quality.json"
    tables_dir = tmp_path / "tables"
    write_document_examples(examples_path, [_example()])
    write_jsonl(
        raw_path,
        [_raw("d1", [{"label": "P", "text": "beta", "char_start": 6, "char_end": 10}])],
    )

    assert (
        main(
            [
                "--examples",
                str(examples_path),
                "--raw",
                str(raw_path),
                "--valid-output",
                str(spans_path),
                "--quality-output",
                str(quality_path),
                "--tables-dir",
                str(tables_dir),
                "--method",
                "m",
                "--setting",
                "s",
                "--split",
                "test",
            ]
        )
        == 0
    )

    spans = read_span_predictions(spans_path)
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    csv_text = (tables_dir / "llm_quality.csv").read_text(encoding="utf-8")
    assert len(spans) == 1
    assert quality["validator_version"] == LLM_VALIDATOR_VERSION
    assert quality["counts"]["written_spans"] == 1
    assert "invalid_json_rate" in csv_text
    with pytest.raises(ValueError, match="pass --force"):
        main(
            [
                "--examples",
                str(examples_path),
                "--raw",
                str(raw_path),
                "--valid-output",
                str(spans_path),
                "--quality-output",
                str(quality_path),
                "--tables-dir",
                str(tables_dir),
                "--method",
                "m",
                "--setting",
                "s",
                "--split",
                "test",
            ]
        )
