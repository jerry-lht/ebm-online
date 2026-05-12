"""Analysis planning confirmation."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any

from ebm_backend.shared.llm.gateway import LLMGateway
from ebm_backend.online_pipeline.application.evidence_analysis.models import AnalysisSpec, PlanningResult
from ebm_backend.online_pipeline.application.question_study.llm_io import load_prompt, load_schema


class AnalysisPlanner:
    """Confirm analysis list from question context and screened studies."""

    _PROMPT_NAME = "analysis_planning"

    async def plan_with_llm(
        self,
        gateway: LLMGateway,
        *,
        question: str,
        pico: Any,
        preliminary_plan: Any,
        included_studies: list[Any],
        run_id: str | None = None,
        prompt_version: str = "v1",
    ) -> PlanningResult:
        prompt_template = load_prompt(self._PROMPT_NAME)
        response_schema = load_schema(self._PROMPT_NAME)
        included_payload = [_to_plain_dict(study) for study in included_studies]
        inputs = {
            "question": question,
            "pico": _to_plain_dict(pico),
            "preliminary_plan": _to_plain_dict(preliminary_plan),
            "included_studies": included_payload,
        }
        try:
            result = await gateway.call(
                task_type=self._PROMPT_NAME,
                inputs=inputs,
                prompt_template=prompt_template,
                prompt_vars={
                    "question": question,
                    "pico_json": json.dumps(inputs["pico"], ensure_ascii=False),
                    "preliminary_plan_json": json.dumps(inputs["preliminary_plan"], ensure_ascii=False),
                    "included_studies_json": json.dumps(included_payload, ensure_ascii=False),
                },
                response_schema=response_schema,
                temperature=0.0,
                cacheable=False,
                run_id=run_id,
                module="module3",
                task_name="analysis_planning",
                study_id="analysis_plan",
                prompt_version=prompt_version,
            )
            analyses = [self._analysis_from_payload(raw, idx) for idx, raw in enumerate(result.content.get("analyses") or [])]
            if analyses:
                return PlanningResult(analyses=analyses, warnings=list(result.content.get("warnings") or []))
            raise ValueError("LLM returned no analyses")
        except Exception as exc:
            fallback = self._fallback_analyses(pico, preliminary_plan)
            return PlanningResult(
                analyses=fallback,
                warnings=[f"Analysis planning failed; used fallback plan: {exc}"],
            )

    def _analysis_from_payload(self, raw: dict[str, Any], idx: int) -> AnalysisSpec:
        return AnalysisSpec(
            analysis_id=str(raw.get("analysis_id") or f"a{idx + 1}"),
            outcome=str(raw.get("outcome") or f"Outcome {idx + 1}"),
            outcome_type=_normalize_outcome_type(raw.get("outcome_type")),
            effect_measure=_normalize_effect_measure(raw.get("effect_measure"), raw.get("outcome_type")),
            intervention=str(raw.get("intervention") or ""),
            comparator=str(raw.get("comparator") or ""),
            timepoint=raw.get("timepoint"),
            pooling_method=str(raw.get("pooling_method") or "IV"),
            model=str(raw.get("model") or "fixed"),
            notes=str(raw.get("notes") or ""),
        )

    def _fallback_analyses(self, pico: Any, preliminary_plan: Any) -> list[AnalysisSpec]:
        plan = _to_plain_dict(preliminary_plan) or {}
        pico_payload = _to_plain_dict(pico) or {}
        outcomes = []
        primary = plan.get("primary_outcome")
        if primary:
            outcomes.append(str(primary))
        outcomes.extend(str(item) for item in plan.get("secondary_outcomes") or [] if str(item).strip())
        if not outcomes:
            outcomes = [str(item) for item in pico_payload.get("outcome") or [] if str(item).strip()]
        if not outcomes:
            outcomes = ["Primary outcome"]
        effect_measures = plan.get("effect_measures") or {}
        intervention = ", ".join(pico_payload.get("intervention") or [])
        comparator = ", ".join(pico_payload.get("comparison") or [])
        analyses: list[AnalysisSpec] = []
        for idx, outcome in enumerate(outcomes, start=1):
            effect_measure = effect_measures.get("binary") or effect_measures.get("continuous") or "RR"
            outcome_type = "binary" if str(effect_measure).upper() in {"RR", "OR"} else "continuous"
            analyses.append(
                AnalysisSpec(
                    analysis_id=f"a{idx}",
                    outcome=outcome,
                    outcome_type=outcome_type,
                    effect_measure=_normalize_effect_measure(effect_measure, outcome_type),
                    intervention=intervention,
                    comparator=comparator,
                    notes="Fallback analysis generated from PICO/preliminary plan.",
                )
            )
        return analyses


def _to_plain_dict(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return [_to_plain_dict(item) for item in value]
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return value


def _normalize_outcome_type(value: Any) -> str:
    text = str(value or "").lower()
    if text in {"continuous", "binary"}:
        return text
    return "binary" if text in {"dichotomous", "event"} else "continuous"


def _normalize_effect_measure(value: Any, outcome_type: Any = None) -> str:
    text = str(value or "").upper()
    if "SMD" in text:
        return "SMD"
    if "MD" in text:
        return "MD"
    if "OR" in text:
        return "OR"
    if "HR" in text:
        return "HR"
    if "GIV" in text or "INVERSE" in text:
        return "GIV"
    if "RR" in text or _normalize_outcome_type(outcome_type) == "binary":
        return "RR"
    return "MD"
