from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class Judgement(str, Enum):
    LOW = "Low risk"
    HIGH = "High risk"
    UNCLEAR = "Unclear risk"


class RoBDomain(str, Enum):
    RANDOM_SEQUENCE_GENERATION = "Random sequence generation"
    ALLOCATION_CONCEALMENT = "Allocation concealment"
    BLINDING_PARTICIPANTS_PERSONNEL = "Blinding of participants and personnel: All outcomes"
    BLINDING_OUTCOME_ASSESSORS = "Blinding of outcome assessment: All outcomes"
    INCOMPLETE_OUTCOME_DATA = "Incomplete outcome data: All outcomes"


class MethodologyExtraction(BaseModel):
    """Stage 1: Extracted methodological information from the article."""

    randomization_method: str = Field(
        ...,
        description="How was the random sequence generated? Quote or describe the method.",
    )
    allocation_concealment_method: str = Field(
        ...,
        description="How was allocation concealed from recruiters? Quote or describe.",
    )
    blinding_participants: str = Field(
        ...,
        description="Were participants blinded? How? Quote relevant details.",
    )
    blinding_personnel: str = Field(
        ...,
        description="Were personnel (intervention deliverers) blinded? How?",
    )
    blinding_outcome_assessors: str = Field(
        ...,
        description="Were outcome assessors blinded? How? Quote relevant details.",
    )
    attrition_details: str = Field(
        ...,
        description="Missing data: how many lost to follow-up per group? Reasons? How handled in analysis?",
    )
    study_design: Optional[str] = Field(
        default=None,
        description="Overall study design (RCT, cluster-RCT, etc.)",
    )
    additional_notes: Optional[str] = Field(
        default=None,
        description="Any other methodological details relevant to bias assessment.",
    )


class SupportContext(BaseModel):
    """Source context used to support one domain judgement."""

    source: str = Field(
        ...,
        description="Where this evidence came from: article, review_context, methodology, evidence_table, or not_reported.",
    )
    quote: str = Field(
        ...,
        description="Verbatim quote or concise context snippet supporting the judgement.",
    )
    relevance: str = Field(
        ...,
        description="Why this context matters for the judgement.",
    )


class DomainResult(BaseModel):
    domain: RoBDomain
    judgement: Judgement
    support_text: str = Field(
        ...,
        description="Quotes or concrete evidence from the article that back the judgement.",
    )
    support_context: List[SupportContext] = Field(
        default_factory=list,
        description="Structured context snippets used to support the judgement.",
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Short rationale explaining how the evidence maps to the judgement.",
    )
    evidence_map: Optional[dict[str, Any]] = Field(
        default=None,
        description="Structured audit fields extracted before the judgement, when available.",
    )


class DomainEvidence(BaseModel):
    """Stage 1 evidence table row for one RoB domain."""

    domain: RoBDomain
    reported_evidence: str = Field(
        ...,
        description="Verbatim article or review-context evidence relevant to this domain.",
    )
    missing_information: str = Field(
        ...,
        description="Important details that are not reported or remain ambiguous.",
    )
    low_risk_signals: str = Field(
        ...,
        description="Evidence that would support a Low risk judgement.",
    )
    high_risk_signals: str = Field(
        ...,
        description="Evidence that would support a High risk judgement.",
    )
    outcome_type: Optional[str] = Field(
        default=None,
        description="For blinding/attrition, whether outcomes are objective, subjective, self-reported, clinician-rated, etc.",
    )
    attrition_by_arm: Optional[str] = Field(
        default=None,
        description="For incomplete outcome data, missing outcome data by arm, reasons, and handling.",
    )
    external_evidence_needed: Optional[str] = Field(
        default=None,
        description="Whether the article lacks details that may require protocol, registry, review notes, or author correspondence.",
    )


class EvidenceTable(BaseModel):
    """Structured evidence extracted before domain judgement."""

    study_design: Optional[str] = None
    notes: Optional[str] = None
    results: List[DomainEvidence]


class RiskOfBiasAssessment(BaseModel):
    study_id: Optional[str] = None
    pmid: Optional[str] = None
    results: List[DomainResult]

    def to_cochrane_format(self) -> List[dict]:
        """Serialize to the same shape used in the ground-truth dataset."""
        return [
            {
                "domain": r.domain.value,
                "judgement": r.judgement.value,
                "support_text": r.support_text,
                "support_context": [item.model_dump() for item in r.support_context],
                "evidence_map": r.evidence_map,
                "source": "llm_assessment",
            }
            for r in self.results
        ]
