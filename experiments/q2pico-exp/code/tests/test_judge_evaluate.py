from __future__ import annotations

import json

from q2pico.judge_evaluate import (
    build_judge_inputs,
    parse_judge_response_text,
    summarize_judge_rows,
    summarize_judge_rows_for_labels,
)
from q2pico.schemas import QuestionPICOExample, SlotPrediction


def _example() -> QuestionPICOExample:
    return QuestionPICOExample(
        question_id="q1",
        split="test59",
        question_text="Question text",
        gold_slots={"P": ["Adults"], "I": ["Drug A"], "C": ["Placebo"], "O": ["Stroke"]},
    )


def _prediction() -> SlotPrediction:
    return SlotPrediction(
        question_id="q1",
        slots={"P": ["Adults"], "I": ["Drug A"], "C": ["Placebo"], "O": ["Stroke"]},
    )


def test_build_judge_inputs_uses_question_text_and_four_labels() -> None:
    rows = build_judge_inputs([_example()], [_prediction()])
    assert len(rows) == 1
    assert rows[0].question_text == "Question text"
    assert rows[0].gold["C"] == ["Placebo"]


def test_build_judge_inputs_can_limit_to_pi_labels() -> None:
    rows = build_judge_inputs([_example()], [_prediction()], labels=("P", "I"))
    assert len(rows) == 1
    assert set(rows[0].gold) == {"P", "I"}
    assert set(rows[0].predicted) == {"P", "I"}


def test_parse_judge_response_text_accepts_wrapped_json() -> None:
    payload = {
        "labels": {
            label: {
                "completeness": "complete",
                "accuracy": "accurate",
                "noise": "low",
                "granularity": "appropriate",
                "overall_verdict": "strong",
                "reason": "Matches the gold slot.",
            }
            for label in ("P", "I", "C", "O")
        },
        "overall": {
            "completeness": "complete",
            "accuracy": "accurate",
            "noise": "low",
            "granularity": "appropriate",
            "overall_verdict": "strong",
            "reason": "Overall match is strong.",
        },
    }
    parsed = parse_judge_response_text("```json\n" + json.dumps(payload) + "\n```")
    assert parsed["labels"]["C"]["overall_verdict"] == "strong"


def test_summarize_judge_rows_outputs_distributions() -> None:
    row = {
        "question_id": "q1",
        "labels": {
            label: {
                "completeness": "complete",
                "accuracy": "accurate",
                "noise": "low",
                "granularity": "appropriate",
                "overall_verdict": "strong",
                "reason": "Matches.",
            }
            for label in ("P", "I", "C", "O")
        },
        "overall": {
            "completeness": "complete",
            "accuracy": "accurate",
            "noise": "low",
            "granularity": "appropriate",
            "overall_verdict": "strong",
            "reason": "Matches overall.",
        },
    }
    summary = summarize_judge_rows([row])
    assert summary["counts"]["questions"] == 1
    assert summary["per_label"]["P"]["accuracy"]["accurate"]["count"] == 1


def test_summarize_judge_rows_for_pi_scope_only() -> None:
    row = {
        "question_id": "q1",
        "labels": {
            label: {
                "completeness": "complete",
                "accuracy": "accurate",
                "noise": "low",
                "granularity": "appropriate",
                "overall_verdict": "strong",
                "reason": "Matches.",
            }
            for label in ("P", "I")
        },
        "overall": {
            "completeness": "complete",
            "accuracy": "accurate",
            "noise": "low",
            "granularity": "appropriate",
            "overall_verdict": "strong",
            "reason": "Matches overall.",
        },
    }
    summary = summarize_judge_rows_for_labels([row], labels=("P", "I"))
    assert summary["labels"] == ["P", "I"]
    assert set(summary["per_label"]) == {"P", "I"}
