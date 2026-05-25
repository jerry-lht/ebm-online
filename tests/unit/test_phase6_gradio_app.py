from __future__ import annotations

import json
from pathlib import Path

from frontend.gradio_app import DEFAULT_QUESTION, _outputs_from_run, _run_view_from_trace, build_app, run_pipeline


def test_phase6_gradio_mock_callback_returns_trace_and_tables(tmp_path):
    index_path = _index_path(tmp_path)

    outputs = run_pipeline(
        DEFAULT_QUESTION,
        DEFAULT_QUESTION,
        1,
        True,
        str(index_path),
    )
    staged_outputs = list(outputs)
    first_outputs = staged_outputs[0]
    outputs = staged_outputs[-1]

    assert len(outputs) == 20
    assert len(staged_outputs) >= 2
    assert "Running" in first_outputs[0]
    answer_markdown = outputs[0]
    candidate_html = outputs[9]
    extraction_html = outputs[13]
    trace = outputs[17]
    trace_file = Path(outputs[18])

    assert "Completed" in answer_markdown
    assert "Duloxetine catheter-related bladder discomfort trial" in candidate_html
    assert "<table" in candidate_html
    assert "<table" in extraction_html
    assert trace["status"] == "completed"
    assert [step["name"] for step in trace["steps"]] == [
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
    assert trace["result"]["candidates"]
    assert trace["result"]["extraction"]["rows"]
    assert trace_file.exists()
    assert json.loads(trace_file.read_text(encoding="utf-8"))["run_id"] == trace["run_id"]


def test_phase6_gradio_empty_question_does_not_run_pipeline():
    outputs = list(run_pipeline("", "", 1, True, ""))[0]

    assert outputs[17]["status"] == "not_started"
    assert outputs[18] is None
    assert "Enter a clinical question" in outputs[0]


def test_phase6_gradio_staged_trace_uses_module3_substep_payloads():
    trace = {
        "run_id": "run-staged",
        "status": "running",
        "question": DEFAULT_QUESTION,
        "top_k": 1,
        "use_mock": False,
        "index_path": "/tmp/index.jsonl",
        "steps": [
            {"name": "question_expansion", "status": "completed", "summary": "expanded", "payload": {}},
            {"name": "question_pi_extraction", "status": "completed", "summary": "pi", "payload": {}},
            {"name": "query_generation", "status": "completed", "summary": "query", "payload": {}},
            {"name": "local_search", "status": "completed", "summary": "retrieved", "payload": {"studies": []}},
            {
                "name": "module3_screening",
                "status": "completed",
                "summary": "screening done",
                "payload": {"decisions": [{"study_id": "s1", "title": "Trial 1", "included": True}]},
            },
            {
                "name": "module3_planning",
                "status": "completed",
                "summary": "planning done",
                "payload": {"analyses": [{"analysis_id": "a1", "outcome": "CRBD", "outcome_type": "binary", "effect_measure": "RR"}]},
            },
            {
                "name": "module3_extraction",
                "status": "completed",
                "summary": "extraction done",
                "payload": {
                    "rows": [
                        {
                            "study_id": "s1",
                            "analysis_id": "a1",
                            "outcome_type": "binary",
                            "effect_measure": "RR",
                            "extraction_status": "included",
                            "exp_events": 6,
                            "exp_n": 32,
                            "ctrl_events": 18,
                            "ctrl_n": 32,
                            "notes": "visible before module3_analysis",
                        }
                    ]
                },
            },
            {"name": "module3_rob", "status": "running", "summary": "rob running", "payload": {}},
            {"name": "module3_aggregation", "status": "pending", "summary": "", "payload": {}},
            {"name": "module3_grade", "status": "pending", "summary": "", "payload": {}},
            {"name": "module3_analysis", "status": "pending", "summary": "", "payload": {}},
        ],
        "result": None,
    }

    run = _run_view_from_trace(trace)
    outputs = _outputs_from_run(run, elapsed=5.0, trace_path=None)
    timeline_html = outputs[2]
    extraction_html = outputs[13]

    assert "Data extraction" in timeline_html
    assert "completed" in timeline_html
    assert "Risk of bias" in timeline_html
    assert "running" in timeline_html
    assert "visible before module3_analysis" in extraction_html
    assert "Waiting for extraction rows." not in extraction_html


def test_phase6_gradio_blocks_app_builds():
    app = build_app()

    assert app.blocks


def test_phase6_gradio_defaults_to_real_llm_mode():
    app = build_app()
    use_mock = next(block for block in app.blocks.values() if getattr(block, "label", None) == "Use mock LLM")

    assert use_mock.value is False


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
    return path
