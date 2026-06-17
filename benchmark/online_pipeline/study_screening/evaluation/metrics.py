"""Study screening benchmark metrics."""

from __future__ import annotations

from typing import Any


def evaluate(predictions: list[dict[str, Any]], gold_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    tp = fp = fn = tn = 0
    for prediction in predictions:
        instance_id = str(prediction["instance_id"])
        predicted = _normalize_decision(prediction.get("decision"))
        gold = _normalize_decision(gold_by_id[instance_id].get("gold_decision"))
        if gold == "include" and predicted == "include":
            tp += 1
        elif gold == "exclude" and predicted == "include":
            fp += 1
        elif gold == "include" and predicted == "exclude":
            fn += 1
        elif gold == "exclude" and predicted == "exclude":
            tn += 1
        else:
            raise ValueError(f"Unsupported gold/predicted decision pair: {gold!r}, {predicted!r}")

    include_precision, include_recall, include_f1 = _prf(tp, fp, fn)
    exclude_precision, exclude_recall, exclude_f1 = _prf(tn, fn, fp)
    total = tp + fp + fn + tn
    return {
        "instance_count": total,
        "include_precision": include_precision,
        "include_recall": include_recall,
        "include_f1": include_f1,
        "false_negative_count": fn,
        "false_negative_rate": fn / (tp + fn) if tp + fn else 0.0,
        "exclude_recall": exclude_recall,
        "specificity": exclude_recall,
        "accuracy": (tp + tn) / total if total else 0.0,
        "macro_f1": (include_f1 + exclude_f1) / 2,
        "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "exclude_precision": exclude_precision,
        "exclude_f1": exclude_f1,
    }


def _normalize_decision(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in {"include", "exclude"}:
        raise ValueError(f"Decision must be include or exclude, got {value!r}")
    return normalized


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1
