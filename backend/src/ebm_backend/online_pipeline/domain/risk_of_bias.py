"""Risk-of-bias domain objects."""

from __future__ import annotations

from dataclasses import dataclass, field

from ebm_backend.online_pipeline.domain.common import EvidenceSourceSpan


ROB1_DOMAINS = [
    "random_sequence_generation",
    "allocation_concealment",
    "blinding_participants_personnel",
    "blinding_outcome_assessment",
    "incomplete_outcome_data",
    "selective_reporting",
    "other_bias",
]


@dataclass(frozen=True)
class RoB1DomainJudgement:
    domain: str
    judgement: str
    rationale: str
    source_spans: list[EvidenceSourceSpan] = field(default_factory=list)


@dataclass(frozen=True)
class RiskOfBiasAssessment:
    study_id: str
    domains: list[RoB1DomainJudgement] = field(default_factory=list)
    overall: str = "unclear"
    notes: str = ""
