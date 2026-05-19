"""Module 1+2 retrieval API routes (standalone, without Module 3)."""

from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path
from time import perf_counter
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ebm_backend.online_pipeline.application.question_study import (
    DEFAULT_LOCAL_INDEX_PATH,
    DEFAULT_V2_INDEX_PATH,
    QuestionExpander,
    QuestionPIExtractor,
    QuestionStudySearcher,
    QueryGenerator,
)
from ebm_backend.online_pipeline.application.run_pipeline import PipelineOrchestrator, SimplifiedPipelineMockGateway


router = APIRouter(prefix="/retrieval", tags=["retrieval"])


class RetrievalRunRequest(BaseModel):
    question: str = Field(..., min_length=1)
    mode: Literal["static", "dynamic"] = "dynamic"
    top_k: int = Field(default=5, ge=1, le=50)
    index_path: str | None = None
    enable_v2_backfill: bool | None = None
    use_mock_llm: bool = False
    rct_only: bool = True


@router.post("/run")
async def run_retrieval(request: RetrievalRunRequest) -> dict[str, Any]:
    total_start = perf_counter()
    enable_v2_backfill = _resolve_backfill(request)
    gateway = SimplifiedPipelineMockGateway() if request.use_mock_llm else PipelineOrchestrator._real_gateway()
    resolved_index_path = _resolve_index_path(request)

    expander = QuestionExpander()
    expansion_start = perf_counter()
    expansion = await expander.expand_with_llm(gateway, request.question)
    expansion_ms = _elapsed_ms(expansion_start)

    pi_extractor = QuestionPIExtractor()
    pi_start = perf_counter()
    pi = await pi_extractor.extract_with_llm(gateway, expansion)
    pi_ms = _elapsed_ms(pi_start)

    query_generator = QueryGenerator()
    query_start = perf_counter()
    query = await query_generator.generate_with_llm(
        gateway,
        population=pi.population,
        intervention=pi.intervention,
    )
    query_ms = _elapsed_ms(query_start)
    query = _apply_rct_filter(query, enabled=request.rct_only)

    fallback_terms = _fallback_terms(expansion=asdict(expansion), pi=asdict(pi), query=asdict(query))
    # Static mode: fixed local corpus (demo1000 by default).
    # Dynamic mode: online-first retrieval; reuse existing cleaned cache when available.
    searcher = QuestionStudySearcher(
        index_path=resolved_index_path,
        enable_v2_backfill=enable_v2_backfill,
        v2_index_path=resolved_index_path if request.mode == "dynamic" else DEFAULT_V2_INDEX_PATH,
    )
    search_start = perf_counter()
    search = searcher.search_from_query_output(query, top_k=request.top_k, fallback_terms=fallback_terms)
    search_ms = _elapsed_ms(search_start)
    search_payload = asdict(search)
    total_ms = _elapsed_ms(total_start)
    timings_ms = {
        "question_expansion_ms": expansion_ms,
        "question_pi_extraction_ms": pi_ms,
        "query_generation_ms": query_ms,
        "local_search_ms": search_ms,
        "total_ms": total_ms,
    }

    return {
        "expansion": asdict(expansion),
        "pi": asdict(pi),
        "query": asdict(query),
        "search": search_payload,
        "stats": _build_stats(search_payload, timings_ms=timings_ms),
        "cleaned_article_choices": _cleaned_article_choices(search_payload, mode=request.mode),
    }


def _resolve_backfill(request: RetrievalRunRequest) -> bool:
    if request.mode == "static":
        return False
    # Dynamic mode is always online-first.
    return True


def _resolve_index_path(request: RetrievalRunRequest) -> Path:
    if request.mode == "static":
        return Path(request.index_path or DEFAULT_LOCAL_INDEX_PATH)
    # Dynamic mode is strictly cache-first and always uses v2 index.
    # Ignore incoming index_path to avoid accidentally pointing to demo1000.
    return Path(DEFAULT_V2_INDEX_PATH)


def _build_stats(search_payload: dict[str, Any], *, timings_ms: dict[str, int] | None = None) -> dict[str, Any]:
    fallback = search_payload.get("fallback_search") or {}
    v2 = fallback.get("v2_backfill") or {}
    return {
        "retrieved_total": int(search_payload.get("total_hits") or 0),
        "returned_top_k": int(search_payload.get("returned_count") or 0),
        "online_backfill_used": bool(v2.get("used")),
        "pubmed_requested": int(v2.get("requested") or 0),
        "rct_gate_excluded": int(v2.get("rct_gate_excluded") or 0),
        "download_success": int(v2.get("download_success") or 0),
        "clean_success": int(v2.get("clean_success") or 0),
        "ingested_success": int(v2.get("ingested") or 0),
        "timings_ms": timings_ms or {},
    }


def _elapsed_ms(start: float) -> int:
    return max(0, int((perf_counter() - start) * 1000))


def _cleaned_article_choices(search_payload: dict[str, Any], *, mode: str) -> list[str]:
    if mode != "dynamic":
        return []
    choices: list[str] = []
    for item in search_payload.get("studies") or []:
        path = str(item.get("article_path") or "").strip()
        if not path:
            continue
        # Dynamic mode should only expose cleaned files produced by v2 backfill,
        # not static corpus article files from data_demo_1000.
        if "retrieval_cache_v2/articles_cleaned/" in path and Path(path).exists():
            choices.append(path)
    deduped = []
    seen: set[str] = set()
    for item in choices:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _fallback_terms(*, expansion: dict[str, Any], pi: dict[str, Any], query: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    pico = expansion.get("pico") or {}
    terms.extend(pi.get("population") or [])
    terms.extend(pi.get("intervention") or [])
    terms.extend(pico.get("population") or [])
    terms.extend(pico.get("intervention") or [])
    for mapping in (query.get("population_mappings") or []):
        terms.extend(_mapping_terms(mapping))
    for mapping in (query.get("intervention_mappings") or []):
        terms.extend(_mapping_terms(mapping))

    deduped: list[str] = []
    seen: set[str] = set()
    for raw in terms:
        term = " ".join(str(raw or "").strip().split())
        key = term.lower()
        if not term or key in seen:
            continue
        seen.add(key)
        deduped.append(term)
    return deduped


def _mapping_terms(mapping: dict[str, Any]) -> list[str]:
    out: list[str] = []
    out.append(str(mapping.get("original") or ""))
    out.extend(str(term) for term in (mapping.get("mesh_preferred") or []))
    out.extend(str(term) for term in (mapping.get("entry_terms") or []))
    return [item for item in out if item.strip()]


def _apply_rct_filter(query: Any, *, enabled: bool) -> Any:
    if not enabled:
        return query
    rct_block = '("randomized" OR "randomised" OR "controlled trial" OR "clinical trial" OR "placebo")'
    boolean_query = str(getattr(query, "boolean_query", "") or "").strip()
    if not boolean_query:
        return replace(query, boolean_query=rct_block)
    if "randomized" in boolean_query.lower() or "controlled trial" in boolean_query.lower():
        return query
    return replace(query, boolean_query=f"({boolean_query}) AND {rct_block}")
