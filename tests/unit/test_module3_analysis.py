from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass

import pytest

from ebm_backend.online_pipeline.interfaces.cli.evidence_analysis import main as module3_cli_main
from ebm_backend.shared.llm.gateway import LLMGateway, LLMResult
from ebm_backend.shared.llm.tracker import TokenUsage
from ebm_backend.online_pipeline.application.evidence_analysis import (
    AnalysisPlanner,
    AnalysisSpec,
    DataExtractor,
    EvidenceContextBuilder,
    EvidenceContext,
    ExtractedDataRow,
    MetaAnalysisAggregator,
    Module3AnalysisRunner,
    RiskOfBiasAssessor,
    StudyScreener,
)
from ebm_backend.online_pipeline.application.question_study import EligibilityCriteria, PICO, PreliminaryAnalysisPlan


@dataclass(frozen=True)
class _Candidate:
    study_id: str
    title: str
    abstract: str
    article_path: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    population: str | None = None
    intervention: str | None = None
    source: str | None = None
    relevance_score: float = 1.0


class FakeLLMGateway:
    def __init__(self):
        self.calls: list[dict] = []

    async def call(self, **kwargs):
        self.calls.append(kwargs)
        task_type = kwargs["task_type"]
        inputs = kwargs.get("inputs") or {}
        content = self._content(task_type, inputs)
        return LLMResult(
            content=content,
            raw_response=json.dumps(content),
            usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            cached=False,
            latency_ms=0,
            call_id=f"fake-{task_type}",
        )

    def _content(self, task_type: str, inputs: dict) -> dict:
        if task_type == "study_screening":
            candidate = inputs["candidate"]
            include = candidate["study_id"] != "s-exclude"
            return {
                "study_id": candidate["study_id"],
                "title": candidate["title"],
                "included": include,
                "rationale": "Relevant RCT" if include else "Wrong intervention",
                "exclusion_reason": None if include else "wrong_intervention",
            }
        if task_type == "analysis_planning":
            return {
                "analyses": [
                    {
                        "analysis_id": "a1",
                        "outcome": "CRBD incidence at 1 hour",
                        "outcome_type": "binary",
                        "effect_measure": "RR",
                        "intervention": "duloxetine",
                        "comparator": "placebo",
                        "timepoint": "1 hour",
                        "pooling_method": "IV",
                        "model": "fixed",
                        "notes": "Primary analysis",
                    }
                ],
                "warnings": [],
            }
        if task_type == "data_extraction":
            context = inputs["evidence_context"]
            return {
                "study_id": context["study_id"],
                "analysis_id": "a1",
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
                "exp_events": 6,
                "ctrl_events": 18,
                "giv_effect": None,
                "giv_se": None,
                "evidence_spans": ["6 vs 18 patients at 1 hour"],
                "notes": "Visible table values",
            }
        if task_type == "risk_of_bias":
            context = inputs["evidence_context"]
            return {
                "study_id": context["study_id"],
                "domains": [
                    {
                        "domain": "random_sequence_generation",
                        "judgement": "low",
                        "rationale": "Computer-generated random numbers reported.",
                        "evidence": "computer-generated table",
                    }
                ],
                "overall": "unclear",
                "warnings": [],
            }
        if task_type == "grade_assessment":
            aggregation = inputs["aggregation"]
            return {
                "analysis_id": aggregation["analysis_id"],
                "certainty": "low",
                "downgrade_reasons": ["single small study"],
                "rationale": "Mock GRADE output.",
                "warnings": [],
            }
        raise ValueError(task_type)


class _StructuredLLMResponse:
    def __init__(self, content: dict):
        self.output_text = json.dumps(content, ensure_ascii=False)

    def model_dump(self):
        return {
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            }
        }


