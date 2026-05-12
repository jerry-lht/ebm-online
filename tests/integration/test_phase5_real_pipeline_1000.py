from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import pytest

from ebm_backend.shared.llm.gateway import LLMGateway
from ebm_backend.online_pipeline.application.evidence_analysis import Module3AnalysisRunner, result_to_dict
from ebm_backend.online_pipeline.application.evidence_analysis.screening import StudyScreener
from ebm_backend.online_pipeline.application.question_study import (
    EligibilityCriteria,
    PICO,
    QuestionExpander,
    QuestionPIExtractor,
    QuestionStudySearcher,
    QueryGenerator,
)
from ebm_backend.online_pipeline.application.run_pipeline import PipelineOrchestrator
from ebm_backend.online_pipeline.application.run_pipeline import DEFAULT_LOCAL_INDEX_PATH
from ebm_backend.online_pipeline.infrastructure.pipeline_repository import InMemoryPipelineStore, PipelineStatus


REAL_PHASE5_QUESTION = (
    "In orthopedic surgery patients, does tranexamic acid reduce transfusion "
    "compared with no tranexamic acid?"
)
REAL_PHASE5_FULL_QUESTION = (
    "In patients undergoing surgery, do ultrasound-guided nerve blocks or fascial plane blocks "
    "reduce postoperative pain compared with no block or standard analgesia?"
)
REAL_PHASE5_FULL_TOP_K = int(os.getenv("PHASE5_FULL_TOP_K", "6"))
REAL_PHASE5_FULL_TRACE_PATH = Path(os.getenv("PHASE5_FULL_TRACE_PATH", "/tmp/phase5_pain_block_full_trace.json"))
REAL_MODULE2_MODULE3_QUESTION = os.getenv("REAL_MODULE2_MODULE3_QUESTION", REAL_PHASE5_QUESTION)
REAL_MODULE2_MODULE3_TOP_K = int(os.getenv("REAL_MODULE2_MODULE3_TOP_K", "1"))
REAL_MODULE2_MODULE3_TRACE_PATH = Path(
    os.getenv("REAL_MODULE2_MODULE3_TRACE_PATH", "/tmp/ebm_real_llm_1000_module2_module3_trace.json")
)


@pytest.mark.skipif(
    os.getenv("RUN_REAL_LLM") != "1",
    reason="Set RUN_REAL_LLM=1 to run the real external Phase 5 pipeline smoke test.",
)
@pytest.mark.asyncio
async def test_phase5_real_llm_module2_and_screening_against_1000_index():
    index_path = Path(DEFAULT_LOCAL_INDEX_PATH)
    assert index_path.exists(), f"Missing 1000-study local index: {index_path}"
    assert sum(1 for _ in index_path.open(encoding="utf-8")) == 1000

    gateway = LLMGateway(conn=None)

    expansion = await QuestionExpander().expand_with_llm(
        gateway,
        REAL_PHASE5_QUESTION,
        run_id="real-phase5-1000-smoke",
    )
    pi = await QuestionPIExtractor().extract_with_llm(
        gateway,
        expansion,
        run_id="real-phase5-1000-smoke",
    )
    query = await QueryGenerator().generate_with_llm(
        gateway,
        population=pi.population,
        intervention=pi.intervention,
        run_id="real-phase5-1000-smoke",
    )
    search = QuestionStudySearcher(index_path).search_from_query_output(
        query,
        top_k=1,
        fallback_terms=[
            *pi.population,
            *pi.intervention,
            *expansion.pico.population,
            *expansion.pico.intervention,
        ],
    )

    assert expansion.is_medical_question is True
    assert pi.population
    assert pi.intervention
    assert query.boolean_query
    assert search.returned_count >= 1

    candidate = search.studies[0]
    assert candidate.study_id != "mock:phase5-study"
    assert not candidate.study_id.startswith("mock:")
    assert candidate.source not in {"mock", "synthetic"}
    assert candidate.article_path
    assert Path(candidate.article_path).exists()
    assert candidate.matched_fields
    assert candidate.relevance_score > 0

    screening = await StudyScreener().screen_with_llm(
        gateway,
        question=REAL_PHASE5_QUESTION,
        pico=PICO(
            population=expansion.pico.population or ["orthopedic surgery patients"],
            intervention=expansion.pico.intervention or ["tranexamic acid"],
            comparison=expansion.pico.comparison or ["no tranexamic acid"],
            outcome=expansion.pico.outcome or ["transfusion"],
        ),
        eligibility_criteria=EligibilityCriteria(
            inclusion=["studies comparing tranexamic acid with no tranexamic acid"],
            exclusion=["wrong population", "wrong intervention"],
            confidence="medium",
        ),
        candidates=[candidate],
        run_id="real-phase5-1000-smoke",
    )

    assert len(screening.decisions) == 1
    assert screening.decisions[0].study_id == candidate.study_id
    assert screening.decisions[0].title


