from __future__ import annotations

import json

import pytest

from pico.cli.evaluate_llm_judge import main
from pico.io_utils import write_document_examples, write_jsonl
from pico.schemas import DocumentExample, Span


def _example(doc_id: str = "d1") -> DocumentExample:
    return DocumentExample(
        doc_id=doc_id,
        split="test",
        abstract="alpha beta gamma",
        tokens=["alpha", "beta", "gamma"],
        token_offsets=[(0, 5), (6, 10), (11, 16)],
        gold_spans=[
            Span(doc_id=doc_id, label="P", text="alpha", start_token=0, end_token=1, char_start=0, char_end=5),
            Span(doc_id=doc_id, label="I", text="beta", start_token=1, end_token=2, char_start=6, char_end=10),
            Span(doc_id=doc_id, label="O", text="gamma", start_token=2, end_token=3, char_start=11, char_end=16),
        ],
        bio_labels=["I-PAR", "I-INT", "I-OUT"],
    )


def _raw(doc_id: str, items: object) -> dict[str, object]:
    return {"doc_id": doc_id, "response": json.dumps(items), "metadata": {}}


def _mock_judge_row(doc_id: str) -> dict[str, object]:
    label = {
        "completeness": "complete",
        "accuracy": "accurate",
        "noise": "low",
        "granularity": "appropriate",
        "overall_verdict": "strong",
        "reason": "Predicted mentions align with gold for this label.",
    }
    return {
        "doc_id": doc_id,
        "labels": {"P": label, "I": label, "O": label},
        "overall": {
            "completeness": "complete",
            "accuracy": "accurate",
            "noise": "low",
            "granularity": "appropriate",
            "overall_verdict": "strong",
            "reason": "Predictions align well with gold across labels.",
        },
        "metadata": {
            "judge_model": "test-model",
            "judge_prompt_version": "judge_rubric_v2",
            "api_mode": "responses",
            "provider": "openai",
            "base_url": "https://api.openai.com/v1",
        },
    }


def test_cli_writes_judge_jsonl_summary_and_tables(tmp_path, monkeypatch) -> None:
    gold_path = tmp_path / "gold.jsonl"
    raw_path = tmp_path / "raw.jsonl"
    output_path = tmp_path / "judge.jsonl"
    summary_path = tmp_path / "judge_metrics.json"
    tables_dir = tmp_path / "tables"
    write_document_examples(gold_path, [_example()])
    write_jsonl(raw_path, [_raw("d1", [{"label": "P", "text": "alpha"}])])

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_run_llm_judge(judge_inputs, **kwargs):
        assert len(judge_inputs) == 1
        assert judge_inputs[0].doc_id == "d1"
        assert kwargs["model_id"] == "test-model"
        return [_mock_judge_row("d1")]

    monkeypatch.setattr("pico.cli.evaluate_llm_judge.run_llm_judge", fake_run_llm_judge)

    assert (
        main(
            [
                "--gold",
                str(gold_path),
                "--raw",
                str(raw_path),
                "--model-id",
                "test-model",
                "--output",
                str(output_path),
                "--summary-output",
                str(summary_path),
                "--tables-dir",
                str(tables_dir),
                "--method",
                "m",
                "--setting",
                "s",
                "--split",
                "test",
            ]
        )
        == 0
    )

    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert len(rows) == 1
    assert rows[0]["doc_id"] == "d1"
    assert summary["counts"]["documents"] == 1
    assert summary["per_label"]["P"]["overall_verdict"]["strong"]["count"] == 1
    assert (tables_dir / "llm_judge_per_label.csv").exists()
    assert (tables_dir / "llm_judge_overall.csv").exists()

    with pytest.raises(ValueError, match="pass --force"):
        main(
            [
                "--gold",
                str(gold_path),
                "--raw",
                str(raw_path),
                "--model-id",
                "test-model",
                "--output",
                str(output_path),
                "--summary-output",
                str(summary_path),
                "--tables-dir",
                str(tables_dir),
                "--method",
                "m",
                "--setting",
                "s",
                "--split",
                "test",
            ]
        )


