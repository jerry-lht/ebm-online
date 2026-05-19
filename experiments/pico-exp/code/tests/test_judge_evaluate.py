from __future__ import annotations

import json

import pytest

from pico.judge_evaluate import build_judge_inputs, parse_judge_response_text, summarize_judge_rows
from pico.prompt_registry import resolve_prompt_path
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


def test_build_judge_inputs_aggregates_gold_and_predictions() -> None:
    inputs, quality = build_judge_inputs(
        [_example()],
        [_raw("d1", [{"label": "P", "text": "alpha"}, {"label": "I", "text": "beta"}])],
    )

    assert len(inputs) == 1
    assert inputs[0].doc_id == "d1"
    assert inputs[0].gold["P"] == ["alpha"]
    assert inputs[0].gold["I"] == ["beta"]
    assert inputs[0].gold["O"] == ["gamma"]
    assert inputs[0].predicted["P"] == ["alpha"]
    assert inputs[0].predicted["I"] == ["beta"]
    assert inputs[0].predicted["O"] == []
    assert quality["raw_rows"] == 1
    assert quality["invalid_rows"] == 0


def test_build_judge_inputs_counts_invalid_rows_and_items() -> None:
    inputs, quality = build_judge_inputs(
        [_example()],
        [
            {"doc_id": "d1", "response": "[not json]"},
            _raw("d1", [{"label": "X", "text": "oops"}, {"label": "P"}]),
        ],
    )

    assert len(inputs) == 1
    assert inputs[0].predicted["P"] == []
    assert quality["invalid_rows"] == 1
    assert quality["response_items"] == 2
    assert quality["invalid_items"] == 2
    assert quality["unknown_label_items"] == 1


def test_parse_judge_response_text_accepts_valid_payload() -> None:
    payload = {
        "labels": {
            "P": {
                "completeness": "complete",
                "accuracy": "accurate",
                "noise": "low",
                "granularity": "appropriate",
                "overall_verdict": "strong",
                "reason": "Prediction covers the participant mentions with little noise.",
            },
            "I": {
                "completeness": "partial",
                "accuracy": "mixed",
                "noise": "medium",
                "granularity": "mixed",
                "overall_verdict": "mixed",
                "reason": "Intervention and comparator are partly captured but one mention is missed.",
            },
            "O": {
                "completeness": "missing",
                "accuracy": "incorrect",
                "noise": "high",
                "granularity": "too_narrow",
                "overall_verdict": "weak",
                "reason": "Outcome content is mostly absent and replaced by irrelevant snippets.",
            },
        },
        "overall": {
            "completeness": "partial",
            "accuracy": "mixed",
            "noise": "medium",
            "granularity": "mixed",
            "overall_verdict": "mixed",
            "reason": "Across labels the extraction is partially complete with mixed correctness.",
        },
    }

    parsed = parse_judge_response_text(json.dumps(payload))
    assert parsed["labels"]["P"]["overall_verdict"] == "strong"
    assert parsed["overall"]["completeness"] == "partial"


def test_parse_judge_response_text_accepts_markdown_wrapped_json() -> None:
    payload = {
        "labels": {
            "P": {
                "completeness": "complete",
                "accuracy": "accurate",
                "noise": "low",
                "granularity": "appropriate",
                "overall_verdict": "strong",
                "reason": "Participant mentions are covered and correctly labeled.",
            },
            "I": {
                "completeness": "complete",
                "accuracy": "accurate",
                "noise": "low",
                "granularity": "appropriate",
                "overall_verdict": "strong",
                "reason": "Intervention and comparator content aligns with gold.",
            },
            "O": {
                "completeness": "partial",
                "accuracy": "mixed",
                "noise": "medium",
                "granularity": "mixed",
                "overall_verdict": "mixed",
                "reason": "Outcome coverage is partial with some extra content.",
            },
        },
        "overall": {
            "completeness": "partial",
            "accuracy": "mixed",
            "noise": "medium",
            "granularity": "mixed",
            "overall_verdict": "mixed",
            "reason": "Overall extraction is partially complete with mixed quality.",
        },
    }
    wrapped = "```json\n" + json.dumps(payload) + "\n```"
    parsed = parse_judge_response_text(wrapped)
    assert parsed["overall"]["overall_verdict"] == "mixed"