class _SyntheticRCTResponses:
    def __init__(self):
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        task_type = kwargs["response_format"]["json_schema"]["name"]
        prompt = kwargs["input"]
        return _StructuredLLMResponse(self._content(task_type, prompt))

    def _content(self, task_type: str, prompt: str) -> dict:
        if task_type == "study_screening":
            study_id = _study_id_from_prompt(prompt)
            return {
                "study_id": study_id,
                "title": f"Synthetic RCT {study_id}",
                "included": True,
                "rationale": "Synthetic randomized trial matches PICO and reports event counts.",
                "exclusion_reason": None,
            }
        if task_type == "analysis_planning":
            return {
                "analyses": [
                    {
                        "analysis_id": "crbd_1h_rr",
                        "outcome": "CRBD incidence at 1 hour",
                        "outcome_type": "binary",
                        "effect_measure": "RR",
                        "intervention": "duloxetine",
                        "comparator": "placebo",
                        "timepoint": "1 hour",
                        "pooling_method": "IV",
                        "model": "fixed",
                        "notes": "Synthetic RCTs all report 1-hour event counts.",
                    }
                ],
                "warnings": [],
            }
        if task_type == "data_extraction":
            study_id = _study_id_from_prompt(prompt)
            counts = {
                "rct-1": (5, 100, 20, 100),
                "rct-2": (9, 120, 24, 120),
                "rct-3": (4, 80, 12, 80),
            }[study_id]
            exp_events, exp_n, ctrl_events, ctrl_n = counts
            return {
                "study_id": study_id,
                "analysis_id": "crbd_1h_rr",
                "outcome_type": "binary",
                "effect_measure": "RR",
                "extraction_status": "included",
                "missing_reason": None,
                "exp_mean": None,
                "exp_sd": None,
                "exp_n": exp_n,
                "ctrl_mean": None,
                "ctrl_sd": None,
                "ctrl_n": ctrl_n,
                "exp_events": exp_events,
                "ctrl_events": ctrl_events,
                "giv_effect": None,
                "giv_se": None,
                "evidence_spans": [f"Duloxetine {exp_events}/{exp_n}; placebo {ctrl_events}/{ctrl_n}"],
                "notes": "Extracted from synthetic results table.",
            }
        if task_type == "risk_of_bias":
            study_id = _study_id_from_prompt(prompt)
            return {
                "study_id": study_id,
                "domains": [
                    {
                        "domain": "random_sequence_generation",
                        "judgement": "low",
                        "rationale": "Computer-generated randomization stated.",
                        "evidence": "computer-generated randomization",
                    },
                    {
                        "domain": "allocation_concealment",
                        "judgement": "unclear",
                        "rationale": "Concealment method not fully described.",
                        "evidence": "",
                    },
                ],
                "overall": "unclear",
                "warnings": [],
            }
        if task_type == "grade_assessment":
            return {
                "analysis_id": "crbd_1h_rr",
                "certainty": "moderate",
                "downgrade_reasons": ["Some allocation concealment details were unclear."],
                "rationale": "Three consistent synthetic RCTs with direct binary outcome data.",
                "warnings": [],
            }
        raise ValueError(task_type)


class _SyntheticRCTClient:
    def __init__(self):
        self.responses = _SyntheticRCTResponses()


def _pico() -> PICO:
    return PICO(
        population=["adults undergoing urinary catheterization"],
        intervention=["duloxetine"],
        comparison=["placebo"],
        outcome=["CRBD incidence"],
    )


def _prelim_plan() -> PreliminaryAnalysisPlan:
    return PreliminaryAnalysisPlan(
        primary_outcome="CRBD incidence at 1 hour",
        effect_measures={"binary": "RR", "continuous": "MD"},
        confidence="low",
    )


def _study_id_from_prompt(prompt: str) -> str:
    for study_id in ("rct-1", "rct-2", "rct-3"):
        if study_id in prompt:
            return study_id
    return "unknown"


