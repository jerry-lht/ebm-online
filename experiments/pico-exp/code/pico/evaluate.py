"""Evaluators for PICO span and BLURB-compatible token predictions."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from pico.conversions import PICO_TO_BLURB, spans_to_blurb_bio_labels
from pico.schemas import DocumentExample, PICO_LABELS, Span

EVALUATOR_VERSION = "phase5-v1"
BLURB_LABELS: tuple[str, ...] = ("O", "I-PAR", "I-INT", "I-OUT")
POSITIVE_BLURB_LABELS: tuple[str, ...] = ("I-PAR", "I-INT", "I-OUT")


@dataclass(frozen=True)
class Counts:
    tp: int = 0
    fp: int = 0
    fn: int = 0


def index_gold_examples(examples: list[DocumentExample]) -> dict[str, DocumentExample]:
    """Index examples by document id, failing on duplicate gold documents."""
    index: dict[str, DocumentExample] = {}
    for example in examples:
        if example.doc_id in index:
            raise ValueError(f"Duplicate gold doc_id: {example.doc_id!r}")
        index[example.doc_id] = example
    return index


def validate_span_predictions(
    gold_by_doc: dict[str, DocumentExample],
    predictions: list[Span],
) -> None:
    for span in predictions:
        example = gold_by_doc.get(span.doc_id)
        if example is None:
            raise ValueError(f"Prediction references unknown doc_id: {span.doc_id!r}")
        if span.end_token > len(example.tokens):
            raise ValueError(
                f"Prediction span {span.doc_id}:{span.start_token}-{span.end_token} "
                f"exceeds {len(example.tokens)} tokens"
            )


def validate_bio_predictions(
    gold_by_doc: dict[str, DocumentExample],
    predictions: dict[str, list[str]],
) -> None:
    for doc_id, labels in predictions.items():
        example = gold_by_doc.get(doc_id)
        if example is None:
            raise ValueError(f"BIO prediction references unknown doc_id: {doc_id!r}")
        if len(labels) != len(example.tokens):
            raise ValueError(
                f"BIO prediction for {doc_id!r} has {len(labels)} labels; "
                f"expected {len(example.tokens)}"
            )
        invalid = sorted(set(labels) - set(BLURB_LABELS))
        if invalid:
            raise ValueError(f"BIO prediction for {doc_id!r} has unsupported labels: {invalid}")


def evaluate_all(
    gold_examples: list[DocumentExample],
    span_predictions: list[Span],
    bio_predictions: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Run all Phase 5 evaluators against a shared gold example set."""
    gold_by_doc = index_gold_examples(gold_examples)
    validate_span_predictions(gold_by_doc, span_predictions)
    if bio_predictions is not None:
        validate_bio_predictions(gold_by_doc, bio_predictions)
    else:
        bio_predictions = _spans_by_doc_to_bio(gold_examples, span_predictions)

    exact_span = evaluate_exact_spans(gold_examples, span_predictions)
    relaxed_span = evaluate_relaxed_spans(gold_examples, span_predictions)
    overlap_subset = evaluate_overlap_subset(gold_examples, span_predictions)
    blurb_token = evaluate_blurb_tokens(gold_examples, bio_predictions)

    return {
        "exact_span": exact_span,
        "relaxed_span": relaxed_span,
        "blurb_token": blurb_token,
        "overlap_subset": overlap_subset,
        "counts": {
            "gold_docs": len(gold_examples),
            "prediction_spans": len(span_predictions),
            "bio_prediction_docs": len(bio_predictions or {}),
        },
        "warnings": [],
    }


def evaluate_exact_spans(
    gold_examples: list[DocumentExample],
    predictions: list[Span],
) -> dict[str, Any]:
    gold_keys = [_span_key(span) for example in gold_examples for span in example.gold_spans]
    pred_keys = [_span_key(span) for span in predictions]
    metrics = _multiset_exact_metrics(gold_keys, pred_keys, PICO_LABELS)

    pred_counter = Counter(pred_keys)
    duplicate_count = sum(count - 1 for count in pred_counter.values() if count > 1)
    metrics["duplicates"] = {
        "count": duplicate_count,
        "rate": _safe_divide(duplicate_count, len(pred_keys)),
    }
    metrics["metadata"] = {
        "match_definition": "Exact match on doc_id, label, start_token, and end_token.",
    }
    return metrics


def evaluate_overlap_subset(
    gold_examples: list[DocumentExample],
    predictions: list[Span],
) -> dict[str, Any]:
    overlap_doc_ids = {
        example.doc_id for example in gold_examples if example.metadata.get("has_overlap") is True
    }
    gold_keys = [
        _span_key(span)
        for example in gold_examples
        if example.doc_id in overlap_doc_ids
        for span in example.gold_spans
    ]
    pred_keys = [_span_key(span) for span in predictions if span.doc_id in overlap_doc_ids]
    metrics = _multiset_exact_metrics(gold_keys, pred_keys, PICO_LABELS)
    metrics["metadata"] = {
        "gold_doc_count": len(overlap_doc_ids),
        "match_definition": "Exact span metrics restricted to gold docs with metadata.has_overlap == true.",
    }
    return metrics


