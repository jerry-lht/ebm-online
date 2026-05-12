"""Data contracts for the simplified Module 3 analysis pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ScreeningDecision:
    study_id: str
    title: str
    included: bool
    rationale: str
    exclusion_reason: str | None = None
    warning: str | None = None


@dataclass(frozen=True)
class ScreeningResult:
    included: list[Any] = field(default_factory=list)
    excluded: list[ScreeningDecision] = field(default_factory=list)
    decisions: list[ScreeningDecision] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AnalysisSpec:
    analysis_id: str
    outcome: str
    outcome_type: str
    effect_measure: str
    intervention: str = ""
    comparator: str = ""
    timepoint: str | None = None
    pooling_method: str = "IV"
    model: str = "fixed"
    notes: str = ""


@dataclass(frozen=True)
class PlanningResult:
    analyses: list[AnalysisSpec] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EvidenceContext:
    study_id: str
    title: str
    abstract: str
    methods: str = ""
    results: str = ""
    tables: list[dict[str, str]] = field(default_factory=list)
    source_path: str | None = None
    full_text_available: bool = False


@dataclass(frozen=True)
class ExtractedDataRow:
    study_id: str
    analysis_id: str
    outcome_type: str
    effect_measure: str
    extraction_status: str = "included"
    missing_reason: str | None = None
    exp_mean: float | None = None
    exp_sd: float | None = None
    exp_n: int | None = None
    ctrl_mean: float | None = None
    ctrl_sd: float | None = None
    ctrl_n: int | None = None
    exp_events: int | None = None
    ctrl_events: int | None = None
    giv_effect: float | None = None
    giv_se: float | None = None
    evidence_spans: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class ExtractionResult:
    rows: list[ExtractedDataRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RoBDomainJudgement:
    domain: str
    judgement: str
    rationale: str
    evidence: str = ""


@dataclass(frozen=True)
class RiskOfBiasAssessment:
    study_id: str
    domains: list[RoBDomainJudgement] = field(default_factory=list)
    overall: str = "unclear"
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RiskOfBiasResult:
    assessments: list[RiskOfBiasAssessment] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StudyAggregation:
    study_id: str
    analysis_id: str
    included: bool
    effect: float | None = None
    se: float | None = None
    variance: float | None = None
    weight: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    excluded_reason: str | None = None


@dataclass(frozen=True)
class AnalysisAggregation:
    analysis_id: str
    outcome: str
    effect_measure: str
    study_effects: list[StudyAggregation] = field(default_factory=list)
    pooled_result: dict[str, Any] | None = None
    heterogeneity: dict[str, Any] | None = None
    excluded_rows: list[ExtractedDataRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AggregationResult:
    analyses: list[AnalysisAggregation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GradeAssessment:
    analysis_id: str
    certainty: str
    downgrade_reasons: list[str] = field(default_factory=list)
    rationale: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GradeResult:
    assessments: list[GradeAssessment] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Module3AnalysisResult:
    screening: ScreeningResult
    planning: PlanningResult
    evidence: dict[str, EvidenceContext]
    extraction: ExtractionResult
    risk_of_bias: RiskOfBiasResult
    aggregation: AggregationResult
    grade: GradeResult
    warnings: list[str] = field(default_factory=list)
