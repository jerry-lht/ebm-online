from __future__ import annotations

import pytest

from screening.io_utils import (
    normalize_prediction_response,
    read_json,
    read_jsonl,
    read_model_jsonl,
    read_prediction_jsonl,
    validate_prediction,
    write_json,
    write_jsonl,
    write_model_jsonl,
)
from screening.schemas import (
    AbstractScreeningPrediction,
    ScreeningExample,
    ScreeningPrediction,
    TextSection,
)


def _toy_example(example_id: str = "example-1") -> ScreeningExample:
    return ScreeningExample(
        example_id=example_id,
        benchmark="q2crbench",
        split="train",
        review_id="review-1",
        study_id="study-1",
        title="Trial title",
        abstract="Trial abstract",
        input_setting="abstract_only",
        metadata={"PICO_IDX": "PICO-1"},
    )


def test_json_round_trip(tmp_path) -> None:
    path = tmp_path / "payload.json"
    write_json(path, {"b": 2, "a": 1})

    assert read_json(path) == {"a": 1, "b": 2}
    assert path.read_text(encoding="utf-8").endswith("\n")


def test_jsonl_round_trip(tmp_path) -> None:
    path = tmp_path / "records.jsonl"
    write_jsonl(path, [{"id": 1}, {"id": 2}])

    assert read_jsonl(path) == [{"id": 1}, {"id": 2}]


def test_jsonl_reports_bad_line(tmp_path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text('{"id": 1}\nnot-json\n', encoding="utf-8")

    with pytest.raises(ValueError, match="line 2"):
        read_jsonl(path)


def test_model_jsonl_round_trip(tmp_path) -> None:
    path = tmp_path / "examples.jsonl"
    examples = [
        _toy_example("example-1"),
        ScreeningExample(
            example_id="example-2",
            benchmark="csmed_ft",
            split="test",
            review_id="CD000001",
            study_id="doc-2",
            full_text_sections=[TextSection(title="Methods", text="Methods text.")],
            input_setting="full_text_only",
        ),
    ]
    write_model_jsonl(path, examples)

    loaded = read_model_jsonl(path, ScreeningExample)
    assert [item.example_id for item in loaded] == ["example-1", "example-2"]
    assert loaded[0].metadata["PICO_IDX"] == "PICO-1"


def test_validate_prediction_accepts_valid_payload() -> None:
    prediction, errors = validate_prediction(
        {
            "example_id": "example-1",
            "decision": "include",
            "criterion_judgments": {
                "population": {
                    "text": "Population remains unclear",
                    "judgment": "unclear",
                    "evidence_spans": [{"text": "Insufficient population detail."}],
                }
            },
            "evidence_spans": [{"text": "No age criteria reported."}],
        }
    )

    assert errors == []
    assert isinstance(prediction, ScreeningPrediction)
    assert prediction.decision == "include"


def test_validate_prediction_returns_schema_errors() -> None:
    prediction, errors = validate_prediction({"example_id": "example-1", "decision": "maybe"})

    assert prediction is None
    assert any("decision" in error for error in errors)


def test_validate_prediction_returns_missing_field_errors() -> None:
    prediction, errors = validate_prediction({"example_id": "example-1"})

    assert prediction is None
    assert any("decision" in error for error in errors)


def test_validate_abstract_prediction_requires_main_reason() -> None:
    prediction, errors = validate_prediction(
        {"example_id": "example-1", "decision": "include", "main_reason": "Relevant abstract."},
        prediction_model=AbstractScreeningPrediction,
    )

    assert errors == []
    assert isinstance(prediction, AbstractScreeningPrediction)

    prediction, errors = validate_prediction(
        {"example_id": "example-1", "decision": "include"},
        prediction_model=AbstractScreeningPrediction,
    )

    assert prediction is None
    assert any("main_reason" in error for error in errors)


def test_normalize_prediction_response_records_non_json() -> None:
    prediction, metadata = normalize_prediction_response(
        example_id="example-1",
        raw_response="not json",
        provider="openai",
        model="example-model",
    )

    assert prediction is None
    assert metadata.raw_response == "not json"
    assert metadata.parsed_json is None
    assert metadata.provider == "openai"
    assert metadata.validation_errors


def test_normalize_prediction_response_records_validation_errors() -> None:
    prediction, metadata = normalize_prediction_response(
        example_id="example-1",
        raw_response='{"decision": "exclude", "criterion_judgments": {"population": {"text": "Adults with CKD", "judgment": "maybe"}}}',
    )

    assert prediction is None
    assert metadata.parsed_json == {
        "decision": "exclude",
        "criterion_judgments": {"population": {"text": "Adults with CKD", "judgment": "maybe"}},
    }
    assert any("criterion_judgments.population.judgment" in error for error in metadata.validation_errors)


def test_normalize_prediction_response_attaches_raw_metadata() -> None:
    prediction, metadata = normalize_prediction_response(
        example_id="example-1",
        raw_response='{"decision": "include", "criterion_judgments": {}, "failed_criterion": null, "main_reason": "ok", "evidence_spans": []}',
        request_id="req-1",
    )

    assert prediction is not None
    assert metadata.validation_errors == []
    assert prediction.raw_response_metadata.request_id == "req-1"
    assert prediction.raw_response_metadata.parsed_json == {
        "decision": "include",
        "criterion_judgments": {},
        "failed_criterion": None,
        "main_reason": "ok",
        "evidence_spans": [],
    }


def test_normalize_prediction_response_supports_abstract_minimal_schema() -> None:
    prediction, metadata = normalize_prediction_response(
        example_id="example-1",
        raw_response='{"decision": "include", "main_reason": "Abstract is plausibly relevant."}',
        prediction_model=AbstractScreeningPrediction,
    )

    assert prediction is not None
    assert isinstance(prediction, AbstractScreeningPrediction)
    assert metadata.validation_errors == []
    assert prediction.main_reason == "Abstract is plausibly relevant."


def test_read_prediction_jsonl_supports_minimal_and_rich_records(tmp_path) -> None:
    path = tmp_path / "predictions.jsonl"
    write_jsonl(
        path,
        [
            {
                "example_id": "example-1",
                "decision": "include",
                "main_reason": "Abstract remains relevant.",
                "metadata": {
                    "input_setting": "abstract_only",
                    "prediction_schema": "abstract_only_v3",
                },
            },
            {
                "example_id": "example-2",
                "decision": "exclude",
                "criterion_judgments": {},
                "failed_criterion": "population",
                "main_reason": "Wrong population.",
                "evidence_spans": [],
                "metadata": {"input_setting": "full_text_only"},
            },
        ],
    )

    predictions = read_prediction_jsonl(path)

    assert isinstance(predictions[0], AbstractScreeningPrediction)
    assert isinstance(predictions[1], ScreeningPrediction)
