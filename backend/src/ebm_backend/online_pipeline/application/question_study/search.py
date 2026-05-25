"""Search wrapper for Module 2 simplified local retrieval."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ebm_backend.index_construction.application import LocalRCTIndex
from ebm_backend.online_pipeline.application.question_study.query_gen import QueryGenOutput
from ebm_backend.online_pipeline.application.question_study.retrieval_cache_v2 import (
    DEFAULT_V2_INDEX_PATH,
    RetrievalCacheV2,
)


DEFAULT_LOCAL_INDEX_PATH = "data/data_for_test/data_demo_1000/index/local_rct_index.jsonl"


@dataclass(frozen=True)
class CandidateStudy:
    study_id: str
    pmid: str | None
    pmcid: str | None
    title: str
    abstract: str | None
    population: str | None
    intervention: str | None
    source: str | None
    relevance_score: float
    article_path: str | None
    matched_fields: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SearchResult:
    query_used: str
    total_hits: int
    returned_count: int
    query_text: str = ""
    studies: list[CandidateStudy] = field(default_factory=list)
    fallback_level: int = 0
    fallback_search: dict[str, Any] | None = None


class QuestionStudySearcher:
    """Module 2 local retriever backed by LocalRCTIndex."""

    def __init__(
        self,
        index_path: str | Path = DEFAULT_LOCAL_INDEX_PATH,
        *,
        enable_v2_backfill: bool = False,
        v2_index_path: str | Path = DEFAULT_V2_INDEX_PATH,
        v2_cache_root: str | Path = "data/retrieval_cache_v2",
        v2_min_local_hits: int = 5,
        v2_pubmed_fetch_count: int = 30,
        v2_timeout: int = 30,
        v2_retries: int = 1,
        v2_requests_per_second: float = 3.0,
    ):
        self.index = LocalRCTIndex(index_path)
        self.enable_v2_backfill = enable_v2_backfill
        self.v2_cache: RetrievalCacheV2 | None = None
        if self.enable_v2_backfill:
            self.v2_cache = RetrievalCacheV2.from_paths(
                cache_root=v2_cache_root,
                index_path=v2_index_path,
                min_local_hits=v2_min_local_hits,
                pubmed_fetch_count=v2_pubmed_fetch_count,
                timeout=v2_timeout,
                retries=v2_retries,
                requests_per_second=v2_requests_per_second,
            )

    def search_from_query_output(
        self,
        output: QueryGenOutput,
        *,
        top_k: int = 20,
        fallback_terms: list[str] | None = None,
    ) -> SearchResult:
        terms = fallback_terms or []
        if self.v2_cache is not None:
            return self._search_dynamic_online_first(output=output, top_k=top_k, fallback_terms=terms)

        primary = self.search(output.boolean_query, top_k=top_k)

        should_use_fallback_terms = not primary.studies
        fallback_query_text = self._fallback_query_text(terms) if should_use_fallback_terms else ""
        fallback_studies: list[CandidateStudy] = []
        if fallback_query_text:
            fallback_hits = self.index.search(fallback_query_text, top_k=top_k)
            fallback_studies = [self._to_candidate(hit.document, hit.score, hit.matched_fields) for hit in fallback_hits]

        merged = self._merge_studies(primary.studies, fallback_studies, top_k=top_k)

        fallback_payload: dict[str, Any] = {
            "used": bool(fallback_studies) and should_use_fallback_terms,
            "reason": "primary_boolean_query_returned_no_hits" if not primary.studies else "primary_query_sufficient",
            "query_text": fallback_query_text,
            "terms": terms,
            "returned_count": len(merged),
        }

        backfill_payload: dict[str, Any] | None = None
        if self.v2_cache is not None:
            try:
                backfill_payload = self.v2_cache.maybe_backfill(
                    output=output,
                    fallback_terms=terms,
                    top_k=top_k,
                    current_local_hits=len(merged),
                )
            except Exception as exc:
                backfill_payload = {
                    "used": False,
                    "reason": "v2_backfill_failed",
                    "error": str(exc),
                }

            if backfill_payload and backfill_payload.get("ingested", 0) > 0:
                v2_primary = self._search_v2(output.boolean_query, top_k=top_k)
                v2_fallback = self._search_v2(fallback_query_text, top_k=top_k) if fallback_query_text else []
                merged = self._merge_studies(merged, self._merge_studies(v2_primary, v2_fallback, top_k=top_k), top_k=top_k)

        if backfill_payload is not None:
            fallback_payload["v2_backfill"] = backfill_payload

        if merged:
            return SearchResult(
                query_used=output.boolean_query,
                query_text=primary.query_text,
                total_hits=len(merged),
                returned_count=len(merged),
                studies=merged,
                fallback_level=1 if fallback_payload.get("used") else 0,
                fallback_search=fallback_payload,
            )

        if primary.studies:
            return primary

        return SearchResult(
            query_used=output.boolean_query,
            query_text=primary.query_text,
            total_hits=0,
            returned_count=0,
            studies=[],
            fallback_level=0,
            fallback_search=fallback_payload,
        )

    def _search_dynamic_online_first(
        self,
        *,
        output: QueryGenOutput,
        top_k: int,
        fallback_terms: list[str],
    ) -> SearchResult:
        assert self.v2_cache is not None
        try:
            online = self.v2_cache.online_first_retrieve(output=output, fallback_terms=fallback_terms, top_k=top_k)
        except Exception as exc:
            return SearchResult(
                query_used=output.boolean_query,
                query_text=self._query_text_for_local_search(output.boolean_query),
                total_hits=0,
                returned_count=0,
                studies=[],
                fallback_level=0,
                fallback_search={"used": False, "reason": "v2_backfill_failed", "error": str(exc), "terms": fallback_terms},
            )

        docs = online.get("studies") or []
        studies = [
            self._to_candidate(
                doc,
                float(max(1, top_k - int(doc.get("_online_rank") or 0))),
                ["online_pubmed"],
            )
            for doc in docs
        ]
        return SearchResult(
            query_used=output.boolean_query,
            query_text=online.get("query") or self._query_text_for_local_search(output.boolean_query),
            total_hits=len(studies),
            returned_count=len(studies),
            studies=studies,
            fallback_level=0,
            fallback_search={"used": True, "reason": "dynamic_online_first", "terms": fallback_terms, "v2_backfill": online.get("v2_backfill") or {}},
        )

    def search(self, boolean_query: str, *, top_k: int = 20) -> SearchResult:
        query_text = self._query_text_for_local_search(boolean_query)
        hits = self.index.search(query_text, top_k=top_k)
        studies = [self._to_candidate(hit.document, hit.score, hit.matched_fields) for hit in hits]
        return SearchResult(
            query_used=boolean_query,
            total_hits=len(studies),
            returned_count=len(studies),
            query_text=query_text,
            studies=studies,
            fallback_level=0,
        )

    @staticmethod
    def _to_candidate(doc: dict[str, Any], score: float, matched_fields: list[str]) -> CandidateStudy:
        return CandidateStudy(
            study_id=str(doc.get("study_id") or ""),
            pmid=doc.get("pmid"),
            pmcid=doc.get("pmcid"),
            title=str(doc.get("title") or ""),
            abstract=doc.get("abstract"),
            population=doc.get("population"),
            intervention=doc.get("intervention"),
            source=doc.get("source"),
            relevance_score=float(score),
            article_path=doc.get("article_path"),
            matched_fields=list(matched_fields),
        )

    @staticmethod
    def _query_text_for_local_search(boolean_query: str) -> str:
        quoted = re.findall(r'"([^"]+)"', boolean_query)
        if quoted:
            return " ".join(quoted)
        text = re.sub(r"\bAND\b|\bOR\b", " ", boolean_query, flags=re.IGNORECASE)
        text = re.sub(r"[()]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _fallback_query_text(terms: list[str]) -> str:
        seen: set[str] = set()
        cleaned: list[str] = []
        for raw in terms:
            term = " ".join(str(raw or "").strip().split())
            key = term.lower()
            if not term or key in seen:
                continue
            seen.add(key)
            cleaned.append(term)
        return " ".join(cleaned)

    def _search_v2(self, boolean_or_free_query: str, *, top_k: int) -> list[CandidateStudy]:
        if self.v2_cache is None:
            return []
        query_text = self._query_text_for_local_search(boolean_or_free_query)
        hits = self.v2_cache.index.search(query_text, top_k=top_k)
        return [self._to_candidate(hit.document, hit.score, hit.matched_fields) for hit in hits]

    @staticmethod
    def _merge_studies(primary: list[CandidateStudy], secondary: list[CandidateStudy], *, top_k: int) -> list[CandidateStudy]:
        merged: dict[str, CandidateStudy] = {}
        for item in primary + secondary:
            key = item.study_id or item.pmid or item.title
            current = merged.get(key)
            if current is None or item.relevance_score > current.relevance_score:
                merged[key] = item
        ordered = sorted(merged.values(), key=lambda row: (-row.relevance_score, row.study_id))
        return ordered[:top_k]
