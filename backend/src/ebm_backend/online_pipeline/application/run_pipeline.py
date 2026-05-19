"""Synchronous simplified pipeline orchestrator for Phase 5."""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

try:
    from openai import AsyncOpenAI
except ModuleNotFoundError:  # pragma: no cover
    AsyncOpenAI = None  # type: ignore[assignment]

from ebm_backend.shared.config.settings import settings
from ebm_backend.shared.llm.gateway import LLMGateway, LLMResult
from ebm_backend.shared.llm.tracker import TokenUsage
from ebm_backend.online_pipeline.application.evidence_analysis import Module3AnalysisRunner, result_to_dict
from ebm_backend.online_pipeline.application.question_study import (
    EligibilityCriteria,
    PreliminaryAnalysisPlan,
    DEFAULT_LOCAL_INDEX_PATH,
    QuestionExpander,
    QuestionPIExtractor,
    QuestionStudySearcher,
    QueryGenerator,
)
from ebm_backend.online_pipeline.infrastructure.pipeline_repository import (
    DEFAULT_PIPELINE_STORE,
    InMemoryPipelineStore,
    PipelineRunState,
    PipelineStatus,
    PipelineStepTrace,
    StepStatus,
    utc_now,
)


DEMO_1000_MANIFEST_PATH = "data/data_for_test/data_demo_1000/manifest/selection_summary.json"
DEMO_1000_QUESTION_PRESETS = [
    "In patients undergoing surgery, do nerve blocks reduce postoperative pain compared with usual analgesia?",
    "In orthopedic surgery patients, does tranexamic acid reduce transfusion compared with no tranexamic acid?",
    "In patients with diabetes, does exercise training improve glycemic control compared with usual care?",
    "In patients with COVID-19 or respiratory disease, does rehabilitation improve functional outcomes?",
    "In dental procedures, do local anesthesia techniques reduce procedural pain compared with conventional injection?",
    "In pregnant or postpartum women, does exercise or lifestyle intervention improve maternal outcomes?",
]