def evaluate_relaxed_spans(
    gold_examples: list[DocumentExample],
    predictions: list[Span],
) -> dict[str, Any]:
    gold_spans = [span for example in gold_examples for span in example.gold_spans]
    by_label: dict[str, Counts] = {}
    for label in PICO_LABELS:
        by_label[label] = _relaxed_counts(
            [span for span in gold_spans if span.label == label],
            [span for span in predictions if span.label == label],
        )

    metrics = _counts_by_label_to_metrics(by_label)
    metrics["metadata"] = {
        "match_definition": (
            "One-to-one greedy match within the same doc_id and label when predicted and gold "
            "token intervals overlap by at least one token; candidates are sorted by descending "
            "overlap token count."
        ),
    }
    return metrics


def evaluate_blurb_tokens(
    gold_examples: list[DocumentExample],
    predictions: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    counts_by_blurb = {label: Counts() for label in POSITIVE_BLURB_LABELS}
    mutable_counts = {label: [0, 0, 0] for label in POSITIVE_BLURB_LABELS}

    for example in gold_examples:
        gold_labels = example.bio_labels
        if len(gold_labels) != len(example.tokens):
            raise ValueError(
                f"Gold BIO labels for {example.doc_id!r} have {len(gold_labels)} labels; "
                f"expected {len(example.tokens)}"
            )
        pred_labels = (predictions or {}).get(example.doc_id, ["O"] * len(example.tokens))
        for gold_label, pred_label in zip(gold_labels, pred_labels, strict=True):
            if gold_label not in BLURB_LABELS:
                raise ValueError(f"Gold BIO label for {example.doc_id!r} is unsupported: {gold_label!r}")
            if pred_label not in BLURB_LABELS:
                raise ValueError(f"Predicted BIO label for {example.doc_id!r} is unsupported: {pred_label!r}")
            for label in POSITIVE_BLURB_LABELS:
                if pred_label == label and gold_label == label:
                    mutable_counts[label][0] += 1
                elif pred_label == label and gold_label != label:
                    mutable_counts[label][1] += 1
                elif pred_label != label and gold_label == label:
                    mutable_counts[label][2] += 1

    for label, values in mutable_counts.items():
        counts_by_blurb[label] = Counts(tp=values[0], fp=values[1], fn=values[2])

    per_label = {label: _metric_dict(counts) for label, counts in counts_by_blurb.items()}
    totals = _sum_counts(counts_by_blurb.values())
    result = _metric_dict(totals)
    result["per_label"] = {
        _blurb_to_pico_name(label): values for label, values in per_label.items()
    }
    result["macro_f1"] = _macro_f1(per_label.values())
    result["metadata"] = {
        "label_space": list(BLURB_LABELS),
        "positive_labels": list(POSITIVE_BLURB_LABELS),
        "primary_f1_excludes_o": True,
        "missing_docs": "Missing prediction docs are treated as all-O predictions.",
    }
    return result


def _spans_by_doc_to_bio(
    gold_examples: list[DocumentExample],
    predictions: list[Span],
) -> dict[str, list[str]]:
    spans_by_doc: dict[str, list[Span]] = defaultdict(list)
    for span in predictions:
        spans_by_doc[span.doc_id].append(span)
    return {
        example.doc_id: spans_to_blurb_bio_labels(spans_by_doc[example.doc_id], len(example.tokens))
        for example in gold_examples
    }


def _multiset_exact_metrics(
    gold_keys: list[tuple[str, str, int, int]],
    pred_keys: list[tuple[str, str, int, int]],
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


def _counts_by_label_to_metrics(counts_by_label: dict[str, Counts]) -> dict[str, Any]:
    per_label = {label: _metric_dict(counts) for label, counts in counts_by_label.items()}
    totals = _sum_counts(counts_by_label.values())
    result = _metric_dict(totals)
    result["per_label"] = per_label
    result["macro_f1"] = _macro_f1(per_label.values())
    return result


def _relaxed_counts(gold_spans: list[Span], pred_spans: list[Span]) -> Counts:
    candidates: list[tuple[int, int, int]] = []
    for pred_index, pred in enumerate(pred_spans):
        for gold_index, gold in enumerate(gold_spans):
            if pred.doc_id != gold.doc_id:
                continue
            overlap = min(pred.end_token, gold.end_token) - max(pred.start_token, gold.start_token)
            if overlap > 0:
                candidates.append((overlap, pred_index, gold_index))

    matched_pred: set[int] = set()
    matched_gold: set[int] = set()
    for _overlap, pred_index, gold_index in sorted(candidates, key=lambda item: (-item[0], item[1], item[2])):
        if pred_index in matched_pred or gold_index in matched_gold:
            continue
        matched_pred.add(pred_index)
        matched_gold.add(gold_index)

    tp = len(matched_gold)
    return Counts(tp=tp, fp=len(pred_spans) - tp, fn=len(gold_spans) - tp)


def _span_key(span: Span) -> tuple[str, str, int, int]:
    return (span.doc_id, span.label, span.start_token, span.end_token)


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
    total_tp = total_fp = total_fn = 0
    for item in counts:
        total_tp += item.tp
        total_fp += item.fp
        total_fn += item.fn
    return Counts(tp=total_tp, fp=total_fp, fn=total_fn)


def _macro_f1(metrics: Any) -> float:
    values = [metric["f1"] for metric in metrics]
    return _safe_divide(sum(values), len(values))


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _blurb_to_pico_name(label: str) -> str:
    reverse = {value: key for key, value in PICO_TO_BLURB.items()}
    return reverse[label]
