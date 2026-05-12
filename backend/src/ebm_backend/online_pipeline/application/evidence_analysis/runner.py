"""End-to-end simplified Module 3 runner."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Any

from ebm_backend.shared.llm.gateway import LLMGateway
from ebm_backend.online_pipeline.application.evidence_analysis.aggregation import MetaAnalysisAggregator
from ebm_backend.online_pipeline.application.evidence_analysis.extraction import DataExtractor, EvidenceContextBuilder
from ebm_backend.online_pipeline.application.evidence_analysis.grade import GradeAssessor
from ebm_backend.online_pipeline.application.evidence_analysis.models import Module3AnalysisResult
from ebm_backend.online_pipeline.application.evidence_analysis.planning import AnalysisPlanner
from ebm_backend.online_pipeline.application.evidence_analysis.rob import RiskOfBiasAssessor
from ebm_backend.online_pipeline.application.evidence_analysis.screening import StudyScreener


class Module3AnalysisRunner:
    """Run screening -> planning -> extraction -> RoB -> aggregation -> GRADE."""

    def __init__(
        self,
        gateway: LLMGateway,
        *,
        screener: StudyScreener | None = None,
        planner: AnalysisPlanner | None = None,
        evidence_builder: EvidenceContextBuilder | None = None,
        extractor: DataExtractor | None = None,
        rob_assessor: RiskOfBiasAssessor | None = None,
        aggregator: MetaAnalysisAggregator | None = None,
        grade_assessor: GradeAssessor | None = None,
    ):
        self.gateway = gateway
        self.screener = screener or StudyScreener()
        self.planner = planner or AnalysisPlanner()
        self.evidence_builder = evidence_builder or EvidenceContextBuilder()
        self.extractor = extractor or DataExtractor()
        self.rob_assessor = rob_assessor or RiskOfBiasAssessor()
        self.aggregator = aggregator or MetaAnalysisAggregator()
        self.grade_assessor = grade_assessor or GradeAssessor()

    async def run(
        self,
        *,
        question: str,
        pico: Any,
        eligibility_criteria: Any,
        preliminary_plan: Any,
        candidates: list[Any],
        run_id: str | None = None,
    ) -> Module3AnalysisResult:
        screening = await self.screener.screen_with_llm(
            self.gateway,
            question=question,
            pico=pico,
            eligibility_criteria=eligibility_criteria,
            candidates=candidates,
            run_id=run_id,
        )
        planning = await self.planner.plan_with_llm(
            self.gateway,
            question=question,
            pico=pico,
            preliminary_plan=preliminary_plan,
            included_studies=screening.included,
            run_id=run_id,
        )
        evidence = {context.study_id: context for context in (self.evidence_builder.build(study) for study in screening.included)}
        extraction = await self.extractor.extract_with_llm(
            self.gateway,
            analyses=planning.analyses,
            evidence_contexts=evidence,
            run_id=run_id,
        )
        risk_of_bias = await self.rob_assessor.assess_with_llm(
            self.gateway,
            evidence_contexts=evidence,
            run_id=run_id,
        )
        aggregation = self.aggregator.aggregate(analyses=planning.analyses, rows=extraction.rows)
        grade = await self.grade_assessor.assess_with_llm(
            self.gateway,
            aggregation=aggregation,
            risk_of_bias=risk_of_bias,
            run_id=run_id,
        )
        warnings = [
            *screening.warnings,
            *planning.warnings,
            *extraction.warnings,
            *risk_of_bias.warnings,
            *aggregation.warnings,
            *grade.warnings,
        ]
        return Module3AnalysisResult(
            screening=screening,
            planning=planning,
            evidence=evidence,
            extraction=extraction,
            risk_of_bias=risk_of_bias,
            aggregation=aggregation,
            grade=grade,
            warnings=warnings,
        )

    def run_sync(
        self,
        *,
        question: str,
        pico: Any,
        eligibility_criteria: Any,
        preliminary_plan: Any,
        candidates: list[Any],
        run_id: str | None = None,
    ) -> Module3AnalysisResult:
        return asyncio.run(
            self.run(
                question=question,
                pico=pico,
                eligibility_criteria=eligibility_criteria,
                preliminary_plan=preliminary_plan,
                candidates=candidates,
                run_id=run_id,
            )
        )


def result_to_dict(result: Module3AnalysisResult) -> dict[str, Any]:
    return asdict(result)
