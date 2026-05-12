"""GRADE certainty of evidence assessment."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from ebm_backend.shared.llm.gateway import LLMGateway
from ebm_backend.online_pipeline.application.evidence_analysis.models import AggregationResult, GradeAssessment, GradeResult, RiskOfBiasResult
from ebm_backend.online_pipeline.application.question_study.llm_io import load_prompt, load_schema


class GradeAssessor:
    """Assess certainty per analysis using aggregation and RoB outputs."""

    _PROMPT_NAME = "grade_assessment"

    async def assess_with_llm(
        self,
        gateway: LLMGateway,
        *,
        aggregation: AggregationResult,
        risk_of_bias: RiskOfBiasResult,
        run_id: str | None = None,
        prompt_version: str = "v1",
    ) -> GradeResult:
        prompt_template = load_prompt(self._PROMPT_NAME)
        response_schema = load_schema(self._PROMPT_NAME)
        assessments: list[GradeAssessment] = []
        warnings: list[str] = []
        rob_payload = asdict(risk_of_bias)
        for analysis in aggregation.analyses:
            try:
                result = await gateway.call(
                    task_type=self._PROMPT_NAME,
                    inputs={"aggregation": asdict(analysis), "risk_of_bias": rob_payload},
                    prompt_template=prompt_template,
                    prompt_vars={
                        "aggregation_json": json.dumps(asdict(analysis), ensure_ascii=False),
                        "risk_of_bias_json": json.dumps(rob_payload, ensure_ascii=False),
                    },
                    response_schema=response_schema,
                    temperature=0.0,
                    cacheable=False,
                    run_id=run_id,
                    module="module3",
                    task_name="grade_assessment",
                    study_id=analysis.analysis_id,
                    prompt_version=prompt_version,
                )
                assessments.append(self._assessment_from_payload(analysis.analysis_id, result.content))
            except Exception as exc:
                warning = f"GRADE assessment failed for {analysis.analysis_id}: {exc}"
                warnings.append(warning)
                assessments.append(
                    GradeAssessment(
                        analysis_id=analysis.analysis_id,
                        certainty="very_low",
                        downgrade_reasons=["Unable to complete structured GRADE assessment."],
                        rationale=warning,
                        warnings=[warning],
                    )
                )
        return GradeResult(assessments=assessments, warnings=warnings)

    def _assessment_from_payload(self, analysis_id: str, content: dict[str, Any]) -> GradeAssessment:
        return GradeAssessment(
            analysis_id=str(content.get("analysis_id") or analysis_id),
            certainty=_normalize_certainty(content.get("certainty")),
            downgrade_reasons=[str(item) for item in content.get("downgrade_reasons") or [] if str(item).strip()],
            rationale=str(content.get("rationale") or ""),
            warnings=list(content.get("warnings") or []),
        )


def _normalize_certainty(value: Any) -> str:
    text = str(value or "").lower().strip().replace(" ", "_")
    allowed = {"high", "moderate", "low", "very_low"}
    return text if text in allowed else "very_low"