class PipelineOrchestrator:
    """Run Module 2 and Module 3 while recording inspectable step traces."""

    def __init__(
        self,
        *,
        store: InMemoryPipelineStore | None = None,
        index_path: str | Path = DEFAULT_LOCAL_INDEX_PATH,
        enable_v2_backfill: bool = False,
    ):
        self.store = store or DEFAULT_PIPELINE_STORE
        self.index_path = Path(index_path)
        self.enable_v2_backfill = bool(enable_v2_backfill)

    def create_pending_run(
        self,
        *,
        question: str,
        top_k: int = 5,
        use_mock: bool = False,
        index_path: str | Path | None = None,
    ) -> PipelineRunState:
        resolved_index_path = Path(index_path) if index_path is not None else self.index_path
        run = PipelineRunState(
            run_id=str(uuid.uuid4()),
            question=question,
            top_k=top_k,
            use_mock=use_mock,
            index_path=str(resolved_index_path),
        )
        return self.store.create(run)

    async def run_existing(self, run: PipelineRunState) -> PipelineRunState:
        return await self._execute_run(run)

    async def run_question(
        self,
        *,
        question: str,
        top_k: int = 5,
        use_mock: bool = False,
        index_path: str | Path | None = None,
    ) -> PipelineRunState:
        run = self.create_pending_run(
            question=question,
            top_k=top_k,
            use_mock=use_mock,
            index_path=index_path,
        )
        return await self._execute_run(run)

    async def _execute_run(self, run: PipelineRunState) -> PipelineRunState:
        question = run.question
        top_k = run.top_k
        use_mock = run.use_mock
        resolved_index_path = Path(run.index_path or self.index_path)
        run_id = run.run_id
        gateway: Any = SimplifiedPipelineMockGateway() if use_mock else self._real_gateway()

        try:
            run.status = PipelineStatus.RUNNING
            self.store.save(run)

            expander = QuestionExpander()
            expansion = await self._run_step(
                run,
                "question_expansion",
                lambda: expander.expand_with_llm(gateway, question, run_id=run_id),
                lambda value: {
                    "summary": _pico_summary(value.pico),
                    "payload": asdict(value),
                },
            )
            if not expansion.is_medical_question:
                raise ValueError("Question expansion marked this input as non-medical.")

            pi_extractor = QuestionPIExtractor()
            pi = await self._run_step(
                run,
                "question_pi_extraction",
                lambda: pi_extractor.extract_with_llm(gateway, expansion, run_id=run_id),
                lambda value: {
                    "summary": f"P={'; '.join(value.population) or 'n/a'} | I={'; '.join(value.intervention) or 'n/a'}",
                    "payload": asdict(value),
                },
            )

            query_generator = QueryGenerator()
            query = await self._run_step(
                run,
                "query_generation",
                lambda: query_generator.generate_with_llm(
                    gateway,
                    population=pi.population,
                    intervention=pi.intervention,
                    run_id=run_id,
                ),
                lambda value: {
                    "summary": value.boolean_query,
                    "payload": asdict(value),
                },
            )

            searcher = QuestionStudySearcher(index_path=resolved_index_path, enable_v2_backfill=self.enable_v2_backfill)
            search = await self._run_step(
                run,
                "local_search",
                lambda: _awaitable_value(
                    searcher.search_from_query_output(
                        query,
                        top_k=top_k,
                        fallback_terms=_fallback_terms(pi=pi, expansion=expansion, query=query),
                    )
                ),
                lambda value: {
                    "summary": _search_summary(value),
                    "payload": asdict(value),
                },
            )
            candidates = search.studies
            if use_mock and not candidates:
                candidates = [_mock_candidate(question, expansion.pico)]

            module3_runner = Module3AnalysisRunner(gateway)
            screening = await self._run_step(
                run,
                "module3_screening",
                lambda: module3_runner.run_screening(
                    question=question,
                    pico=expansion.pico,
                    eligibility_criteria=expansion.eligibility_criteria,
                    candidates=candidates,
                    run_id=run_id,
                ),
                lambda value: {
                    "summary": f"included={len(value.included)} excluded={len(value.excluded)} warnings={len(value.warnings)}",
                    "payload": asdict(value),
                },
            )
            planning = await self._run_step(
                run,
                "module3_planning",
                lambda: module3_runner.run_planning(
                    question=question,
                    pico=expansion.pico,
                    preliminary_plan=expansion.preliminary_analysis_plan,
                    screening=screening,
                    run_id=run_id,
                ),
                lambda value: {
                    "summary": f"analyses={len(value.analyses)} warnings={len(value.warnings)}",
                    "payload": asdict(value),
                },
            )
            evidence = module3_runner.build_evidence_contexts(screening=screening)
            extraction_task = self._run_step(
                run,
                "module3_extraction",
                lambda: module3_runner.extractor.extract_with_llm(
                    module3_runner.gateway,
                    analyses=planning.analyses,
                    evidence_contexts=evidence,
                    run_id=run_id,
                ),
                lambda value: {
                    "summary": f"rows={len(value.rows)} warnings={len(value.warnings)}",
                    "payload": asdict(value),
                },
            )
            rob_task = self._run_step(
                run,
                "module3_rob",
                lambda: module3_runner.rob_assessor.assess_with_llm(
                    module3_runner.gateway,
                    evidence_contexts=evidence,
                    run_id=run_id,
                ),
                lambda value: {
                    "summary": f"assessments={len(value.assessments)} warnings={len(value.warnings)}",
                    "payload": asdict(value),
                },
            )
            extraction, risk_of_bias = await asyncio.gather(extraction_task, rob_task)
            aggregation = await self._run_step(
                run,
                "module3_aggregation",
                lambda: _awaitable_value(module3_runner.run_aggregation(planning=planning, extraction=extraction)),
                lambda value: {
                    "summary": f"analyses={len(value.analyses)} warnings={len(value.warnings)}",
                    "payload": asdict(value),
                },
            )
            grade = await self._run_step(
                run,
                "module3_grade",
                lambda: module3_runner.run_grade(aggregation=aggregation, risk_of_bias=risk_of_bias, run_id=run_id),
                lambda value: {
                    "summary": f"assessments={len(value.assessments)} warnings={len(value.warnings)}",
                    "payload": asdict(value),
                },
            )
            module3_result = module3_runner.compose_result(
                screening=screening,
                planning=planning,
                evidence=evidence,
                extraction=extraction,
                risk_of_bias=risk_of_bias,
                aggregation=aggregation,
                grade=grade,
            )
            module3 = await self._run_step(
                run,
                "module3_analysis",
                lambda: _awaitable_value(module3_result),
                lambda value: {
                    "summary": _module3_summary(result_to_dict(value)),
                    "payload": result_to_dict(value),
                },
            )

            run.result = _compact_result(
                module2={
                    "expansion": asdict(expansion),
                    "pi": asdict(pi),
                    "query": asdict(query),
                    "search": asdict(search),
                    "module3_candidates": [asdict(candidate) for candidate in candidates],
                    "demo": demo_1000_context(),
                },
                module3=result_to_dict(module3),
            )
            run.status = PipelineStatus.COMPLETED
            run.completed_at = utc_now()
            self.store.save(run)
            return run
        except Exception as exc:
            run.status = PipelineStatus.FAILED
            run.error = str(exc)
            run.completed_at = utc_now()
            self.store.save(run)
            return run

    async def _run_step(self, run: PipelineRunState, name: str, action, serializer):
        step = PipelineStepTrace(name=name, status=StepStatus.RUNNING, started_at=utc_now())
        run.steps.append(step)
        self.store.save(run)
        try:
            value = await action()
            serialized = serializer(value)
            step.status = StepStatus.COMPLETED
            step.summary = str(serialized.get("summary") or "")
            step.payload = dict(serialized.get("payload") or {})
            step.completed_at = utc_now()
            self.store.save(run)
            return value
        except Exception as exc:
            step.status = StepStatus.FAILED
            step.error = str(exc)
            step.completed_at = utc_now()
            self.store.save(run)
            raise

    @staticmethod
    def _real_gateway() -> LLMGateway:
        if AsyncOpenAI is None:  # pragma: no cover
            raise RuntimeError("openai package is required for real LLM execution")
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for real LLM execution.")
        return LLMGateway(
            conn=None,
            client=AsyncOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                timeout=float(os.getenv("LLM_TIMEOUT_SECONDS", "180")),
            ),
        )


