"""Application ports for online pipeline module execution."""

from __future__ import annotations

from typing import Protocol

from ebm_backend.online_pipeline.domain.article import CleanedArticle, SearchRetrievalResult
from ebm_backend.online_pipeline.domain.common import WorkflowConstraints
from ebm_backend.online_pipeline.domain.grade import GradeResult
from ebm_backend.online_pipeline.domain.meta_analysis import MetaAnalysisResultPackage
from ebm_backend.online_pipeline.domain.module_config import ModuleRunConfig
from ebm_backend.online_pipeline.domain.question import QuestionPICO
from ebm_backend.online_pipeline.domain.screening import StudyScreeningResult
from ebm_backend.online_pipeline.domain.screening import ScreeningCriteria
from ebm_backend.online_pipeline.domain.study_characteristics import StudyPIOCharacteristics
from ebm_backend.online_pipeline.domain.risk_of_bias import RiskOfBiasAssessment


class ModuleMethodResolverPort(Protocol):
    def resolve(self, *, module_name: str, method_name: str):
        ...


class Q2PICOPort(Protocol):
    def run(self, *, question_text: str) -> QuestionPICO:
        ...


class SearchRetrievalPort(Protocol):
    def run(self, *, question_pico: QuestionPICO, config: ModuleRunConfig) -> SearchRetrievalResult:
        ...


class StudyScreeningPort(Protocol):
    def run(
        self,
        *,
        question_text: str,
        question_pico: QuestionPICO,
        constraints: WorkflowConstraints,
        articles: list[CleanedArticle],
    ) -> StudyScreeningResult:
        ...


class StudyPIOExtractionPort(Protocol):
    def run(
        self,
        *,
        question_pico: QuestionPICO,
        included_studies: list[str],
        articles: list[CleanedArticle],
    ) -> list[StudyPIOCharacteristics]:
        ...


class RiskOfBiasPort(Protocol):
    def run(self, *, included_studies: list[str], articles: list[CleanedArticle]) -> list[RiskOfBiasAssessment]:
        ...


class MetaAnalysisPort(Protocol):
    def run(
        self,
        *,
        review_id: str,
        question_text: str,
        question_pico: QuestionPICO,
        included_studies: list[str],
        articles: list[CleanedArticle],
        study_characteristics: list[StudyPIOCharacteristics],
    ) -> MetaAnalysisResultPackage:
        ...


class GradeAssessmentPort(Protocol):
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
        ...
