"""Application-layer entry point for running online pipeline modules."""

from __future__ import annotations

from dataclasses import dataclass

from ebm_backend.online_pipeline.application.ports import ModuleMethodResolverPort
from ebm_backend.online_pipeline.domain.article import CleanedArticle, SearchRetrievalResult
from ebm_backend.online_pipeline.domain.common import WorkflowConstraints
from ebm_backend.online_pipeline.domain.grade import GradeResult
from ebm_backend.online_pipeline.domain.meta_analysis import MetaAnalysisResultPackage
from ebm_backend.online_pipeline.domain.module_config import ModuleRunConfig
from ebm_backend.online_pipeline.domain.question import QuestionPICO
from ebm_backend.online_pipeline.domain.risk_of_bias import RiskOfBiasAssessment
from ebm_backend.online_pipeline.domain.screening import ScreeningCriteria, StudyScreeningResult
from ebm_backend.online_pipeline.domain.study_characteristics import StudyPIOCharacteristics


@dataclass(frozen=True)
class ModuleRunner:
    resolver: ModuleMethodResolverPort

    def run_q2pico(self, *, method_name: str, question_text: str) -> QuestionPICO:
        method = self._resolve_method(module_name="q2pico", method_name=method_name)
        return method.run(question_text=question_text)

    def run_search_retrieval(
        self,
        *,
        method_name: str,
        question_pico: QuestionPICO,
        config: ModuleRunConfig,
    ) -> SearchRetrievalResult:
        method = self._resolve_method(module_name="search_retrieval", method_name=method_name)
        return method.run(question_pico=question_pico, config=config)

    def run_study_screening(
        self,
        *,
        method_name: str,
        question_text: str,
        question_pico: QuestionPICO,
        constraints: WorkflowConstraints,
        articles: list[CleanedArticle],
    ) -> StudyScreeningResult:
        method = self._resolve_method(module_name="study_screening", method_name=method_name)
        return method.run(
            question_text=question_text,
            question_pico=question_pico,
            constraints=constraints,
            articles=articles,
        )

    def run_study_pio_extraction(
        self,
        *,
        method_name: str,
        question_pico: QuestionPICO,
        included_studies: list[str],
        articles: list[CleanedArticle],
    ) -> list[StudyPIOCharacteristics]:
        method = self._resolve_method(module_name="study_pio", method_name=method_name)
        return method.run(
            question_pico=question_pico,
            included_studies=included_studies,
            articles=articles,
        )

    def run_risk_of_bias(
        self,
        *,
        method_name: str,
        included_studies: list[str],
        articles: list[CleanedArticle],
    ) -> list[RiskOfBiasAssessment]:
        method = self._resolve_method(module_name="risk_of_bias", method_name=method_name)
        return method.run(included_studies=included_studies, articles=articles)

    def run_meta_analysis(
        self,
        *,
        method_name: str,
        review_id: str,
        question_text: str,
        question_pico: QuestionPICO,
        included_studies: list[str],
        articles: list[CleanedArticle],
        study_characteristics: list[StudyPIOCharacteristics],
    ) -> MetaAnalysisResultPackage:
        method = self._resolve_method(module_name="meta_analysis", method_name=method_name)
        return method.run(
            review_id=review_id,
            question_text=question_text,
            question_pico=question_pico,
            included_studies=included_studies,
            articles=articles,
            study_characteristics=study_characteristics,
        )

    def run_grade_assessment(
        self,
        *,
        method_name: str,
        review_id: str,
        question_text: str,
        question_pico: QuestionPICO,
        screening_criteria: ScreeningCriteria,
        study_characteristics: list[StudyPIOCharacteristics],
        risk_of_bias: list[RiskOfBiasAssessment],
        meta_analysis_result: MetaAnalysisResultPackage,
    ) -> GradeResult:
        method = self._resolve_method(module_name="grade", method_name=method_name)
        return method.run(
            review_id=review_id,
            question_text=question_text,
            question_pico=question_pico,
            screening_criteria=screening_criteria,
            study_characteristics=study_characteristics,
            risk_of_bias=risk_of_bias,
            meta_analysis_result=meta_analysis_result,
        )

    def _resolve_method(self, *, module_name: str, method_name: str):
        return self.resolver.resolve(module_name=module_name, method_name=method_name)
