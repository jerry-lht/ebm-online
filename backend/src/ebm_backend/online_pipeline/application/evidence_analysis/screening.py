"""Study screening (include/exclude decision)."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict, is_dataclass
from typing import Any

from ebm_backend.shared.llm.gateway import LLMGateway
from ebm_backend.online_pipeline.application.evidence_analysis.models import ScreeningDecision, ScreeningResult
from ebm_backend.online_pipeline.application.question_study.llm_io import load_prompt, load_schema


class StudyScreener:
    """Screen candidate studies with one structured LLM call per study."""

    _PROMPT_NAME = "study_screening"
    _DEFAULT_CONCURRENCY = 8

    async def screen_with_llm(
        self,
        gateway: LLMGateway,
        *,
        question: str,
        pico: Any,
        eligibility_criteria: Any,
        candidates: list[Any],
        concurrency: int | None = None,
        run_id: str | None = None,
        prompt_version: str = "v1",
    ) -> ScreeningResult:
        prompt_template = load_prompt(self._PROMPT_NAME)
        response_schema = load_schema(self._PROMPT_NAME)
        semaphore = asyncio.Semaphore(_resolve_concurrency(concurrency, "MODULE3_SCREENING_CONCURRENCY", self._DEFAULT_CONCURRENCY))
        ordered_results: list[tuple[ScreeningDecision, Any, str | None]] = [None] * len(candidates)  # type: ignore[list-item]

        async def _screen_one(index: int, candidate: Any) -> None:
            candidate_payload = _to_plain_dict(candidate)
            study_id = _study_id(candidate)
            async with semaphore:
                try:
                    result = await gateway.call(
                        task_type=self._PROMPT_NAME,
                        inputs={
                            "question": question,
                            "pico": _to_plain_dict(pico),
                            "eligibility_criteria": _to_plain_dict(eligibility_criteria),
                            "candidate": candidate_payload,
                        },
                        prompt_template=prompt_template,
                        prompt_vars={
                            "question": question,
                            "pico_json": json.dumps(_to_plain_dict(pico), ensure_ascii=False),
                            "eligibility_json": json.dumps(_to_plain_dict(eligibility_criteria), ensure_ascii=False),
                            "candidate_json": json.dumps(candidate_payload, ensure_ascii=False),
                        },
                        response_schema=response_schema,
                        temperature=0.0,
                        cacheable=False,
                        run_id=run_id,
                        module="module3",
                        task_name="study_screening",
                        study_id=study_id,
                        prompt_version=prompt_version,
                    )
                    decision = self._decision_from_payload(candidate, result.content)
                    ordered_results[index] = (decision, candidate, None)
                except Exception as exc:  # pragma: no cover - exercised through fake gateway tests
                    warning = f"Screening failed for {study_id}; defaulted to include: {exc}"
                    decision = ScreeningDecision(
                        study_id=study_id,
                        title=str(candidate_payload.get("title") or ""),
                        included=True,
                        rationale="Included by conservative fallback after screening failure.",
                        warning=warning,
                    )
                    ordered_results[index] = (decision, candidate, warning)

        await asyncio.gather(*(_screen_one(index, candidate) for index, candidate in enumerate(candidates)))

        included: list[Any] = []
        excluded: list[ScreeningDecision] = []
        decisions: list[ScreeningDecision] = []
        warnings: list[str] = []
        for decision, candidate, warning in ordered_results:
            if decision.included:
                included.append(candidate)
            else:
                excluded.append(decision)
            decisions.append(decision)
            if warning:
                warnings.append(warning)
        return ScreeningResult(included=included, excluded=excluded, decisions=decisions, warnings=warnings)

    def _decision_from_payload(self, candidate: Any, content: dict[str, Any]) -> ScreeningDecision:
        return ScreeningDecision(
            study_id=str(content.get("study_id") or _study_id(candidate)),
            title=str(content.get("title") or _candidate_value(candidate, "title") or ""),
            included=bool(content.get("included", True)),
            rationale=str(content.get("rationale") or ""),
            exclusion_reason=content.get("exclusion_reason"),
        )


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


def _candidate_value(candidate: Any, key: str) -> Any:
    if isinstance(candidate, dict):
        return candidate.get(key)
    return getattr(candidate, key, None)


def _study_id(candidate: Any) -> str:
    return str(_candidate_value(candidate, "study_id") or _candidate_value(candidate, "pmid") or "unknown")


def _resolve_concurrency(value: int | None, env_name: str, default: int) -> int:
    if isinstance(value, int) and value > 0:
        return value
    raw = os.getenv(env_name, str(default)).strip()
    try:
        parsed = int(raw)
        return parsed if parsed > 0 else default
    except ValueError:
        return default