def _write_synthetic_article(path, *, study_id: str, exp_events: int, exp_n: int, ctrl_events: int, ctrl_n: int) -> None:
    path.write_text(
        json.dumps(
            {
                "metadata": {
                    "pmid": study_id,
                    "title": f"Synthetic RCT {study_id}",
                    "classification": "primary_rct",
                },
                "sections": [
                    {
                        "section_key": "abstract",
                        "section_title_normalized": "Abstract",
                        "blocks": [
                            {
                                "type": "text",
                                "text_md": (
                                    "A randomized placebo-controlled trial tested duloxetine for preventing "
                                    "catheter-related bladder discomfort after urinary catheterization."
                                ),
                            }
                        ],
                    },
                    {
                        "section_key": "methods",
                        "section_title_normalized": "Methods",
                        "blocks": [
                            {
                                "type": "text",
                                "text_md": (
                                    "Participants were randomized using a computer-generated randomization list. "
                                    "Allocation concealment was not fully described."
                                ),
                            }
                        ],
                    },
                    {
                        "section_key": "results",
                        "section_title_normalized": "Results",
                        "blocks": [
                            {
                                "type": "text",
                                "text_md": (
                                    f"At 1 hour, CRBD occurred in {exp_events} of {exp_n} participants in the "
                                    f"duloxetine group and {ctrl_events} of {ctrl_n} participants in the placebo group."
                                ),
                            }
                        ],
                    },
                    {
                        "section_key": "tables",
                        "section_title_normalized": "Tables",
                        "blocks": [
                            {
                                "type": "table",
                                "table_id": f"table-{study_id}",
                                "table_title": "CRBD incidence at 1 hour",
                                "table_caption": "Synthetic extraction table.",
                                "table_text_raw": (
                                    f"Outcome Duloxetine Placebo CRBD at 1 hour {exp_events}/{exp_n} {ctrl_events}/{ctrl_n}"
                                ),
                            }
                        ],
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_screening_include_exclude_split():
    gateway = FakeLLMGateway()
    candidates = [
        _Candidate(study_id="s-include", title="Duloxetine trial", abstract="RCT"),
        _Candidate(study_id="s-exclude", title="Wrong intervention", abstract="RCT"),
    ]
    result = asyncio.run(
        StudyScreener().screen_with_llm(
            gateway,
            question="duloxetine for CRBD?",
            pico=_pico(),
            eligibility_criteria=EligibilityCriteria(),
            candidates=candidates,
        )
    )
    assert len(result.included) == 1
    assert len(result.excluded) == 1
    assert result.excluded[0].exclusion_reason == "wrong_intervention"
    assert all(call["cacheable"] is False for call in gateway.calls)


def test_planning_generates_analysis_list():
    gateway = FakeLLMGateway()
    result = asyncio.run(
        AnalysisPlanner().plan_with_llm(
            gateway,
            question="duloxetine for CRBD?",
            pico=_pico(),
            preliminary_plan=_prelim_plan(),
            included_studies=[_Candidate(study_id="s1", title="Duloxetine trial", abstract="RCT")],
        )
    )
    assert result.analyses[0].analysis_id == "a1"
    assert result.analyses[0].effect_measure == "RR"


def test_extraction_mock_values_enter_aggregation():
    gateway = FakeLLMGateway()
    analysis = AnalysisSpec(
        analysis_id="a1",
        outcome="CRBD incidence at 1 hour",
        outcome_type="binary",
        effect_measure="RR",
    )
    context = EvidenceContext(study_id="s1", title="Duloxetine trial", abstract="RCT results")
    extraction = asyncio.run(
        DataExtractor().extract_with_llm(
            gateway,
            analyses=[analysis],
            evidence_contexts={"s1": context},
        )
    )
    assert extraction.rows[0].exp_events == 6
    aggregation = MetaAnalysisAggregator().aggregate(analyses=[analysis], rows=extraction.rows)
    assert aggregation.analyses[0].study_effects[0].included is True
    assert aggregation.analyses[0].pooled_result is not None
    assert aggregation.analyses[0].pooled_result["study_count"] == 1


def test_rob_auto_adds_selective_reporting():
    gateway = FakeLLMGateway()
    context = EvidenceContext(study_id="s1", title="Duloxetine trial", abstract="RCT results")
    result = asyncio.run(RiskOfBiasAssessor().assess_with_llm(gateway, evidence_contexts={"s1": context}))
    domains = {domain.domain: domain for domain in result.assessments[0].domains}
    assert domains["selective_reporting"].judgement == "unable_to_determine"
    assert domains["random_sequence_generation"].judgement == "low"


def test_module3_runner_complete_flow_and_grade_certainty():
    gateway = FakeLLMGateway()
    result = asyncio.run(
        Module3AnalysisRunner(gateway).run(
            question="Does duloxetine reduce catheter-related bladder discomfort?",
            pico=_pico(),
            eligibility_criteria=EligibilityCriteria(),
            preliminary_plan=_prelim_plan(),
            candidates=[_Candidate(study_id="s1", title="Duloxetine trial", abstract="6 vs 18 events")],
        )
    )
    assert result.screening.included
    assert result.planning.analyses[0].analysis_id == "a1"
    assert result.extraction.rows[0].exp_events == 6
    assert result.aggregation.analyses[0].pooled_result is not None
    assert result.grade.assessments[0].certainty == "low"
    assert [call["task_type"] for call in gateway.calls] == [
        "study_screening",
        "analysis_planning",
        "data_extraction",
        "risk_of_bias",
        "grade_assessment",
    ]


def test_module3_synthetic_rcts_full_flow_through_llm_gateway(tmp_path):
    specs = [
        ("rct-1", 5, 100, 20, 100),
        ("rct-2", 9, 120, 24, 120),
        ("rct-3", 4, 80, 12, 80),
    ]
    candidates = []
    for study_id, exp_events, exp_n, ctrl_events, ctrl_n in specs:
        article_path = tmp_path / f"{study_id}.json"
        _write_synthetic_article(
            article_path,
            study_id=study_id,
            exp_events=exp_events,
            exp_n=exp_n,
            ctrl_events=ctrl_events,
            ctrl_n=ctrl_n,
        )
        candidates.append(
            _Candidate(
                study_id=study_id,
                title=f"Synthetic RCT {study_id}",
                abstract="Synthetic RCT reports CRBD event counts for duloxetine and placebo.",
                article_path=str(article_path),
                population="adults with urinary catheterization",
                intervention="duloxetine",
                source="synthetic",
            )
        )

    client = _SyntheticRCTClient()
    gateway = LLMGateway(conn=None, client=client, model="gpt-test")
    result = asyncio.run(
        Module3AnalysisRunner(gateway).run(
            question="Does duloxetine reduce catheter-related bladder discomfort?",
            pico=_pico(),
            eligibility_criteria=EligibilityCriteria(
                inclusion=["randomized trials in catheterized adults"],
                exclusion=["non-randomized studies"],
                confidence="high",
            ),
            preliminary_plan=_prelim_plan(),
            candidates=candidates,
        )
    )

    assert len(result.screening.included) == 3
    assert result.planning.analyses[0].analysis_id == "crbd_1h_rr"
    assert {row.study_id for row in result.extraction.rows} == {"rct-1", "rct-2", "rct-3"}
    assert [row.exp_events for row in result.extraction.rows] == [5, 9, 4]
    assert result.aggregation.analyses[0].pooled_result is not None
    assert result.aggregation.analyses[0].pooled_result["study_count"] == 3
    assert result.aggregation.analyses[0].pooled_result["effect_original"] < 1.0
    assert result.grade.assessments[0].certainty == "moderate"
    assert all(result.evidence[study_id].full_text_available for study_id, *_ in specs)
    assert all(call["temperature"] == 0.0 for call in client.responses.calls)
    assert len(client.responses.calls) == 11
    assert [call["response_format"]["json_schema"]["name"] for call in client.responses.calls] == [
        "study_screening",
        "study_screening",
        "study_screening",
        "analysis_planning",
        "data_extraction",
        "data_extraction",
        "data_extraction",
        "risk_of_bias",
        "risk_of_bias",
        "risk_of_bias",
        "grade_assessment",
    ]


def test_aggregation_tracks_missing_rows():
    analysis = AnalysisSpec(
        analysis_id="a1",
        outcome="CRBD incidence",
        outcome_type="binary",
        effect_measure="RR",
    )
    row = ExtractedDataRow(
        study_id="s1",
        analysis_id="a1",
        outcome_type="binary",
        effect_measure="RR",
        extraction_status="missing",
        missing_reason="No event counts visible",
    )
    result = MetaAnalysisAggregator().aggregate(analyses=[analysis], rows=[row])
    assert result.analyses[0].pooled_result is None
    assert result.analyses[0].excluded_rows == [row]


def test_evidence_context_builder_reads_article_json(tmp_path):
    article_path = tmp_path / "article.json"
    article_path.write_text(
        json.dumps(
            {
                "metadata": {"title": "Duloxetine trial", "pmid": "1"},
                "sections": [
                    {
                        "section_key": "abstract",
                        "section_title_normalized": "Abstract",
                        "blocks": [{"type": "text", "text_md": "Abstract text"}],
                    },
                    {
                        "section_key": "methods",
                        "section_title_normalized": "Methods",
                        "blocks": [{"type": "text", "text_md": "Randomized double-blind methods"}],
                    },
                    {
                        "section_key": "results",
                        "section_title_normalized": "Results",
                        "blocks": [{"type": "text", "text_md": "Results: 6 vs 18 events"}],
                    },
                    {
                        "section_key": "tables",
                        "section_title_normalized": "Tables",
                        "blocks": [
                            {
                                "type": "table",
                                "table_id": "t1",
                                "table_title": "Events",
                                "table_caption": "Primary table",
                                "table_text_raw": "Duloxetine 6 Control 18",
                            }
                        ],
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    context = EvidenceContextBuilder().build(
        _Candidate(study_id="s1", title="Duloxetine trial", abstract="fallback", article_path=str(article_path))
    )
    assert context.full_text_available is True
    assert context.abstract == "Abstract text"
    assert "Randomized" in context.methods
    assert "6 vs 18" in context.results
    assert context.tables[0]["title"] == "Events"


def test_module3_mock_cli_outputs_full_result(tmp_path, capsys):
    index_path = tmp_path / "index.jsonl"
    index_path.write_text(
        json.dumps(
            {
                "study_id": "s1",
                "pmid": "1",
                "pmcid": "PMC1",
                "title": "Duloxetine catheter-related bladder discomfort trial",
                "abstract": "Duloxetine reduced catheter-related bladder discomfort.",
                "population": "catheter-related bladder discomfort",
                "intervention": "duloxetine",
                "population_original": "catheter-related bladder discomfort",
                "intervention_original": "duloxetine",
                "mesh_terms": [],
                "mesh_population": [],
                "mesh_intervention": [],
                "source": "unit",
                "article_path": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    exit_code = module3_cli_main(
        [
            "--mock",
            "--question",
            "Does duloxetine reduce catheter-related bladder discomfort?",
            "--population",
            "catheter-related bladder discomfort",
            "--intervention",
            "duloxetine",
            "--index-path",
            str(index_path),
            "--top-k",
            "1",
        ]
    )
    assert exit_code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["screening"]["included"][0]["study_id"] == "s1"
    assert out["aggregation"]["analyses"][0]["pooled_result"]["study_count"] == 1
    assert out["grade"]["assessments"][0]["certainty"] == "low"


def test_module3_cli_requires_mock():
    with pytest.raises(SystemExit):
        module3_cli_main(["--question", "Does duloxetine help?", "--top-k", "1"])
