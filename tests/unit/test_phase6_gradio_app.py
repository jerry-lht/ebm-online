from __future__ import annotations

import json
from pathlib import Path

from frontend.gradio_app import DEFAULT_QUESTION, build_app, run_pipeline


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

    assert len(outputs) == 17
    assert len(staged_outputs) >= 2
    assert "Running" in first_outputs[0]
    answer_markdown = outputs[0]
    candidate_html = outputs[8]
    extraction_html = outputs[10]
    trace = outputs[14]
    trace_file = Path(outputs[15])

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
        "module3_analysis",
    ]
    assert trace["result"]["candidates"]
    assert trace["result"]["extraction"]["rows"]
    assert trace_file.exists()
    assert json.loads(trace_file.read_text(encoding="utf-8"))["run_id"] == trace["run_id"]


def test_phase6_gradio_empty_question_does_not_run_pipeline():
    outputs = list(run_pipeline("", "", 1, True, ""))[0]

    assert outputs[14]["status"] == "not_started"
    assert outputs[15] is None
    assert "Enter a clinical question" in outputs[0]


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