@pytest.mark.skipif(
    os.getenv("RUN_REAL_LLM_FULL") != "1",
    reason="Set RUN_REAL_LLM_FULL=1 to run the full real Phase 5 trace test.",
)
@pytest.mark.asyncio
async def test_phase5_real_llm_full_pain_block_trace_against_1000_index():
    """Full real pipeline trace for manual inspection.

    This test is intentionally opt-in because it can take several minutes and make
    many external LLM calls. It prints every major stage and saves the complete
    trace JSON to PHASE5_FULL_TRACE_PATH.
    """
    index_path = Path(DEFAULT_LOCAL_INDEX_PATH)
    assert index_path.exists(), f"Missing 1000-study local index: {index_path}"
    assert sum(1 for _ in index_path.open(encoding="utf-8")) == 1000

    run = await PipelineOrchestrator(store=InMemoryPipelineStore()).run_question(
        question=REAL_PHASE5_FULL_QUESTION,
        top_k=REAL_PHASE5_FULL_TOP_K,
        use_mock=False,
    )

    payload = _run_payload(run)
    REAL_PHASE5_FULL_TRACE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    _print_full_trace_summary(payload, REAL_PHASE5_FULL_TRACE_PATH)

    assert run.status == PipelineStatus.COMPLETED, payload
    assert run.result is not None
    assert run.result["query"]["boolean_query"]
    assert run.result["search"]["returned_count"] >= 1
    assert run.result["candidates"]
    assert all(candidate["study_id"] != "mock:phase5-study" for candidate in run.result["candidates"])
    assert "screening" in run.result
    assert "planning" in run.result
    assert "extraction" in run.result
    assert "risk_of_bias" in run.result
    assert "aggregation" in run.result
    assert "grade" in run.result