class SimplifiedPipelineMockGateway:
    """Deterministic LLM substitute covering Module 2 and Module 3 task schemas."""

    async def call(self, **kwargs) -> LLMResult:
        task_type = kwargs["task_type"]
        inputs = kwargs.get("inputs") or {}
        content = self._content(task_type, inputs)
        return LLMResult(
            content=content,
            raw_response=json.dumps(content, ensure_ascii=False),
            usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            cached=False,
            latency_ms=0,
            call_id=f"mock-{task_type}",
        )

    def _content(self, task_type: str, inputs: dict[str, Any]) -> dict[str, Any]:
        if task_type == "question_expansion":
            question = str(inputs.get("question") or "")
            return {
                "is_medical_question": True,
                "expanded_question": question,
                "pico": {
                    "population": ["catheter-related bladder discomfort"],
                    "intervention": ["duloxetine"],
                    "comparison": ["placebo"],
                    "outcome": ["catheter-related bladder discomfort incidence"],
                },
                "eligibility_criteria": {
                    "inclusion": ["randomized controlled trials"],
                    "exclusion": ["non-human studies"],
                    "confidence": "low",
                },
                "preliminary_analysis_plan": {
                    "primary_outcome": "catheter-related bladder discomfort incidence",
                    "secondary_outcomes": [],
                    "timepoints": [],
                    "effect_measures": {"binary": "RR", "continuous": "MD"},
                    "subgroups_of_interest": [],
                    "confidence": "low",
                },
                "needs_user_confirmation": [],
            }
        if task_type == "question_pi_extraction":
            pico = inputs.get("pico") or {}
            return {
                "population": list(pico.get("population") or ["catheter-related bladder discomfort"]),
                "intervention": list(pico.get("intervention") or ["duloxetine"]),
                "notes": "Mock PI extraction for Phase 5 smoke.",
            }
        if task_type == "query_generation":
            population = inputs.get("population") or ["catheter-related bladder discomfort"]
            intervention = inputs.get("intervention") or ["duloxetine"]
            return {
                "population_mappings": [
                    {
                        "original": str(population[0]),
                        "mesh_preferred": [],
                        "entry_terms": ["catheter related bladder discomfort", "CRBD"],
                    }
                ],
                "intervention_mappings": [
                    {
                        "original": str(intervention[0]),
                        "mesh_preferred": [],
                        "entry_terms": [],
                    }
                ],
                "population_extra_terms": [],
                "intervention_extra_terms": [],
                "notes": "Mock query generation for Phase 5 smoke.",
            }
        if task_type == "study_screening":
            candidate = inputs.get("candidate") or {}
            return {
                "study_id": candidate.get("study_id") or "unknown",
                "title": candidate.get("title") or "",
                "included": True,
                "rationale": "Mock screening includes retrieved studies.",
                "exclusion_reason": None,
            }
        if task_type == "analysis_planning":
            plan = inputs.get("preliminary_plan") or {}
            pico = inputs.get("pico") or {}
            return {
                "analyses": [
                    {
                        "analysis_id": "a1",
                        "outcome": plan.get("primary_outcome") or _first(pico.get("outcome")) or "Primary outcome",
                        "outcome_type": "binary",
                        "effect_measure": "RR",
                        "intervention": _first(pico.get("intervention")) or "intervention",
                        "comparator": _first(pico.get("comparison")) or "control",
                        "timepoint": None,
                        "pooling_method": "IV",
                        "model": "fixed",
                        "notes": "Mock analysis plan.",
                    }
                ],
                "warnings": [],
            }
        if task_type == "data_extraction":
            analysis = inputs.get("analysis") or {}
            context = inputs.get("evidence_context") or {}
            return {
                "study_id": context.get("study_id") or "unknown",
                "analysis_id": analysis.get("analysis_id") or "a1",
                "outcome_type": "binary",
                "effect_measure": "RR",
                "extraction_status": "included",
                "missing_reason": None,
                "exp_mean": None,
                "exp_sd": None,
                "exp_n": 32,
                "ctrl_mean": None,
                "ctrl_sd": None,
                "ctrl_n": 32,
                "exp_events": 5,
                "ctrl_events": 17,
                "giv_effect": None,
                "giv_se": None,
                "evidence_spans": ["Mock extraction uses visible event-count style fields."],
                "notes": "Mock extraction.",
            }
        if task_type == "risk_of_bias":
            context = inputs.get("evidence_context") or {}
            return {
                "study_id": context.get("study_id") or "unknown",
                "domains": [
                    {
                        "domain": "random_sequence_generation",
                        "judgement": "unclear",
                        "rationale": "Mock RoB judgement.",
                        "evidence": "",
                    }
                ],
                "overall": "unclear",
                "warnings": [],
            }
        if task_type == "grade_assessment":
            aggregation = inputs.get("aggregation") or {}
            return {
                "analysis_id": aggregation.get("analysis_id") or "a1",
                "certainty": "low",
                "downgrade_reasons": ["Mock certainty assessment."],
                "rationale": "Mock GRADE assessment based on synthetic extraction.",
                "warnings": [],
            }
        raise ValueError(f"Unsupported mock task: {task_type}")