def test_parse_judge_response_text_accepts_pio_top_level_shape() -> None:
    payload = {
        "P": {
            "completeness": "complete",
            "accuracy": "accurate",
            "noise": "low",
            "granularity": "appropriate",
            "overall_verdict": "strong",
            "reason": "Participant mentions are covered and correctly labeled.",
        },
        "I": {
            "completeness": "complete",
            "accuracy": "accurate",
            "noise": "low",
            "granularity": "appropriate",
            "overall_verdict": "strong",
            "reason": "Intervention and comparator content aligns with gold.",
        },
        "O": {
            "completeness": "partial",
            "accuracy": "mixed",
            "noise": "medium",
            "granularity": "mixed",
            "overall_verdict": "mixed",
            "reason": "Outcome coverage is partial with some extra content.",
        },
        "overall": {
            "completeness": "partial",
            "accuracy": "mixed",
            "noise": "medium",
            "granularity": "mixed",
            "overall_verdict": "mixed",
            "reason": "Overall extraction is partially complete with mixed quality.",
        },
    }
    parsed = parse_judge_response_text(json.dumps(payload))
    assert parsed["labels"]["P"]["overall_verdict"] == "strong"


def test_parse_judge_response_text_accepts_wrapped_payload_shape() -> None:
    payload = {
        "judge_rubric": {
            "labels": {
                "P": {
                    "completeness": "complete",
                    "accuracy": "accurate",
                    "noise": "low",
                    "granularity": "appropriate",
                    "overall_verdict": "strong",
                    "reason": "Participant mentions are covered and correctly labeled.",
                },
                "I": {
                    "completeness": "complete",
                    "accuracy": "accurate",
                    "noise": "low",
                    "granularity": "appropriate",
                    "overall_verdict": "strong",
                    "reason": "Intervention and comparator content aligns with gold.",
                },
                "O": {
                    "completeness": "partial",
                    "accuracy": "mixed",
                    "noise": "medium",
                    "granularity": "mixed",
                    "overall_verdict": "mixed",
                    "reason": "Outcome coverage is partial with some extra content.",
                },
            },
            "overall": {
                "completeness": "partial",
                "accuracy": "mixed",
                "noise": "medium",
                "granularity": "mixed",
                "overall_verdict": "mixed",
                "reason": "Overall extraction is partially complete with mixed quality.",
            },
        }
    }
    parsed = parse_judge_response_text(json.dumps(payload))
    assert parsed["labels"]["I"]["overall_verdict"] == "strong"


def test_parse_judge_response_text_accepts_overall_nested_inside_labels() -> None:
    payload = {
        "labels": {
            "P": {
                "completeness": "complete",
                "accuracy": "accurate",
                "noise": "low",
                "granularity": "appropriate",
                "overall_verdict": "strong",
                "reason": "Participant mentions are covered and correctly labeled.",
            },
            "I": {
                "completeness": "complete",
                "accuracy": "accurate",
                "noise": "low",
                "granularity": "appropriate",
                "overall_verdict": "strong",
                "reason": "Intervention and comparator content aligns with gold.",
            },
            "O": {
                "completeness": "partial",
                "accuracy": "mixed",
                "noise": "medium",
                "granularity": "mixed",
                "overall_verdict": "mixed",
                "reason": "Outcome coverage is partial with some extra content.",
            },
            "overall": {
                "completeness": "partial",
                "accuracy": "mixed",
                "noise": "medium",
                "granularity": "mixed",
                "overall_verdict": "mixed",
                "reason": "Overall extraction is partially complete with mixed quality.",
            },
        }
    }
    parsed = parse_judge_response_text(json.dumps(payload))
    assert parsed["labels"]["P"]["overall_verdict"] == "strong"
    assert parsed["overall"]["overall_verdict"] == "mixed"


