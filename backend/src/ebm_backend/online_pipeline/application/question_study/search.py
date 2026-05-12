"""Search wrapper for Module 2 simplified local retrieval."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ebm_backend.index_construction.application import LocalRCTIndex
from ebm_backend.online_pipeline.application.question_study.query_gen import QueryGenOutput


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

    def __init__(self, index_path: str | Path = DEFAULT_LOCAL_INDEX_PATH):
        self.index = LocalRCTIndex(index_path)

    def search_from_query_output(
        self,
        output: QueryGenOutput,
        *,
        top_k: int = 20,
        fallback_terms: list[str] | None = None,
    ) -> SearchResult:
        primary = self.search(output.boolean_query, top_k=top_k)
        if primary.studies or not fallback_terms:
            return primary

        fallback_query_text = self._fallback_query_text(fallback_terms)
        if not fallback_query_text:
            return primary

        hits = self.index.search(fallback_query_text, top_k=top_k)
        studies = [self._to_candidate(hit.document, hit.score, hit.matched_fields) for hit in hits]
        return SearchResult(
            query_used=output.boolean_query,
            query_text=primary.query_text,
            total_hits=len(studies),
            returned_count=len(studies),
            studies=studies,
            fallback_level=1 if studies else 0,
            fallback_search={
                "used": bool(studies),
                "reason": "primary_boolean_query_returned_no_hits",
                "query_text": fallback_query_text,
                "terms": fallback_terms,
                "returned_count": len(studies),
            },
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