async def _awaitable_value(value):
    return value


def _first(values: Any) -> str | None:
    if not values:
        return None
    return str(values[0])


def _pico_summary(pico: Any) -> str:
    return (
        f"P={'; '.join(pico.population) or 'n/a'} | "
        f"I={'; '.join(pico.intervention) or 'n/a'} | "
        f"C={'; '.join(pico.comparison) or 'n/a'} | "
        f"O={'; '.join(pico.outcome) or 'n/a'}"
    )


def _module3_summary(payload: dict[str, Any]) -> str:
    included = len(payload.get("screening", {}).get("included") or [])
    excluded = len(payload.get("screening", {}).get("excluded") or [])
    analyses = len(payload.get("planning", {}).get("analyses") or [])
    rows = len(payload.get("extraction", {}).get("rows") or [])
    grade = len(payload.get("grade", {}).get("assessments") or [])
    return f"{included} included, {excluded} excluded, {analyses} analyses, {rows} extracted rows, {grade} GRADE assessments"


def _search_summary(value: Any) -> str:
    if value.fallback_search and value.fallback_search.get("used"):
        return f"{value.returned_count} candidate studies returned by fallback search"
    return f"{value.returned_count} candidate studies returned"


def _mock_candidate(question: str, pico: Any) -> Any:
    from ebm_backend.online_pipeline.application.question_study import CandidateStudy

    return CandidateStudy(
        study_id="mock:phase5-study",
        pmid=None,
        pmcid=None,
        title="Synthetic mock study for Phase 5 pipeline smoke",
        abstract=(
            f"Mock RCT for {question}. The intervention group had 5 events among 32 participants, "
            "and the control group had 17 events among 32 participants."
        ),
        population=_first(pico.population) or question,
        intervention=_first(pico.intervention) or question,
        source="mock",
        relevance_score=0.0,
        article_path=None,
    )


