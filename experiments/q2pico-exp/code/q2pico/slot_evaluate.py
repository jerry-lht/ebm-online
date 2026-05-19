"""Exact and normalized slot evaluation for Question-to-PICO predictions."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from q2pico.schemas import PICO_LABELS, QuestionPICOExample, SlotPrediction

SLOT_EVALUATOR_VERSION = "question-slot-evaluator-v1"


@dataclass(frozen=True)
class Counts:
    tp: int = 0
    fp: int = 0
    fn: int = 0


def evaluate_slot_predictions(
    examples: list[QuestionPICOExample],
    predictions: list[SlotPrediction],
    *,
    labels: tuple[str, ...] = PICO_LABELS,
) -> dict[str, Any]:
    gold_exact = [
        _text_key(example.question_id, label, value, normalized=False)
        for example in examples
        for label, values in example.gold_slots.items()
        if label in labels
        for value in values
    ]
    gold_normalized = [
        _text_key(example.question_id, label, value, normalized=True)
        for example in examples
        for label, values in example.gold_slots.items()
        if label in labels
        for value in values
    ]
    predictions_by_id = {row.question_id: row for row in predictions}
    pred_exact = [
        _text_key(question_id, label, value, normalized=False)
        for question_id, row in predictions_by_id.items()
        for label, values in row.slots.items()
        if label in labels
        for value in values
    ]
    pred_normalized = [
        _text_key(question_id, label, value, normalized=True)
        for question_id, row in predictions_by_id.items()
        for label, values in row.slots.items()
        if label in labels
        for value in values
    ]

    exact = _multiset_metrics(gold_exact, pred_exact, labels=labels)
    normalized = _multiset_metrics(gold_normalized, pred_normalized, labels=labels)
    completeness = _completeness(examples, predictions_by_id, labels=labels)
    return {
        "slot_evaluator_version": SLOT_EVALUATOR_VERSION,
        "slot_exact": {
            **exact,
            "metadata": {"match_definition": "Multiset exact match on question_id, label, and raw text."},
        },
        "slot_normalized": {
            **normalized,
            "metadata": {
                "match_definition": "Multiset match on question_id, label, and conservatively normalized text.",
                "normalization": "strip, casefold, collapse whitespace, normalize common dash characters",
            },
        },
        "pico_completeness": completeness,
        "counts": {
            "gold_questions": len(examples),
            "prediction_questions": len(predictions_by_id),
        },
        "labels": list(labels),
    }


def normalize_text(text: str) -> str:
    normalized = text.strip().casefold()
    normalized = normalized.replace("\u2010", "-").replace("\u2011", "-").replace("\u2012", "-")
    normalized = normalized.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _text_key(question_id: str, label: str, text: str, *, normalized: bool) -> tuple[str, str, str]:
    return (question_id, label, normalize_text(text) if normalized else text)


def _multiset_metrics(
    gold_keys: list[tuple[str, str, str]],
    pred_keys: list[tuple[str, str, str]],
    *,
    labels: tuple[str, ...],
) -> dict[str, Any]:
    gold_counter = Counter(gold_keys)
    pred_counter = Counter(pred_keys)
    all_keys = set(gold_counter) | set(pred_counter)
    by_label: dict[str, Counts] = {}
    for label in labels:
        tp = fp = fn = 0
        for key in all_keys:
            if key[1] != label:
                continue
            gold_count = gold_counter[key]
            pred_count = pred_counter[key]
            tp += min(gold_count, pred_count)
            fp += max(0, pred_count - gold_count)
            fn += max(0, gold_count - pred_count)
        by_label[label] = Counts(tp=tp, fp=fp, fn=fn)
    return _counts_by_label_to_metrics(by_label)


def _completeness(
    examples: list[QuestionPICOExample],
    predictions_by_id: dict[str, SlotPrediction],
    *,
    labels: tuple[str, ...],
) -> dict[str, Any]:
    label_questions_with_gold = {label: 0 for label in labels}
    label_questions_complete = {label: 0 for label in labels}
    questions_with_any_gold = 0
    complete_questions = 0

    for example in examples:
        predicted = predictions_by_id.get(example.question_id)
        question_complete = True
        has_any_gold = False
        for label in labels:
            gold_values = {normalize_text(value) for value in example.gold_slots[label]}
            if not gold_values:
                continue
            has_any_gold = True
            label_questions_with_gold[label] += 1
            predicted_values = {
                normalize_text(value)
                for value in (predicted.slots[label] if predicted is not None else [])
            }
            matched = all(value in predicted_values for value in gold_values)
            if matched:
                label_questions_complete[label] += 1
            else:
                question_complete = False
        if has_any_gold:
            questions_with_any_gold += 1
            if question_complete:
                complete_questions += 1

    return {
        "per_label": {
            label: {
                "questions_with_gold": label_questions_with_gold[label],
                "complete_questions": label_questions_complete[label],
                "complete_rate": _safe_divide(
                    label_questions_complete[label], label_questions_with_gold[label]
                ),
            }
            for label in labels
        },
        "questions_with_any_gold": questions_with_any_gold,
        "complete_questions": complete_questions,
        "pico_complete_question_rate": _safe_divide(complete_questions, questions_with_any_gold),
        "metadata": {
            "definition": (
                "A label/question is complete when every distinct normalized gold value for that label "
                "appears in the prediction."
            ),
        },
    }


def _counts_by_label_to_metrics(counts_by_label: dict[str, Counts]) -> dict[str, Any]:
    per_label = {label: _metric_dict(counts) for label, counts in counts_by_label.items()}
    totals = _sum_counts(counts_by_label.values())
    result = _metric_dict(totals)
    result["per_label"] = per_label
    result["macro_f1"] = _safe_divide(sum(metric["f1"] for metric in per_label.values()), len(per_label))
    return result


def _metric_dict(counts: Counts) -> dict[str, Any]:
    precision = _safe_divide(counts.tp, counts.tp + counts.fp)
    recall = _safe_divide(counts.tp, counts.tp + counts.fn)
    return {
        "precision": precision,
        "recall": recall,
        "f1": _safe_divide(2 * precision * recall, precision + recall),
        "tp": counts.tp,
        "fp": counts.fp,
        "fn": counts.fn,
    }


def _sum_counts(counts: Any) -> Counts:
    tp = fp = fn = 0
    for item in counts:
        tp += item.tp
        fp += item.fp
        fn += item.fn
    return Counts(tp=tp, fp=fp, fn=fn)


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator
