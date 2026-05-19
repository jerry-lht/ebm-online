from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path

import pytest

from ebm_backend.shared.llm.gateway import LLMGateway
from ebm_backend.online_pipeline.application.evidence_analysis.models import ExtractedDataRow
from ebm_backend.online_pipeline.application.evidence_analysis import AnalysisSpec, DataExtractor, EvidenceContextBuilder, MetaAnalysisAggregator, Module3AnalysisRunner
from ebm_backend.online_pipeline.application.question_study import EligibilityCriteria, PICO, PreliminaryAnalysisPlan


@dataclass(frozen=True)
class _Candidate:
    study_id: str
    title: str
    abstract: str
    article_path: str
    pmid: str | None = None
    pmcid: str | None = None
    population: str | None = None
    intervention: str | None = None
    source: str | None = "synthetic"
    relevance_score: float = 1.0


@pytest.mark.skipif(
    os.getenv("RUN_REAL_LLM") != "1",
    reason="Set RUN_REAL_LLM=1 to run the real external LLM smoke test.",
)
def test_module3_real_llm_extracts_synthetic_rct_counts(tmp_path: Path):
    specs = [
        ("real-rct-1", 5, 100, 20, 100),
        ("real-rct-2", 9, 120, 24, 120),
        ("real-rct-3", 4, 80, 12, 80),
    ]
    candidates = []
    for study_id, exp_events, exp_n, ctrl_events, ctrl_n in specs:
        article_path = tmp_path / f"{study_id}.json"
        _write_synthetic_article(article_path, study_id, exp_events, exp_n, ctrl_events, ctrl_n)
        candidates.append(
            _Candidate(
                study_id=study_id,
                title=f"Synthetic randomized trial {study_id}",
                abstract=(
                    f"At 1 hour, catheter-related bladder discomfort occurred in {exp_events}/{exp_n} "
                    f"duloxetine participants and {ctrl_events}/{ctrl_n} placebo participants."
                ),
                article_path=str(article_path),
                population="adults undergoing urinary catheterization",
                intervention="duloxetine",
            )
        )

    gateway = LLMGateway(conn=None)
    result = asyncio.run(
        Module3AnalysisRunner(gateway).run(
            question="Does duloxetine reduce catheter-related bladder discomfort compared with placebo?",
            pico=PICO(
                population=["adults undergoing urinary catheterization"],
                intervention=["duloxetine"],
                comparison=["placebo"],
                outcome=["catheter-related bladder discomfort incidence at 1 hour"],
            ),
            eligibility_criteria=EligibilityCriteria(
                inclusion=["parallel-group randomized trials", "reports 1-hour CRBD event counts"],
                exclusion=["non-randomized studies", "does not compare duloxetine with placebo"],
                confidence="high",
            ),
            preliminary_plan=PreliminaryAnalysisPlan(
                primary_outcome="catheter-related bladder discomfort incidence at 1 hour",
                effect_measures={"binary": "RR", "continuous": "MD"},
                confidence="high",
            ),
            candidates=candidates,
        )
    )

    assert len(result.screening.included) == 3
    expected = {
        "real-rct-1": (5, 100, 20, 100),
        "real-rct-2": (9, 120, 24, 120),
        "real-rct-3": (4, 80, 12, 80),
    }
    target_rows = _rows_matching_expected_counts(result.extraction.rows, expected)
    assert len(target_rows) == 3, result.extraction.rows
    for row in target_rows:
        assert row.extraction_status == "included", row
        assert (row.exp_events, row.exp_n, row.ctrl_events, row.ctrl_n) == expected[row.study_id]
    target_analysis_id = target_rows[0].analysis_id
    target_aggregation = next(
        analysis for analysis in result.aggregation.analyses if analysis.analysis_id == target_analysis_id
    )
    assert target_aggregation.pooled_result is not None
    assert target_aggregation.pooled_result["study_count"] == 3
    assert target_aggregation.pooled_result["effect_original"] < 1.0
    assert any(assessment.analysis_id == target_analysis_id for assessment in result.grade.assessments)


@pytest.mark.skipif(
    os.getenv("RUN_REAL_LLM") != "1",
    reason="Set RUN_REAL_LLM=1 to run the real external LLM smoke test.",
)
def test_module3_real_llm_extraction_only_synthetic_rcts(tmp_path: Path):
    specs = [
        ("real-rct-1", 5, 100, 20, 100),
        ("real-rct-2", 9, 120, 24, 120),
        ("real-rct-3", 4, 80, 12, 80),
    ]
    contexts = {}
    for study_id, exp_events, exp_n, ctrl_events, ctrl_n in specs:
        article_path = tmp_path / f"{study_id}.json"
        _write_synthetic_article(article_path, study_id, exp_events, exp_n, ctrl_events, ctrl_n)
        context = EvidenceContextBuilder().build(
            _Candidate(
                study_id=study_id,
                title=f"Synthetic randomized trial {study_id}",
                abstract="",
                article_path=str(article_path),
            )
        )
        contexts[context.study_id] = context

    analysis = AnalysisSpec(
        analysis_id="crbd_rr",
        outcome="catheter-related bladder discomfort incidence at 1 hour",
        outcome_type="binary",
        effect_measure="RR",
        intervention="duloxetine",
        comparator="placebo",
        timepoint="1 hour",
    )
    extraction = asyncio.run(
        DataExtractor().extract_with_llm(
            LLMGateway(conn=None),
            analyses=[analysis],
            evidence_contexts=contexts,
        )
    )

    expected = {
        "real-rct-1": (5, 100, 20, 100),
        "real-rct-2": (9, 120, 24, 120),
        "real-rct-3": (4, 80, 12, 80),
    }
    assert extraction.warnings == []
    for row in extraction.rows:
        assert row.extraction_status == "included", row
        assert (row.exp_events, row.exp_n, row.ctrl_events, row.ctrl_n) == expected[row.study_id]

    aggregation = MetaAnalysisAggregator().aggregate(analyses=[analysis], rows=extraction.rows)
    assert aggregation.analyses[0].pooled_result is not None
    assert aggregation.analyses[0].pooled_result["study_count"] == 3
    assert aggregation.analyses[0].pooled_result["effect_original"] < 1.0


def _write_synthetic_article(
    path: Path,
    study_id: str,
    exp_events: int,
    exp_n: int,
    ctrl_events: int,
    ctrl_n: int,
) -> None:
    path.write_text(
        json.dumps(
            {
                "metadata": {
                    "pmid": study_id,
                    "title": f"Synthetic randomized trial {study_id}",
                    "classification": "primary_rct",
                },
                "xml_content": {
                    "sections": [
                        {
                            "section": "Abstract",
                            "text": (
                                "This parallel-group randomized placebo-controlled trial tested duloxetine "
                                "for preventing catheter-related bladder discomfort after urinary catheterization."
                            ),
                        },
                        {
                            "section": "Methods",
                            "text": (
                                "Adults undergoing elective surgery with urinary catheterization were randomized "
                                "1:1 to oral duloxetine or matching placebo using a computer-generated sequence. "
                                "Outcome assessors were blinded."
                            ),
                        },
                        {
                            "section": "Results",
                            "text": (
                                f"At 1 hour, catheter-related bladder discomfort occurred in {exp_events} of "
                                f"{exp_n} participants assigned to duloxetine and {ctrl_events} of {ctrl_n} "
                                "participants assigned to placebo."
                            ),
                        },
                    ],
                    "tables": [
                        {
                            "section_path": ["Results"],
                            "raw_xml": (
                                f"<table-wrap id=\"table-{study_id}\">"
                                "<label>Table 1</label>"
                                "<caption><p>Catheter-related bladder discomfort at 1 hour</p></caption>"
                                "<table><tbody>"
                                "<tr><td>Outcome</td><td>Duloxetine</td><td>Placebo</td></tr>"
                                f"<tr><td>CRBD at 1 hour</td><td>{exp_events}/{exp_n}</td><td>{ctrl_events}/{ctrl_n}</td></tr>"
                                "</tbody></table></table-wrap>"
                            ),
                        }
                    ],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _rows_matching_expected_counts(
    rows: list[ExtractedDataRow],
    expected: dict[str, tuple[int, int, int, int]],
) -> list[ExtractedDataRow]:
    matching = [
        row
        for row in rows
        if row.study_id in expected
        and (row.exp_events, row.exp_n, row.ctrl_events, row.ctrl_n) == expected[row.study_id]
    ]
    by_analysis: dict[str, list[ExtractedDataRow]] = {}
    for row in matching:
        by_analysis.setdefault(row.analysis_id, []).append(row)
    for analysis_rows in by_analysis.values():
        if {row.study_id for row in analysis_rows} == set(expected):
            return analysis_rows
    return []
