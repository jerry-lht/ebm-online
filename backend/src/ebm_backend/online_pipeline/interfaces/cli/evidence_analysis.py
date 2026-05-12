"""Command-line entry point for the simplified Module 3 pipeline."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ebm_backend.shared.llm.gateway import LLMResult
from ebm_backend.shared.llm.tracker import TokenUsage
from ebm_backend.online_pipeline.application.evidence_analysis.runner import Module3AnalysisRunner, result_to_dict
from ebm_backend.online_pipeline.application.question_study import (
    CandidateStudy,
    EligibilityCriteria,
    PICO,
    PreliminaryAnalysisPlan,
    QueryGenerator,
    QuestionStudySearcher,
)


class MockLLMGateway:
    """Small deterministic gateway for CLI and tests that need no external API."""

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
            outcome = plan.get("primary_outcome") or _first(pico.get("outcome")) or "Primary outcome"
            intervention = _first(pico.get("intervention")) or ""
            comparator = _first(pico.get("comparison")) or "control"
            return {
                "analyses": [
                    {
                        "analysis_id": "a1",
                        "outcome": outcome,
                        "outcome_type": "binary",
                        "effect_measure": "RR",
                        "intervention": intervention,
                        "comparator": comparator,
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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run simplified Module 3 analysis.")
    parser.add_argument("--question", required=True)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--index-path", default="data/data_for_test/data_demo_1000/index/local_rct_index.jsonl")
    parser.add_argument("--mock", action="store_true", help="Use deterministic mock LLM outputs.")
    parser.add_argument("--population", action="append", default=[])
    parser.add_argument("--intervention", action="append", default=[])
    parser.add_argument("--comparison", action="append", default=[])
    parser.add_argument("--outcome", action="append", default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.mock:
        raise SystemExit("Only --mock is supported in the simplified CLI smoke path.")
    pico = _pico_from_args(args)
    query = QueryGenerator().generate(population=pico.population, intervention=pico.intervention)
    candidates = QuestionStudySearcher(index_path=Path(args.index_path)).search_from_query_output(query, top_k=args.top_k).studies
    if not candidates:
        candidates = [_mock_candidate(args)]
    result = asyncio.run(
        Module3AnalysisRunner(MockLLMGateway()).run(
            question=args.question,
            pico=pico,
            eligibility_criteria=EligibilityCriteria(inclusion=[], exclusion=[], confidence="low"),
            preliminary_plan=PreliminaryAnalysisPlan(
                primary_outcome=_first(pico.outcome) or "Primary outcome",
                effect_measures={"binary": "RR", "continuous": "MD"},
                confidence="low",
            ),
            candidates=candidates,
        )
    )
    print(json.dumps(result_to_dict(result), ensure_ascii=False, indent=2))
    return 0


def _pico_from_args(args: argparse.Namespace) -> PICO:
    question = args.question.strip()
    return PICO(
        population=args.population or [question],
        intervention=args.intervention or [question],
        comparison=args.comparison or ["control"],
        outcome=args.outcome or ["Primary outcome"],
    )


def _mock_candidate(args: argparse.Namespace) -> CandidateStudy:
    question = args.question.strip()
    return CandidateStudy(
        study_id="mock:module3-study",
        pmid=None,
        pmcid=None,
        title="Synthetic mock study for Module 3 CLI smoke",
        abstract=(
            "Mock RCT abstract for local Module 3 smoke testing. "
            "The intervention group had 5 events among 32 participants, and the control group had 17 events among 32 participants."
        ),
        population=_first(args.population) or question,
        intervention=_first(args.intervention) or question,
        source="mock",
        relevance_score=0.0,
        article_path=None,
    )


def _first(values: Any) -> str | None:
    if not values:
        return None
    return str(values[0])


if __name__ == "__main__":
    raise SystemExit(main())
