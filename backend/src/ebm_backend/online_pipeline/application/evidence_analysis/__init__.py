"""Module 3: EBM Annotation and Analysis."""

from .aggregation import MetaAnalysisAggregator
from .extraction import DataExtractor, EvidenceContextBuilder
from .grade import GradeAssessor
from .models import (
    AggregationResult,
    AnalysisAggregation,
    AnalysisSpec,
    EvidenceContext,
    ExtractedDataRow,
    ExtractionResult,
    GradeAssessment,
    GradeResult,
    Module3AnalysisResult,
    PlanningResult,
    RiskOfBiasAssessment,
    RiskOfBiasResult,
    RoBDomainJudgement,
    ScreeningDecision,
    ScreeningResult,
    StudyAggregation,
)
from .planning import AnalysisPlanner
from .rob import RiskOfBiasAssessor
from .runner import Module3AnalysisRunner, result_to_dict
from .screening import StudyScreener

__all__ = [
    "AggregationResult",
    "AnalysisAggregation",
    "AnalysisPlanner",
    "AnalysisSpec",
    "DataExtractor",
    "EvidenceContext",
    "EvidenceContextBuilder",
    "ExtractedDataRow",
    "ExtractionResult",
    "GradeAssessment",
    "GradeAssessor",
    "GradeResult",
    "MetaAnalysisAggregator",
    "Module3AnalysisResult",
    "Module3AnalysisRunner",
    "PlanningResult",
    "RiskOfBiasAssessment",
    "RiskOfBiasAssessor",
    "RiskOfBiasResult",
    "RoBDomainJudgement",
    "ScreeningDecision",
    "ScreeningResult",
    "StudyAggregation",
    "StudyScreener",
    "result_to_dict",
]