@pytest.mark.skipif(
    os.getenv("RUN_REAL_LLM") != "1",
    reason="Set RUN_REAL_LLM=1 to run the staged real Module 2 -> Module 3 trace test.",
)
@pytest.mark.asyncio
async def test_phase5_real_llm_module2_1000_candidates_feed_module3_trace():
    """Run real Module 2 against the 1000-study index, then feed candidates to Module 3."""
    index_path = Path(DEFAULT_LOCAL_INDEX_PATH)
    assert index_path.exists(), f"Missing 1000-study local index: {index_path}"
    assert sum(1 for _ in index_path.open(encoding="utf-8")) == 1000

    gateway = LLMGateway(conn=None)

    print(f"\nQUESTION: {REAL_MODULE2_MODULE3_QUESTION}", flush=True)
    expansion = await QuestionExpander().expand_with_llm(
        gateway,
        REAL_MODULE2_MODULE3_QUESTION,
        run_id="real-phase5-full-staged",
    )
    print("STEP question_expansion:", asdict(expansion.pico), flush=True)

    pi = await QuestionPIExtractor().extract_with_llm(
        gateway,
        expansion,
        run_id="real-phase5-full-staged",
    )
    print("STEP question_pi_extraction:", asdict(pi), flush=True)

    query_generator = QueryGenerator()
    query_generation_source = "llm"
    try:
        query = await query_generator.generate_with_llm(
            gateway,
            population=pi.population,
            intervention=pi.intervention,
            run_id="real-phase5-full-staged",
        )
    except Exception as exc:
        if not _is_llm_timeout(exc):
            raise
        query_generation_source = "local_timeout_fallback"
        print(f"STEP query_generation_timeout: {exc.__class__.__name__}", flush=True)
        query = query_generator.generate(population=pi.population, intervention=pi.intervention)
    print("STEP query_generation:", query.boolean_query, flush=True)

    search = QuestionStudySearcher(index_path).search_from_query_output(
        query,
        top_k=REAL_MODULE2_MODULE3_TOP_K,
        fallback_terms=[
            *pi.population,
            *pi.intervention,
            *expansion.pico.population,
            *expansion.pico.intervention,
        ],
    )
    print(f"STEP local_search: returned={search.returned_count} fallback={search.fallback_search}", flush=True)
    for idx, study in enumerate(search.studies, start=1):
        print(
            f"  candidate {idx}: {study.study_id} score={study.relevance_score} "
            f"fields={study.matched_fields} title={study.title}",
            flush=True,
        )

    assert search.returned_count >= 1
    assert all(not study.study_id.startswith("mock:") for study in search.studies)
    assert all(study.source not in {"mock", "synthetic"} for study in search.studies)
    assert all(study.article_path and Path(study.article_path).exists() for study in search.studies)

    module3 = await Module3AnalysisRunner(gateway).run(
        question=REAL_MODULE2_MODULE3_QUESTION,
        pico=expansion.pico,
        eligibility_criteria=expansion.eligibility_criteria,
        preliminary_plan=expansion.preliminary_analysis_plan,
        candidates=search.studies,
        run_id="real-phase5-full-staged",
    )
    module3_payload = result_to_dict(module3)
    payload = {
        "question": REAL_MODULE2_MODULE3_QUESTION,
        "index_path": str(index_path),
        "top_k": REAL_MODULE2_MODULE3_TOP_K,
        "module2": {
            "expansion": asdict(expansion),
            "pi": asdict(pi),
            "query": asdict(query),
            "query_generation_source": query_generation_source,
            "search": asdict(search),
        },
        "module3": module3_payload,
    }
    REAL_MODULE2_MODULE3_TRACE_PATH.write_text(
        json.dumps(_jsonable(payload), ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    print("STEP module3_screening:", _screening_summary(module3_payload.get("screening") or {}), flush=True)
    print("STEP module3_planning:", module3_payload.get("planning"), flush=True)
    print("STEP module3_extraction:", module3_payload.get("extraction"), flush=True)
    print("STEP module3_risk_of_bias:", module3_payload.get("risk_of_bias"), flush=True)
    print("STEP module3_aggregation:", module3_payload.get("aggregation"), flush=True)
    print("STEP module3_grade:", module3_payload.get("grade"), flush=True)
    print("SAVED:", REAL_MODULE2_MODULE3_TRACE_PATH, flush=True)

    assert module3_payload["screening"]["decisions"]
    assert "risk_of_bias" in module3_payload
    assert "grade" in module3_payload


def _run_payload(run) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "status": run.status.value,
        "error": run.error,
        "question": run.question,
        "top_k": run.top_k,
        "use_mock": run.use_mock,
        "index_path": run.index_path,
        "steps": [_jsonable(step) for step in run.steps],
        "result": _jsonable(run.result),
    }


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _print_full_trace_summary(payload: dict[str, Any], trace_path: Path) -> None:
    print("\nFULL PHASE 5 TRACE", flush=True)
    print("status=", payload["status"], "error=", payload["error"], flush=True)
    print("run_id=", payload["run_id"], flush=True)
    print("trace_path=", trace_path, flush=True)
    for step in payload["steps"]:
        print(f"STEP {step['name']}: {step['status']} | {step.get('summary')}", flush=True)

    result = payload.get("result") or {}
    print("query=", (result.get("query") or {}).get("boolean_query"), flush=True)
    print(
        "search_returned=",
        (result.get("search") or {}).get("returned_count"),
        "fallback=",
        (result.get("search") or {}).get("fallback_search"),
        flush=True,
    )
    for idx, candidate in enumerate(result.get("candidates") or [], start=1):
        print(
            f"  candidate {idx}: {candidate.get('study_id')} score={candidate.get('relevance_score')} "
            f"fields={candidate.get('matched_fields')} title={candidate.get('title')}",
            flush=True,
        )
    print("screening=", _screening_summary(result.get("screening") or {}), flush=True)
    print("planning=", result.get("planning"), flush=True)
    print("extraction=", result.get("extraction"), flush=True)
    print("risk_of_bias=", result.get("risk_of_bias"), flush=True)
    print("aggregation=", result.get("aggregation"), flush=True)
    print("grade=", result.get("grade"), flush=True)
    print("warnings=", result.get("warnings"), flush=True)


def _screening_summary(screening: dict[str, Any]) -> dict[str, Any]:
    return {
        "included": len(screening.get("included") or []),
        "excluded": len(screening.get("excluded") or []),
        "decisions": [
            {
                "study_id": decision.get("study_id"),
                "included": decision.get("included"),
                "reason": decision.get("exclusion_reason"),
                "rationale": decision.get("rationale"),
            }
            for decision in screening.get("decisions") or []
        ],
        "warnings": screening.get("warnings") or [],
    }


def _is_llm_timeout(exc: Exception) -> bool:
    current: BaseException | None = exc
    while current is not None:
        if current.__class__.__name__ in {"APITimeoutError", "TimeoutException", "ReadTimeout"}:
            return True
        current = current.__cause__
    return False
