"""GRADE assessment domain contracts."""

from __future__ import annotations

from dataclasses import dataclass, field

from ebm_backend.online_pipeline.domain.common import EvidenceSourceSpan, GradeDomainName
from ebm_backend.online_pipeline.domain.meta_analysis import (
    AnalysisComparison,
    AnalysisOutcome,
    AnalysisSubgroup,
    AnalysisTimepoint,
)


@dataclass(frozen=True)
class EffectEstimateRef:
    estimate_type: str
    estimate_id: str | None = None
    estimation_status: str | None = None


@dataclass(frozen=True)
class GRADEDomainJudgement:
    domain: GradeDomainName
    downgraded: str
    severity: str
    levels: int | str
    level_evaluable: bool
    rationale: str
    source_spans: list[EvidenceSourceSpan] = field(default_factory=list)


@dataclass(frozen=True)
class DomainJudgements:
    risk_of_bias: GRADEDomainJudgement
    inconsistency: GRADEDomainJudgement
    indirectness: GRADEDomainJudgement
    imprecision: GRADEDomainJudgement


@dataclass(frozen=True)
class SoFRowGRADEAssessment:
    sof_row_id: str
    row_label: str | None
    setting_id: str
    setting_family_id: str
    candidate_id: str
    comparison: AnalysisComparison
    outcome: AnalysisOutcome
    timepoint: AnalysisTimepoint
    subgroup: AnalysisSubgroup
    effect_estimate_ref: EffectEstimateRef
    included_study_ids: list[str]
    domain_judgements: DomainJudgements


@dataclass(frozen=True)
class GradeResult:
    review_id: str
    question_text: str
    sof_rows: list[SoFRowGRADEAssessment] = field(default_factory=list)