def test_parse_judge_response_text_accepts_prose_wrapped_json() -> None:
    payload = {
        "labels": {
            "P": {
                "completeness": "complete",
                "accuracy": "accurate",
                "noise": "low",
                "granularity": "appropriate",
                "overall_verdict": "strong",
                "reason": "Participant mentions are covered and correctly labeled.",
            },
            "I": {
                "completeness": "complete",
                "accuracy": "accurate",
                "noise": "low",
                "granularity": "appropriate",
                "overall_verdict": "strong",
                "reason": "Intervention and comparator content aligns with gold.",
            },
            "O": {
                "completeness": "partial",
                "accuracy": "mixed",
                "noise": "medium",
                "granularity": "mixed",
                "overall_verdict": "mixed",
                "reason": "Outcome coverage is partial with some extra content.",
            },
        },
        "overall": {
            "completeness": "partial",
            "accuracy": "mixed",
            "noise": "medium",
            "granularity": "mixed",
            "overall_verdict": "mixed",
            "reason": "Overall extraction is partially complete with mixed quality.",
        },
    }
    wrapped = "Here is the evaluation:\n" + json.dumps(payload) + "\nDone."
    parsed = parse_judge_response_text(wrapped)
    assert parsed["overall"]["overall_verdict"] == "mixed"


def test_parse_judge_response_text_rejects_invalid_enum() -> None:
    payload = {
        "labels": {
            "P": {
                "completeness": "complete",
                "accuracy": "accurate",
                "noise": "low",
                "granularity": "appropriate",
                "overall_verdict": "excellent",
                "reason": "ok",
            },
            "I": {
                "completeness": "complete",
                "accuracy": "accurate",
                "noise": "low",
                "granularity": "appropriate",
                "overall_verdict": "strong",
                "reason": "ok",
            },
            "O": {
                "completeness": "complete",
                "accuracy": "accurate",
                "noise": "low",
                "granularity": "appropriate",
                "overall_verdict": "strong",
                "reason": "ok",
            },
        },
        "overall": {
            "completeness": "complete",
            "accuracy": "accurate",
            "noise": "low",
            "granularity": "appropriate",
            "overall_verdict": "strong",
            "reason": "ok",
        },
    }

    with pytest.raises(ValueError, match="overall_verdict"):
        parse_judge_response_text(json.dumps(payload))


def test_summarize_judge_rows_counts_and_rates() -> None:
    rows = [
        {
            "doc_id": "d1",
            "labels": {
                "P": {
                    "completeness": "complete",
                    "accuracy": "accurate",
                    "noise": "low",
                    "granularity": "appropriate",
                    "overall_verdict": "strong",
                    "reason": "x",
                },
                "I": {
                    "completeness": "partial",
                    "accuracy": "mixed",
                    "noise": "medium",
                    "granularity": "mixed",
                    "overall_verdict": "mixed",
                    "reason": "x",
                },
                "O": {
                    "completeness": "missing",
                    "accuracy": "incorrect",
                    "noise": "high",
                    "granularity": "too_narrow",
                    "overall_verdict": "weak",
                    "reason": "x",
                },
            },
            "overall": {
                "completeness": "partial",
                "accuracy": "mixed",
                "noise": "medium",
                "granularity": "mixed",
                "overall_verdict": "mixed",
                "reason": "x",
            },
            "metadata": {},
        },
        {
            "doc_id": "d2",
            "labels": {
                "P": {
                    "completeness": "partial",
                    "accuracy": "mixed",
                    "noise": "medium",
                    "granularity": "too_broad",
                    "overall_verdict": "mixed",
                    "reason": "x",
                },
                "I": {
                    "completeness": "complete",
                    "accuracy": "accurate",
                    "noise": "low",
                    "granularity": "appropriate",
                    "overall_verdict": "strong",
                    "reason": "x",
                },
                "O": {
                    "completeness": "complete",
                    "accuracy": "accurate",
                    "noise": "low",
                    "granularity": "appropriate",
                    "overall_verdict": "strong",
                    "reason": "x",
                },
            },
            "overall": {
                "completeness": "complete",
                "accuracy": "accurate",
                "noise": "low",
                "granularity": "appropriate",
                "overall_verdict": "strong",
                "reason": "x",
            },
            "metadata": {},
        },
    ]

    summary = summarize_judge_rows(rows)
    assert summary["counts"]["documents"] == 2
    assert summary["per_label"]["P"]["completeness"]["complete"]["count"] == 1
    assert summary["per_label"]["P"]["completeness"]["partial"]["rate"] == 0.5
    assert summary["overall"]["overall_verdict"]["mixed"]["count"] == 1
    assert summary["overall"]["overall_verdict"]["strong"]["count"] == 1


def test_judge_prompt_version_resolves_from_staged_directory() -> None:
    assert resolve_prompt_path("judge_rubric_v2").parts[-2] == "stage_rubric"
