"""LLM-assisted Population/Intervention extraction for Module 2 questions."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass, field
from typing import Any

from ebm_backend.shared.llm.gateway import LLMGateway
from ebm_backend.online_pipeline.application.question_study.expansion import PICO, QuestionExpansionResult
from ebm_backend.online_pipeline.application.question_study.llm_io import load_prompt, load_schema


@dataclass(frozen=True)
class QuestionPI:
    population: list[str] = field(default_factory=list)
    intervention: list[str] = field(default_factory=list)
    notes: str = ""


class QuestionPIExtractor:
    """Extract retrieval-oriented P/I terms from question expansion output."""

    _PROMPT_NAME = "question_pi_extraction"

    def extract(self, expansion: QuestionExpansionResult) -> QuestionPI:
        """Deterministic fallback: reuse P/I terms from expanded PICO."""
        return QuestionPI(
            population=list(expansion.pico.population),
            intervention=list(expansion.pico.intervention),
            notes="Derived from expanded PICO without an additional LLM call.",
        )

    async def extract_with_llm(
        self,
        gateway: LLMGateway,
        expansion: QuestionExpansionResult,
        *,
        run_id: str | None = None,
        prompt_version: str = "v1",
    ) -> QuestionPI:
        prompt_template = load_prompt(self._PROMPT_NAME)
        response_schema: dict[str, Any] = load_schema(self._PROMPT_NAME)
        result = await gateway.call(
            task_type=self._PROMPT_NAME,
            inputs={
                "question": expansion.question,
                "expanded_question": expansion.expanded_question,
                "pico": asdict(expansion.pico),
            },
            prompt_template=prompt_template,
            prompt_vars={
                "question": expansion.question,
                "expanded_question": expansion.expanded_question,
                "pico_json": json.dumps(asdict(expansion.pico), ensure_ascii=False),
            },
            response_schema=response_schema,
            temperature=0.0,
            cacheable=False,
            run_id=run_id,
            module="module2",
            task_name="question_pi_extraction",
            study_id="question",
            prompt_version=prompt_version,
        )
        return QuestionPI(
            population=[str(term).strip() for term in result.content.get("population") or [] if str(term).strip()],
            intervention=[str(term).strip() for term in result.content.get("intervention") or [] if str(term).strip()],
            notes=str(result.content.get("notes") or ""),
        )

    def extract_with_llm_sync(
        self,
        gateway: LLMGateway,
        expansion: QuestionExpansionResult,
        *,
        run_id: str | None = None,
        prompt_version: str = "v1",
    ) -> QuestionPI:
        return asyncio.run(
            self.extract_with_llm(
                gateway,
                expansion,
                run_id=run_id,
                prompt_version=prompt_version,
            )
        )
