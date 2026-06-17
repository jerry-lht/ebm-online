"""Abstract base classes for GRADE methods."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ebm_backend.online_pipeline.domain.grade import GradeResult
from ebm_backend.online_pipeline.domain.meta_analysis import MetaAnalysisResultPackage
from ebm_backend.online_pipeline.domain.question import QuestionPICO
from ebm_backend.online_pipeline.domain.risk_of_bias import RiskOfBiasAssessment
from ebm_backend.online_pipeline.domain.screening import ScreeningCriteria
from ebm_backend.online_pipeline.domain.study_characteristics import StudyPIOCharacteristics


class GradeAssessmentMethod(ABC):
    """Workflow-level GRADE method interface."""

    @abstractmethod
    def run(
        self,
        *,
        review_id: str,
        question_text: str,
        question_pico: QuestionPICO,
        screening_criteria: ScreeningCriteria,
        study_characteristics: list[StudyPIOCharacteristics],
        risk_of_bias: list[RiskOfBiasAssessment],
        meta_analysis_result: MetaAnalysisResultPackage,
    ) -> GradeResult:
        """Run GRADE assessment for a complete workflow result."""


class GradeDomainMethod(ABC):
    """Single-domain GRADE method interface."""

    domain: str

    @abstractmethod
    def run(self, *, domain_evidence: dict[str, Any], evidence_body: dict[str, Any]) -> dict[str, Any]:
        """Return one GRADE domain judgement."""
