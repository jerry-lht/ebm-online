from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from screening.schemas import (
    AbstractScreeningPrediction,
    CriterionJudgment,
    CriterionOnlyJudgment,
    CriterionOnlyResponse,
    Decision,
    EvidenceSpan,
    InputSetting,
    RunMetadata,
    ScreeningExample,
    ScreeningPrediction,
    TextSection,
)


def test_abstract_only_example_validates() -> None:
    example = ScreeningExample(
        example_id="q2crbench:train:review-1:study-1",
        benchmark="q2crbench",
        split="train",
        review_id="review-1",
        study_id="study-1",
        question="Should the study be included?",
        title="Trial title",
        abstract="Trial abstract",
        input_setting=InputSetting.abstract_only,
        gold_decision="include",
    )

    assert example.gold_decision == "include"
    assert example.input_setting == InputSetting.abstract_only


def test_full_text_only_example_validates() -> None:
    example = ScreeningExample(
        example_id="csmed-ft:test:CD000001:doc-1",
        benchmark="csmed_ft",
        split="test",
        review_id="CD000001",
        study_id="doc-1",
        full_text_sections=[TextSection(title="Methods", text="Randomized trial methods.")],
        input_setting=InputSetting.full_text_only,
        gold_decision="exclude",
    )

    assert example.full_text_sections[0].title == "Methods"


def test_abstract_plus_full_text_example_validates() -> None:
    example = ScreeningExample(
        example_id="csmed-ft:test:CD000001:doc-2",
        benchmark="csmed_ft",
        split="test",
        review_id="CD000001",
        study_id="doc-2",
        title="Study title",
        evidence_profile=[TextSection(title="Characteristics", text="Study characteristics.")],
        input_setting=InputSetting.abstract_plus_full_text,
    )

    assert example.evidence_profile[0].source is None


def test_evidence_profile_example_validates_without_full_text_sections() -> None:
    example = ScreeningExample(
        example_id="q2crbench:train:review-1:study-1",
        benchmark="q2crbench",
        split="train",
        review_id="review-1",
        study_id="study-1",
        evidence_profile=[TextSection(title="GRADE", text="Evidence profile text.")],
        input_setting=InputSetting.evidence_profile,
    )

    assert example.full_text_sections == []
    assert example.input_setting == InputSetting.evidence_profile


def test_input_setting_requires_matching_text() -> None:
    with pytest.raises(ValidationError):
        ScreeningExample(
            example_id="missing-text",
            benchmark="q2crbench",
            split="train",
            review_id="review-1",
            study_id="study-1",
            input_setting=InputSetting.full_text_only,
        )


def test_prediction_schema_validates_nested_judgments() -> None:
    prediction = ScreeningPrediction(
        example_id="example-1",
        decision=Decision.exclude,
        failed_criterion="population",
        main_reason="Wrong population.",
        evidence_spans=[EvidenceSpan(text="Participants were adults with a different disease.")],
        criterion_judgments={
            "population": CriterionJudgment(
                text="Adults with a different disease population",
                judgment="no",
                evidence_spans=[EvidenceSpan(text="Adults with a different disease.")],
                reason="Population does not match.",
            )
        },
    )

    assert prediction.decision == Decision.exclude
    assert prediction.criterion_judgments["population"].judgment == "no"


def test_prediction_schema_coerces_string_evidence_spans() -> None:
    prediction = ScreeningPrediction(
        example_id="example-1",
        decision=Decision.include,
        evidence_spans=["Top-level evidence"],
        criterion_judgments={
            "population": CriterionJudgment(
                text="Adults with CKD",
                judgment="yes",
                evidence_spans=["Criterion evidence"],
                reason="Population matches.",
            )
        },
    )

    assert prediction.evidence_spans[0].text == "Top-level evidence"
    assert prediction.criterion_judgments["population"].evidence_spans[0].text == "Criterion evidence"


def test_minimal_criterion_only_schema_requires_text_and_restricts_judgments() -> None:
    payload = CriterionOnlyResponse(
        criterion_judgments={
            "inc_1": CriterionOnlyJudgment(
                text="Adults with chronic kidney disease",
                judgment="yes",
            ),
            "exc_1": CriterionOnlyJudgment(
                text="Protocol-only publication",
                judgment="unclear",
            ),
        }
    )

    assert payload.criterion_judgments["inc_1"].text == "Adults with chronic kidney disease"

    with pytest.raises(ValidationError):
        CriterionOnlyJudgment(text="", judgment="yes")

    with pytest.raises(ValidationError):
        CriterionOnlyJudgment(text="Comparator required", judgment="not_applicable")

    with pytest.raises(ValidationError):
        CriterionOnlyResponse(
            criterion_judgments={
                "population": CriterionOnlyJudgment(text="Adults with CKD", judgment="yes")
            }
        )


def test_abstract_prediction_schema_requires_main_reason() -> None:
    prediction = AbstractScreeningPrediction(
        example_id="example-1",
        decision=Decision.include,
        main_reason="Abstract remains plausibly relevant to the review topic.",
    )

    assert prediction.main_reason.startswith("Abstract remains")

    with pytest.raises(ValidationError):
        AbstractScreeningPrediction(
            example_id="example-1",
            decision=Decision.include,
            main_reason="",
        )


def test_prediction_rejects_invalid_values() -> None:
    with pytest.raises(ValidationError):
        ScreeningPrediction(example_id="example-1", decision="maybe")

    with pytest.raises(ValidationError):
        CriterionJudgment(judgment="partly")

    with pytest.raises(ValidationError):
        AbstractScreeningPrediction(
            example_id="example-1",
            decision="maybe",
            main_reason="Invalid decision.",
        )


def test_missing_required_example_fields_fail() -> None:
    with pytest.raises(ValidationError):
        ScreeningExample(
            example_id="",
            benchmark="q2crbench",
            split="train",
            review_id="review-1",
            study_id="study-1",
        )


def test_run_metadata_validates_time_order() -> None:
    with pytest.raises(ValidationError):
        RunMetadata(
            run_id="run-1",
            method="direct",
            started_at=datetime(2026, 5, 14, 12, tzinfo=timezone.utc),
            ended_at=datetime(2026, 5, 14, 11, tzinfo=timezone.utc),
        )
