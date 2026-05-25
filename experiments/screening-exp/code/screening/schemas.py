"""Shared schemas for screening examples, predictions, and run metadata."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Decision(str, Enum):
    """Normalized model decision values."""

    include = "include"
    exclude = "exclude"


class GoldDecision(str, Enum):
    """Gold labels used by decision evaluators."""

    include = "include"
    exclude = "exclude"


class CriterionJudgmentValue(str, Enum):
    """Allowed criterion-level judgment labels."""

    yes = "yes"
    no = "no"
    unclear = "unclear"
    not_applicable = "not_applicable"


class CriterionGroup(str, Enum):
    """Allowed criterion groups for criterion-wise screening."""

    inclusion = "inclusion"
    exclusion = "exclusion"


class InputSetting(str, Enum):
    """Supported text input settings for screening methods."""

    abstract_only = "abstract_only"
    evidence_profile = "evidence_profile"
    full_text_only = "full_text_only"
    abstract_plus_full_text = "abstract_plus_full_text"


class TextSection(BaseModel):
    """A named section of source text."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    text: str
    source: str | None = None
    section_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must be non-empty")
        return value


class Pico(BaseModel):
    """PICO/PICOS fields associated with a review question."""

    model_config = ConfigDict(extra="forbid")

    population: str | None = None
    intervention: str | None = None
    comparator: str | list[str] | None = None
    outcome: str | None = None
    study_design: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScreeningCriteria(BaseModel):
    """Review inclusion and exclusion criteria."""

    model_config = ConfigDict(extra="forbid")

    inclusion: list[str] = Field(default_factory=list)
    exclusion: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class ScreeningExample(BaseModel):
    """Unified example schema consumed by screening methods."""

    model_config = ConfigDict(extra="forbid")

    example_id: str
    benchmark: str
    split: str
    review_id: str
    study_id: str
    question: str | None = None
    pico: Pico = Field(default_factory=Pico)
    criteria: ScreeningCriteria = Field(default_factory=ScreeningCriteria)
    title: str | None = None
    abstract: str | None = None
    full_text_sections: list[TextSection] = Field(default_factory=list)
    evidence_profile: list[TextSection] = Field(default_factory=list)
    gold_decision: GoldDecision | None = None
    gold_reason: str | None = None
    input_setting: InputSetting | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("example_id", "benchmark", "split", "review_id", "study_id")
    @classmethod
    def required_strings_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("required string fields must be non-empty")
        return value

    @field_validator("question", "title", "abstract", "gold_reason")
    @classmethod
    def optional_blank_strings_to_none(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def validate_text_available_for_setting(self) -> "ScreeningExample":
        if self.input_setting is None:
            return self

        has_abstract = bool((self.title or "").strip() or (self.abstract or "").strip())
        has_full_text = bool(self.full_text_sections or self.evidence_profile)

        if self.input_setting == InputSetting.abstract_only and not has_abstract:
            raise ValueError("abstract_only examples require title or abstract")
        if self.input_setting == InputSetting.evidence_profile and not self.evidence_profile:
            raise ValueError("evidence_profile examples require evidence profile sections")
        if self.input_setting == InputSetting.full_text_only and not has_full_text:
            raise ValueError("full_text_only examples require full text or evidence profile")
        if self.input_setting == InputSetting.abstract_plus_full_text and not (
            has_abstract and has_full_text
        ):
            raise ValueError(
                "abstract_plus_full_text examples require abstract/title and full text/evidence"
            )
        return self


class EvidenceSpan(BaseModel):
    """Evidence span cited by a prediction."""

    model_config = ConfigDict(extra="forbid")

    text: str
    source: str | None = None
    section_id: str | None = None
    start_char: int | None = Field(default=None, ge=0)
    end_char: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("text")
    @classmethod
    def span_text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must be non-empty")
        return value

    @model_validator(mode="after")
    def validate_offsets(self) -> "EvidenceSpan":
        if self.start_char is not None and self.end_char is not None:
            if self.end_char < self.start_char:
                raise ValueError("end_char must be greater than or equal to start_char")
        return self


class CriterionJudgment(BaseModel):
    """Model judgment for one screening criterion."""

    model_config = ConfigDict(extra="forbid")

    text: str | None = None
    judgment: CriterionJudgmentValue
    evidence_spans: list[EvidenceSpan] = Field(default_factory=list)
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("text")
    @classmethod
    def optional_text_to_none(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            if not value:
                return None
        return value

    @field_validator("evidence_spans", mode="before")
    @classmethod
    def coerce_string_evidence_spans(
        cls, value: list[EvidenceSpan | dict[str, Any] | str] | None
    ) -> list[EvidenceSpan | dict[str, Any]]:
        if value is None:
            return []
        normalized: list[EvidenceSpan | dict[str, Any]] = []
        for item in value:
            if isinstance(item, str):
                normalized.append({"text": item})
            else:
                normalized.append(item)
        return normalized

    @field_validator("reason")
    @classmethod
    def optional_reason_to_none(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            return None
        return value


class CriterionOnlyJudgment(BaseModel):
    """Minimal criterion-wise judgment returned by the Phase 8 one-shot prompt."""

    model_config = ConfigDict(extra="forbid")

    text: str
    judgment: CriterionJudgmentValue

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must be non-empty")
        return value

    @field_validator("judgment")
    @classmethod
    def judgment_must_use_minimal_label_set(cls, value: CriterionJudgmentValue) -> CriterionJudgmentValue:
        if value == CriterionJudgmentValue.not_applicable:
            raise ValueError("judgment must be one of yes, no, unclear")
        return value


class CriterionOnlyResponse(BaseModel):
    """Minimal JSON payload expected from the Phase 8 criterion-wise prompt."""

    model_config = ConfigDict(extra="forbid")

    criterion_judgments: dict[str, CriterionOnlyJudgment]

    @field_validator("criterion_judgments")
    @classmethod
    def criterion_keys_must_use_inc_exc_prefix(
        cls, value: dict[str, CriterionOnlyJudgment]
    ) -> dict[str, CriterionOnlyJudgment]:
        invalid = [
            criterion_id
            for criterion_id in value
            if not (criterion_id.startswith("inc_") or criterion_id.startswith("exc_"))
        ]
        if invalid:
            invalid_text = ", ".join(sorted(invalid))
            raise ValueError(f"criterion ids must start with inc_ or exc_: {invalid_text}")
        return value


class CriterionSpec(BaseModel):
    """One criterion derived from review clauses or fallback logic."""

    model_config = ConfigDict(extra="forbid")

    criterion_id: str
    criterion_group: CriterionGroup
    criterion_text: str
    required: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("criterion_id", "criterion_text")
    @classmethod
    def criterion_strings_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("criterion strings must be non-empty")
        return value


class EvidenceItem(BaseModel):
    """One retrieved evidence chunk available to the criterion-wise prompt."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    text: str
    source: str
    section_id: str
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("evidence_id", "text", "source", "section_id")
    @classmethod
    def evidence_strings_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("evidence strings must be non-empty")
        return value


class RawResponseMetadata(BaseModel):
    """Raw model response and parser metadata retained for auditability."""

    model_config = ConfigDict(extra="forbid")

    raw_response: str | None = None
    parsed_json: dict[str, Any] | None = None
    validation_errors: list[str] = Field(default_factory=list)
    provider: str | None = None
    model: str | None = None
    request_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseScreeningPrediction(BaseModel):
    """Shared prediction fields required by evaluators and run outputs."""

    model_config = ConfigDict(extra="forbid")

    example_id: str
    decision: Decision
    raw_response_metadata: RawResponseMetadata = Field(default_factory=RawResponseMetadata)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("example_id")
    @classmethod
    def example_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("example_id must be non-empty")
        return value


class AbstractScreeningPrediction(BaseScreeningPrediction):
    """Minimal abstract-only prediction schema for benchmark-aligned runs."""

    main_reason: str

    @field_validator("main_reason")
    @classmethod
    def main_reason_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("main_reason must be non-empty")
        return value


class ScreeningPrediction(BaseScreeningPrediction):
    """Richer prediction schema emitted by full-text or legacy direct methods."""

    criterion_judgments: dict[str, CriterionJudgment] = Field(default_factory=dict)
    failed_criterion: str | None = None
    main_reason: str | None = None
    evidence_spans: list[EvidenceSpan] = Field(default_factory=list)

    @field_validator("evidence_spans", mode="before")
    @classmethod
    def coerce_top_level_evidence_spans(
        cls, value: list[EvidenceSpan | dict[str, Any] | str] | None
    ) -> list[EvidenceSpan | dict[str, Any]]:
        if value is None:
            return []
        normalized: list[EvidenceSpan | dict[str, Any]] = []
        for item in value:
            if isinstance(item, str):
                normalized.append({"text": item})
            else:
                normalized.append(item)
        return normalized

    @field_validator("failed_criterion", "main_reason")
    @classmethod
    def optional_prediction_strings_to_none(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            return None
        return value


class AggregationResult(BaseModel):
    """Local aggregation result for criterion-wise judgments."""

    model_config = ConfigDict(extra="forbid")

    final_decision: Decision
    aggregation_status: str
    failed_criterion: str | None = None
    main_reason: str
    evidence_spans: list[EvidenceSpan] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("aggregation_status", "main_reason")
    @classmethod
    def aggregation_strings_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("aggregation strings must be non-empty")
        return value

    @field_validator("failed_criterion")
    @classmethod
    def aggregation_failed_criterion_to_none(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            return None
        return value


class RunMetadata(BaseModel):
    """Metadata required to trace a run from inputs to outputs."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    method: str
    benchmark: str | None = None
    split: str | None = None
    input_setting: InputSetting | None = None
    provider: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)
    schema_version: str = "v0"
    config_path: Path | None = None
    provider_config_path: Path | None = None
    examples_path: Path | None = None
    prediction_path: Path | None = None
    metric_path: Path | None = None
    command: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    sample_count: int | None = Field(default=None, ge=0)
    success_count: int | None = Field(default=None, ge=0)
    error_count: int | None = Field(default=None, ge=0)
    is_real_llm_run: bool = False
    error_examples: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("run_id", "method")
    @classmethod
    def run_required_strings_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("run_id and method must be non-empty")
        return value

    @model_validator(mode="after")
    def validate_run_times(self) -> "RunMetadata":
        if self.started_at and self.ended_at and self.ended_at < self.started_at:
            raise ValueError("ended_at must be greater than or equal to started_at")
        return self