def test_cli_resume_skips_completed_docs(tmp_path, monkeypatch) -> None:
    gold_path = tmp_path / "gold.jsonl"
    raw_path = tmp_path / "raw.jsonl"
    output_path = tmp_path / "judge.jsonl"
    summary_path = tmp_path / "judge_metrics.json"
    write_document_examples(gold_path, [_example("d1"), _example("d2")])
    write_jsonl(raw_path, [_raw("d1", []), _raw("d2", [])])
    write_jsonl(output_path, [_mock_judge_row("d1")])

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_run_llm_judge(judge_inputs, **kwargs):
        assert [item.doc_id for item in judge_inputs] == ["d2"]
        return [_mock_judge_row("d2")]

    monkeypatch.setattr("pico.cli.evaluate_llm_judge.run_llm_judge", fake_run_llm_judge)

    assert (
        main(
            [
                "--gold",
                str(gold_path),
                "--raw",
                str(raw_path),
                "--model-id",
                "test-model",
                "--output",
                str(output_path),
                "--summary-output",
                str(summary_path),
                "--resume",
            ]
        )
        == 0
    )

    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert [row["doc_id"] for row in rows] == ["d1", "d2"]


def test_cli_writes_partial_results_before_raising_on_failures(tmp_path, monkeypatch) -> None:
    gold_path = tmp_path / "gold.jsonl"
    raw_path = tmp_path / "raw.jsonl"
    output_path = tmp_path / "judge.jsonl"
    summary_path = tmp_path / "judge_metrics.json"
    write_document_examples(gold_path, [_example("d1"), _example("d2")])
    write_jsonl(raw_path, [_raw("d1", []), _raw("d2", [])])

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_run_llm_judge(judge_inputs, **kwargs):
        return [_mock_judge_row("d1")], [{"doc_id": "d2", "error_type": "ValueError", "message": "boom"}]

    monkeypatch.setattr("pico.cli.evaluate_llm_judge.run_llm_judge", fake_run_llm_judge)

    with pytest.raises(RuntimeError, match="LLM judge failed for 1 documents"):
        main(
            [
                "--gold",
                str(gold_path),
                "--raw",
                str(raw_path),
                "--model-id",
                "test-model",
                "--output",
                str(output_path),
                "--summary-output",
                str(summary_path),
            ]
        )

    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert [row["doc_id"] for row in rows] == ["d1"]
    assert summary["counts"]["failed_rows"] == 1
    assert summary["failures"][0]["doc_id"] == "d2"


def test_cli_force_overwrites_existing_rows(tmp_path, monkeypatch) -> None:
    gold_path = tmp_path / "gold.jsonl"
    raw_path = tmp_path / "raw.jsonl"
    output_path = tmp_path / "judge.jsonl"
    summary_path = tmp_path / "judge_metrics.json"
    tables_dir = tmp_path / "tables"
    write_document_examples(gold_path, [_example()])
    write_jsonl(raw_path, [_raw("d1", [])])

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_run_llm_judge(judge_inputs, **kwargs):
        return [_mock_judge_row("d1")]

    monkeypatch.setattr("pico.cli.evaluate_llm_judge.run_llm_judge", fake_run_llm_judge)

    assert (
        main(
            [
                "--gold",
                str(gold_path),
                "--raw",
                str(raw_path),
                "--model-id",
                "test-model",
                "--output",
                str(output_path),
                "--summary-output",
                str(summary_path),
                "--tables-dir",
                str(tables_dir),
                "--method",
                "m",
                "--setting",
                "s",
                "--split",
                "test",
            ]
        )
        == 0
    )

    assert (
        main(
            [
                "--gold",
                str(gold_path),
                "--raw",
                str(raw_path),
                "--model-id",
                "test-model",
                "--output",
                str(output_path),
                "--summary-output",
                str(summary_path),
                "--tables-dir",
                str(tables_dir),
                "--method",
                "m",
                "--setting",
                "s",
                "--split",
                "test",
                "--force",
            ]
        )
        == 0
    )
