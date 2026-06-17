"""Study screening domain objects."""

from __future__ import annotations

from dataclasses import dataclass, field

from ebm_backend.online_pipeline.domain.common import EvidenceSourceSpan


@dataclass(frozen=True)
class ScreeningCriteria:
    inclusion_criteria: list[str] = field(default_factory=list)
    exclusion_criteria: list[str] = field(default_factory=list)
    rationale: str = ""


@dataclass(frozen=True)
class ScreeningDecision:
    study_id: str
    decision: str
    rationale: str
    exclusion_reason: str | None = None
    source_spans: list[EvidenceSourceSpan] = field(default_factory=list)


@dataclass(frozen=True)
class StudyScreeningResult:
    screening_criteria: ScreeningCriteria
    decisions: list[ScreeningDecision] = field(default_factory=list)
    included_studies: list[str] = field(default_factory=list)
