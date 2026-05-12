"""Question expansion to PICO + eligibility criteria."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from ebm_backend.shared.llm.gateway import LLMGateway
from ebm_backend.online_pipeline.application.question_study.llm_io import load_prompt, load_schema


@dataclass(frozen=True)
class PICO:
    """Structured clinical question components."""

    population: list[str] = field(default_factory=list)
    intervention: list[str] = field(default_factory=list)
    comparison: list[str] = field(default_factory=list)
    outcome: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EligibilityCriteria:
    """Simplified eligibility criteria from question expansion."""

    inclusion: list[str] = field(default_factory=list)
    exclusion: list[str] = field(default_factory=list)
    confidence: str = "medium"


@dataclass(frozen=True)
class PreliminaryAnalysisPlan:
    """Initial analysis hints used by downstream analysis module."""

    primary_outcome: str | None = None
    secondary_outcomes: list[str] = field(default_factory=list)
    timepoints: list[str] = field(default_factory=list)
    effect_measures: dict[str, str] = field(default_factory=dict)
    subgroups_of_interest: list[str] = field(default_factory=list)
    confidence: str = "low"


@dataclass(frozen=True)
class QuestionExpansionResult:
    """Output payload of simplified question expansion step."""

    question: str
    pico: PICO
    eligibility_criteria: EligibilityCriteria
    preliminary_analysis_plan: PreliminaryAnalysisPlan
    expanded_question: str
    needs_user_confirmation: list[str] = field(default_factory=list)
    is_medical_question: bool = True


class QuestionExpander:
    """Deterministic, mock-friendly question expander for Module 2 MVP."""

    _PROMPT_NAME = "question_expansion"

    def expand(self, question: str, *, pico: PICO | None = None) -> QuestionExpansionResult:
        resolved = pico or self._fallback_pico(question)
        return QuestionExpansionResult(
            question=question,
            pico=resolved,
            eligibility_criteria=EligibilityCriteria(
                inclusion=[],
                exclusion=[],
                confidence="low",
            ),
            preliminary_analysis_plan=PreliminaryAnalysisPlan(
                confidence="low",
            ),
            expanded_question=question.strip(),
            needs_user_confirmation=[
                "eligibility_criteria",
                "preliminary_analysis_plan",
            ],
            is_medical_question=bool(question.strip()),
        )

    def from_pico(self, question: str, pico: PICO) -> QuestionExpansionResult:
        """Build expansion result directly from externally provided PICO."""
        return self.expand(question, pico=pico)

    async def expand_with_llm(
        self,
        gateway: LLMGateway,
        question: str,
        *,
        run_id: str | None = None,
        prompt_version: str = "v1",
    ) -> QuestionExpansionResult:
        """Expand a clinical question via LLM structured output (Responses API)."""
        prompt_template = load_prompt(self._PROMPT_NAME)
        response_schema: dict[str, Any] = load_schema(self._PROMPT_NAME)
        result = await gateway.call(
            task_type=self._PROMPT_NAME,
            inputs={"question": question},
            prompt_template=prompt_template,
            prompt_vars={"question": question.strip()},
            response_schema=response_schema,
            temperature=0.0,
            cacheable=False,
            run_id=run_id,
            module="module2",
            task_name="question_expansion",
            study_id="question",
            prompt_version=prompt_version,
        )
        return self._result_from_llm_payload(question, result.content)

    def expand_with_llm_sync(
        self,
        gateway: LLMGateway,
        question: str,
        *,
        run_id: str | None = None,
        prompt_version: str = "v1",
    ) -> QuestionExpansionResult:
        return asyncio.run(self.expand_with_llm(gateway, question, run_id=run_id, prompt_version=prompt_version))

    @staticmethod
    def _result_from_llm_payload(question: str, content: dict[str, Any]) -> QuestionExpansionResult:
        pico_raw = content.get("pico") or {}
        plan_raw = content.get("preliminary_analysis_plan") or {}
        elig_raw = content.get("eligibility_criteria") or {}
        effect = plan_raw.get("effect_measures") or {}
        return QuestionExpansionResult(
            question=question,
            pico=PICO(
                population=list(pico_raw.get("population") or []),
                intervention=list(pico_raw.get("intervention") or []),
                comparison=list(pico_raw.get("comparison") or []),
                outcome=list(pico_raw.get("outcome") or []),
            ),
            eligibility_criteria=EligibilityCriteria(
                inclusion=list(elig_raw.get("inclusion") or []),
                exclusion=list(elig_raw.get("exclusion") or []),
                confidence=str(elig_raw.get("confidence") or "medium"),
            ),
            preliminary_analysis_plan=PreliminaryAnalysisPlan(
                primary_outcome=plan_raw.get("primary_outcome"),
                secondary_outcomes=list(plan_raw.get("secondary_outcomes") or []),
                timepoints=list(plan_raw.get("timepoints") or []),
                effect_measures={k: str(v) for k, v in effect.items() if isinstance(v, str)},
                subgroups_of_interest=list(plan_raw.get("subgroups_of_interest") or []),
                confidence=str(plan_raw.get("confidence") or "low"),
            ),
            expanded_question=str(content.get("expanded_question") or "").strip() or question.strip(),
            needs_user_confirmation=list(content.get("needs_user_confirmation") or []),
            is_medical_question=bool(content.get("is_medical_question", True)),
        )

    @staticmethod
    def _fallback_pico(question: str) -> PICO:
        text = question.strip()
        if not text:
            return PICO()
        return PICO(population=[text], intervention=[text])
