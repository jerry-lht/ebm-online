"""Risk of Bias assessment (RoB 1 tool)."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict
from typing import Any

from ebm_backend.shared.llm.gateway import LLMGateway
from ebm_backend.online_pipeline.application.evidence_analysis.models import EvidenceContext, RiskOfBiasAssessment, RiskOfBiasResult, RoBDomainJudgement
from ebm_backend.online_pipeline.application.question_study.llm_io import load_prompt, load_schema


SELECTIVE_REPORTING_DOMAIN = "selective_reporting"


class RiskOfBiasAssessor:
    """Assess RoB 1 domains available from the article text."""

    _PROMPT_NAME = "risk_of_bias"
    _DEFAULT_CONCURRENCY = 8

    async def assess_with_llm(
        self,
        gateway: LLMGateway,
        *,
        evidence_contexts: dict[str, EvidenceContext],
        concurrency: int | None = None,
        run_id: str | None = None,
        prompt_version: str = "v1",
    ) -> RiskOfBiasResult:
        prompt_template = load_prompt(self._PROMPT_NAME)
        response_schema = load_schema(self._PROMPT_NAME)
        semaphore = asyncio.Semaphore(_resolve_concurrency(concurrency, "MODULE3_ROB_CONCURRENCY", self._DEFAULT_CONCURRENCY))
        contexts = list(evidence_contexts.values())
        ordered_assessments: list[RiskOfBiasAssessment | None] = [None] * len(contexts)
        warnings: list[str] = []
        async def _assess_one(index: int, context: EvidenceContext) -> None:
            async with semaphore:
                try:
                    result = await gateway.call(
                        task_type=self._PROMPT_NAME,
                        inputs={"evidence_context": asdict(context)},
                        prompt_template=prompt_template,
                        prompt_vars={"evidence_json": json.dumps(asdict(context), ensure_ascii=False)},
                        response_schema=response_schema,
                        temperature=0.0,
                        cacheable=False,
                        run_id=run_id,
                        module="module3",
                        task_name="risk_of_bias",
                        study_id=context.study_id,
                        prompt_version=prompt_version,
                    )
                    ordered_assessments[index] = self._assessment_from_payload(context.study_id, result.content)
                except Exception as exc:
                    warning = f"Risk of bias failed for {context.study_id}: {exc}"
                    warnings.append(warning)
                    ordered_assessments[index] = RiskOfBiasAssessment(
                        study_id=context.study_id,
                        domains=[_selective_reporting_domain()],
                        overall="unclear",
                        warnings=[warning],
                    )

        await asyncio.gather(*(_assess_one(index, context) for index, context in enumerate(contexts)))
        assessments = [item for item in ordered_assessments if item is not None]
        return RiskOfBiasResult(assessments=assessments, warnings=warnings)

    def _assessment_from_payload(self, study_id: str, content: dict[str, Any]) -> RiskOfBiasAssessment:
        domains = [
            RoBDomainJudgement(
                domain=str(raw.get("domain") or ""),
                judgement=_normalize_judgement(raw.get("judgement")),
                rationale=str(raw.get("rationale") or ""),
                evidence=str(raw.get("evidence") or ""),
            )
            for raw in content.get("domains") or []
            if isinstance(raw, dict) and str(raw.get("domain") or "").strip()
        ]
        domains = [domain for domain in domains if domain.domain != SELECTIVE_REPORTING_DOMAIN]
        domains.append(_selective_reporting_domain())
        return RiskOfBiasAssessment(
            study_id=str(content.get("study_id") or study_id),
            domains=domains,
            overall=_normalize_judgement(content.get("overall")),
            warnings=list(content.get("warnings") or []),
        )


def _selective_reporting_domain() -> RoBDomainJudgement:
    return RoBDomainJudgement(
        domain=SELECTIVE_REPORTING_DOMAIN,
        judgement="unable_to_determine",
        rationale="Selective reporting requires protocol or registry comparison and is fixed as unable_to_determine in this MVP.",
        evidence="",
    )


def _normalize_judgement(value: Any) -> str:
    text = str(value or "").lower().strip().replace(" ", "_")
    allowed = {"low", "high", "unclear", "unable_to_determine"}
    return text if text in allowed else "unclear"


def _resolve_concurrency(value: int | None, env_name: str, default: int) -> int:
    if isinstance(value, int) and value > 0:
        return value
    raw = os.getenv(env_name, str(default)).strip()
    try:
        parsed = int(raw)
        return parsed if parsed > 0 else default
    except ValueError:
        return default
