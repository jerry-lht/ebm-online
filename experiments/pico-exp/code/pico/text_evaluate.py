"""Text/content evaluators for LLM PICO extraction."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from pico.schemas import DocumentExample, PICO_LABELS

TEXT_EVALUATOR_VERSION = "phase8-text-v1"


@dataclass(frozen=True)
class Counts:
    tp: int = 0
    fp: int = 0
    fn: int = 0


def evaluate_text_predictions(
    examples: list[DocumentExample],
    raw_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate raw LLM text predictions against gold span texts."""
    gold_exact = [_text_key(example.doc_id, span.label, span.text, normalized=False) for example in examples for span in example.gold_spans]
    gold_normalized = [
        _text_key(example.doc_id, span.label, span.text, normalized=True)
        for example in examples
        for span in example.gold_spans
    ]
    pred_exact, pred_normalized, parse_quality = _prediction_keys(raw_rows)

    exact = _multiset_metrics(gold_exact, pred_exact)
    normalized = _multiset_metrics(gold_normalized, pred_normalized)
    completeness = _completeness(examples, set(pred_normalized))
    return {
        "text_evaluator_version": TEXT_EVALUATOR_VERSION,
        "text_exact": {
            **exact,
            "metadata": {"match_definition": "Multiset exact match on doc_id, label, and raw text."},
        },
        "text_normalized": {
            **normalized,
            "metadata": {
                "match_definition": "Multiset match on doc_id, label, and conservatively normalized text.",
                "normalization": "strip, casefold, collapse whitespace, normalize common dash characters",
            },
        },
        "pio_completeness": completeness,
        "prediction_quality": parse_quality,
    }


def normalize_text(text: str) -> str:
    normalized = text.strip().casefold()
    normalized = normalized.replace("\u2010", "-").replace("\u2011", "-").replace("\u2012", "-")
    normalized = normalized.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _prediction_keys(raw_rows: list[dict[str, Any]]) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]], dict[str, Any]]:
    exact_keys: list[tuple[str, str, str]] = []
    normalized_keys: list[tuple[str, str, str]] = []
    invalid_rows = 0
    invalid_items = 0
    response_items = 0
    unknown_label_items = 0

    for row in raw_rows:
        doc_id = row.get("doc_id")
        response = row.get("response")
        if not isinstance(doc_id, str) or not isinstance(response, str):
            invalid_rows += 1
            continue
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            invalid_rows += 1
            continue
        if not isinstance(parsed, list):
            invalid_rows += 1
            continue
        for item in parsed:
            response_items += 1
            if not isinstance(item, dict):
                invalid_items += 1
                continue
            label = item.get("label")
            text = item.get("text")
            if not isinstance(label, str) or not isinstance(text, str):
                invalid_items += 1
                continue
            if label not in PICO_LABELS:
                invalid_items += 1
                unknown_label_items += 1
                continue
            exact_keys.append(_text_key(doc_id, label, text, normalized=False))
            normalized_keys.append(_text_key(doc_id, label, text, normalized=True))

    return exact_keys, normalized_keys, {
        "raw_rows": len(raw_rows),
        "invalid_rows": invalid_rows,
        "response_items": response_items,
        "invalid_items": invalid_items,
        "unknown_label_items": unknown_label_items,
    }


def _text_key(doc_id: str, label: str, text: str, normalized: bool) -> tuple[str, str, str]:
    return (doc_id, label, normalize_text(text) if normalized else text)


def _multiset_metrics(
    gold_keys: list[tuple[str, str, str]],
    pred_keys: list[tuple[str, str, str]],
) -> dict[str, Any]:
    gold_counter = Counter(gold_keys)
    pred_counter = Counter(pred_keys)
    all_keys = set(gold_counter) | set(pred_counter)
    by_label: dict[str, Counts] = {}
    for label in PICO_LABELS:
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


def _completeness(examples: list[DocumentExample], pred_normalized_keys: set[tuple[str, str, str]]) -> dict[str, Any]:
    label_docs_with_gold = {label: 0 for label in PICO_LABELS}
    label_docs_complete = {label: 0 for label in PICO_LABELS}
    pio_gold_docs = 0
    pio_complete_docs = 0

    for example in examples:
        doc_complete_for_all_gold_labels = True
        doc_has_any_gold = False
        for label in PICO_LABELS:
            gold_texts = {
                normalize_text(span.text)
                for span in example.gold_spans
                if span.label == label
            }
            if not gold_texts:
                continue
            doc_has_any_gold = True
            label_docs_with_gold[label] += 1
            matched = all((example.doc_id, label, text) in pred_normalized_keys for text in gold_texts)
            if matched:
                label_docs_complete[label] += 1
            else:
                doc_complete_for_all_gold_labels = False
        if doc_has_any_gold:
            pio_gold_docs += 1
            if doc_complete_for_all_gold_labels:
                pio_complete_docs += 1

    per_label = {
        label: {
            "docs_with_gold": label_docs_with_gold[label],
            "complete_docs": label_docs_complete[label],
            "complete_rate": _safe_divide(label_docs_complete[label], label_docs_with_gold[label]),
        }
        for label in PICO_LABELS
    }
    return {
        "per_label": per_label,
        "docs_with_any_pio_gold": pio_gold_docs,
        "pio_complete_docs": pio_complete_docs,
        "pio_complete_document_rate": _safe_divide(pio_complete_docs, pio_gold_docs),
        "metadata": {
            "definition": "A label/doc is complete when every distinct normalized gold text for that label is predicted.",
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
