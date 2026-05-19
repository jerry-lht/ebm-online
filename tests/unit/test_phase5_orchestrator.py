from __future__ import annotations

import json

import pytest

from ebm_backend.online_pipeline.application.run_pipeline import PipelineOrchestrator, SimplifiedPipelineMockGateway
from ebm_backend.online_pipeline.infrastructure.pipeline_repository import InMemoryPipelineStore, PipelineStatus


@pytest.mark.asyncio
async def test_phase5_orchestrator_records_module2_and_module3_trace(tmp_path):
    index_path = _index_path(tmp_path)
    store = InMemoryPipelineStore()
    run = await PipelineOrchestrator(store=store, index_path=index_path).run_question(
        question="Does duloxetine reduce catheter-related bladder discomfort?",
        top_k=3,
        use_mock=True,
    )

    assert run.status == PipelineStatus.COMPLETED
    assert run.result is not None
    step_names = [step.name for step in run.steps]
    assert step_names == [
        "question_expansion",
        "question_pi_extraction",
        "query_generation",
        "local_search",
        "module3_screening",
        "module3_planning",
        "module3_extraction",
        "module3_rob",
        "module3_aggregation",
        "module3_grade",
        "module3_analysis",
    ]

    query_step = next(step for step in run.steps if step.name == "query_generation")
    assert "boolean_query" in query_step.payload
    assert "duloxetine" in query_step.payload["boolean_query"].lower()

    search_step = next(step for step in run.steps if step.name == "local_search")
    assert search_step.payload["returned_count"] == 1
    assert search_step.payload["studies"][0]["study_id"] == "pmid:37877838"

    module3_step = next(step for step in run.steps if step.name == "module3_analysis")
    for key in ["screening", "planning", "extraction", "aggregation", "grade"]:
        assert key in module3_step.payload
    assert module3_step.payload["screening"]["included"]
    assert module3_step.payload["extraction"]["rows"]
    assert run.result["query"]["boolean_query"]
    assert run.result["risk_of_bias"]["assessments"]
    assert run.result["aggregation"]["analyses"]


@pytest.mark.asyncio
async def test_phase5_real_mode_no_hits_does_not_inject_synthetic_candidate(tmp_path, monkeypatch):
    index_path = tmp_path / "local_rct_index.jsonl"
    index_path.write_text("", encoding="utf-8")
    store = InMemoryPipelineStore()
    monkeypatch.setattr(PipelineOrchestrator, "_real_gateway", staticmethod(lambda: SimplifiedPipelineMockGateway()))

    run = await PipelineOrchestrator(store=store, index_path=index_path).run_question(
        question="Does duloxetine reduce catheter-related bladder discomfort?",
        top_k=3,
        use_mock=False,
    )

    assert run.status == PipelineStatus.COMPLETED
    assert run.result is not None
    assert run.result["candidates"] == []
    assert run.result["screening"]["included"] == []
    assert run.result["risk_of_bias"]["assessments"] == []


def _index_path(tmp_path):
    path = tmp_path / "local_rct_index.jsonl"
    doc = {
        "study_id": "pmid:37877838",
        "pmid": "37877838",
        "pmcid": "PMC1",
        "title": "Duloxetine reduces catheter-related bladder discomfort",
        "abstract": "Randomized trial of duloxetine for catheter related bladder discomfort after urinary catheterization.",
        "population": "catheter-related bladder discomfort",
        "intervention": "duloxetine",
        "source": "PMC",
        "article_path": None,
    }
    path.write_text(json.dumps(doc) + "\n", encoding="utf-8")
    return path
