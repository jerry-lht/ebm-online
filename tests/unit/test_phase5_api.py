from __future__ import annotations

import json
import time

from fastapi.testclient import TestClient

from ebm_backend.online_pipeline.interfaces.api.main import create_app
from ebm_backend.online_pipeline.infrastructure.pipeline_repository import DEFAULT_PIPELINE_STORE


def test_phase5_api_creates_run_and_exposes_trace(tmp_path):
    index_path = _index_path(tmp_path)
    client = TestClient(create_app())

    response = client.post(
        "/pipeline/runs",
        json={
            "question": "Does duloxetine reduce catheter-related bladder discomfort?",
            "top_k": 3,
            "use_mock": True,
            "index_path": str(index_path),
        },
    )

    assert response.status_code == 200
    created = response.json()
    assert created["status"] in {"pending", "running", "completed"}
    run_id = created["run_id"]

    body = None
    for _ in range(20):
        trace = client.get(f"/pipeline/runs/{run_id}/trace")
        assert trace.status_code == 200
        body = trace.json()
        if body["run"]["status"] == "completed":
            break
        time.sleep(0.05)
    assert body is not None
    assert body["run"]["status"] == "completed"

    assert [step["name"] for step in body["steps"]] == [
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
    assert body["result"]["query"]["boolean_query"]
    assert body["result"]["candidates"]
    assert body["result"]["extraction"]["rows"]
    assert body["result"]["grade"]["assessments"]

    result = client.get(f"/pipeline/runs/{run_id}/results")
    assert result.status_code == 200
    result_body = result.json()["result"]
    assert result_body["aggregation"]["analyses"]
    assert result_body["risk_of_bias"]["assessments"]


def test_phase5_api_defaults_to_real_mode_and_1000_index():
    DEFAULT_PIPELINE_STORE._runs.clear()
    client = TestClient(create_app())

    response = client.post(
        "/pipeline/runs",
        json={
            "question": "not a clinical topic",
        },
    )

    assert response.status_code == 200
    created = response.json()
    assert created["use_mock"] is False
    assert created["index_path"] == "data/data_for_test/data_demo_1000/index/local_rct_index.jsonl"


def test_phase5_api_returns_404_for_unknown_run():
    client = TestClient(create_app())
    response = client.get("/pipeline/runs/not-found")
    assert response.status_code == 404


def _index_path(tmp_path):
    path = tmp_path / "local_rct_index.jsonl"
    doc = {
        "study_id": "pmid:37877838",
        "pmid": "37877838",
        "pmcid": "PMC1",
        "title": "Duloxetine catheter-related bladder discomfort trial",
        "abstract": "Adults with catheter related bladder discomfort received duloxetine or placebo.",
        "population": "catheter-related bladder discomfort",
        "intervention": "duloxetine",
        "source": "PMC",
        "article_path": None,
    }
    path.write_text(json.dumps(doc) + "\n", encoding="utf-8")
    DEFAULT_PIPELINE_STORE._runs.clear()
    return path