def _compact_result(*, module2: dict[str, Any], module3: dict[str, Any]) -> dict[str, Any]:
    return {
        "question_expansion": module2["expansion"],
        "pi": module2["pi"],
        "query": module2["query"],
        "search": module2["search"],
        "candidates": module2.get("module3_candidates") or module2["search"].get("studies", []),
        "screening": module3.get("screening"),
        "planning": module3.get("planning"),
        "extraction": module3.get("extraction"),
        "risk_of_bias": module3.get("risk_of_bias"),
        "aggregation": module3.get("aggregation"),
        "grade": module3.get("grade"),
        "warnings": module3.get("warnings", []),
        "demo_1000": module2.get("demo"),
    }


def _fallback_terms(*, pi: Any, expansion: Any, query: Any) -> list[str]:
    terms: list[str] = []
    terms.extend(pi.population)
    terms.extend(pi.intervention)
    terms.extend(expansion.pico.population)
    terms.extend(expansion.pico.intervention)
    terms.extend(_mapping_terms(query.mapping_detail.get("population") or []))
    terms.extend(_mapping_terms(query.mapping_detail.get("intervention") or []))
    terms.extend(_demo_relevant_keywords(" ".join(str(term) for term in terms)))
    seen: set[str] = set()
    out: list[str] = []
    for raw in terms:
        term = " ".join(str(raw or "").strip().split())
        key = term.lower()
        if term and key not in seen:
            seen.add(key)
            out.append(term)
    return out


def _mapping_terms(mappings: list[Any]) -> list[str]:
    terms: list[str] = []
    for mapping in mappings:
        terms.append(mapping.original)
        terms.extend(mapping.mesh_preferred)
        terms.extend(mapping.entry_terms)
    return terms


def demo_1000_context() -> dict[str, Any]:
    manifest_path = Path(DEMO_1000_MANIFEST_PATH)
    context: dict[str, Any] = {
        "index_path": DEFAULT_LOCAL_INDEX_PATH,
        "manifest_path": DEMO_1000_MANIFEST_PATH,
        "question_presets": DEMO_1000_QUESTION_PRESETS,
    }
    if not manifest_path.exists():
        return context
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return context
    theme_keywords = payload.get("theme_keywords") or {}
    keywords: list[str] = []
    for values in theme_keywords.values():
        keywords.extend(str(value) for value in values)
    context.update(
        {
            "selected_total": payload.get("selected_total"),
            "theme_counts": payload.get("theme_counts") or {},
            "theme_keywords": theme_keywords,
            "keywords": keywords,
        }
    )
    return context


def _demo_relevant_keywords(text: str) -> list[str]:
    normalized = text.lower()
    keywords: list[str] = []
    for theme_terms in (demo_1000_context().get("theme_keywords") or {}).values():
        theme_values = [str(value) for value in theme_terms]
        if any(term.lower() in normalized for term in theme_values):
            keywords.extend(theme_values)
    return keywords
