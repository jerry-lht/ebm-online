"""End-to-end Module 2 LLM runner without SQL requirements."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from ebm_backend.shared.llm.gateway import LLMGateway
from ebm_backend.online_pipeline.application.question_study.expansion import QuestionExpander, QuestionExpansionResult
from ebm_backend.online_pipeline.application.question_study.pi import QuestionPI, QuestionPIExtractor
from ebm_backend.online_pipeline.application.question_study.query_gen import QueryGenOutput, QueryGenerator
from ebm_backend.online_pipeline.application.question_study.search import DEFAULT_LOCAL_INDEX_PATH, QuestionStudySearcher, SearchResult


@dataclass(frozen=True)
class Module2LLMResult:
    expansion: QuestionExpansionResult
    pi: QuestionPI
    query: QueryGenOutput
    search: SearchResult


class Module2LLMRunner:
    """Run question expansion -> PI extraction -> MeSH/query expansion -> search."""

    def __init__(
        self,
        gateway: LLMGateway,
        *,
        index_path: str | Path = DEFAULT_LOCAL_INDEX_PATH,
    ):
        self.gateway = gateway
        self.expander = QuestionExpander()
        self.pi_extractor = QuestionPIExtractor()
        self.query_generator = QueryGenerator()
        self.searcher = QuestionStudySearcher(index_path=index_path)

    async def run(self, question: str, *, top_k: int = 20, run_id: str | None = None) -> Module2LLMResult:
        expansion = await self.expander.expand_with_llm(self.gateway, question, run_id=run_id)
        pi = await self.pi_extractor.extract_with_llm(self.gateway, expansion, run_id=run_id)
        query = await self.query_generator.generate_with_llm(
            self.gateway,
            population=pi.population,
            intervention=pi.intervention,
            run_id=run_id,
        )
        search = self.searcher.search_from_query_output(
            query,
            top_k=top_k,
            fallback_terms=[*pi.population, *pi.intervention, *expansion.pico.population, *expansion.pico.intervention],
        )
        return Module2LLMResult(
            expansion=expansion,
            pi=pi,
            query=query,
            search=search,
        )

    def run_sync(self, question: str, *, top_k: int = 20, run_id: str | None = None) -> Module2LLMResult:
        return asyncio.run(self.run(question, top_k=top_k, run_id=run_id))
