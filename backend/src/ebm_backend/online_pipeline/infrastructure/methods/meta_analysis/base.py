"""Abstract base classes for meta-analysis methods."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ebm_backend.online_pipeline.domain.article import CleanedArticle
from ebm_backend.online_pipeline.domain.meta_analysis import MetaAnalysisResultPackage
from ebm_backend.online_pipeline.domain.question import QuestionPICO
from ebm_backend.online_pipeline.domain.study_characteristics import StudyPIOCharacteristics


class MetaAnalysisMethod(ABC):
    """Workflow-level meta-analysis method interface."""

    @abstractmethod
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
        """Run the complete meta-analysis module."""


class StudyResultsMethod(ABC):
    subtask = "study_results"

    @abstractmethod
    def run(self, *, instance: dict[str, Any], articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract study-level result rows for one analysis setting."""


class AnalysisMethodsMethod(ABC):
    subtask = "analysis_methods"

    @abstractmethod
    def run(self, *, instance: dict[str, Any]) -> list[dict[str, Any]]:
        """Decide analysis methods for one analysis setting."""


class SubgroupAnalysisMethod(ABC):
    subtask = "subgroup_analysis"

    @abstractmethod
    def run(self, *, instances: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """Calculate subgroup estimates and subgroup difference tests."""


class OverallEstimatesMethod(ABC):
    subtask = "overall_estimates"

    @abstractmethod
    def run(self, *, instance: dict[str, Any]) -> list[dict[str, Any]]:
        """Calculate overall estimates for one analysis setting."""
