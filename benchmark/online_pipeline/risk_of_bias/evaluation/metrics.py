"""Classification metrics for Risk of Bias evaluation."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


LABELS = ("low_risk", "unclear_risk", "high_risk")
DOMAIN_IDS = (
    "random_sequence_generation",
    "allocation_concealment",
    "blinding_participants_personnel",
    "blinding_outcome_assessment",
    "incomplete_outcome_data",
    "selective_reporting",
    "other_bias",
)


def evaluate_comparisons(rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid_rows = [row for row in rows if row.get("valid_prediction")]
    covered_rows = [row for row in rows if row.get("covered")]
    total = len(rows)
    correct = sum(1 for row in valid_rows if row.get("match"))
    metrics: dict[str, Any] = {
        "instance_count": len({str(row.get("instance_id") or "") for row in rows}),
        "comparison_count": total,
        "valid_prediction_count": len(valid_rows),
        "covered_count": len(covered_rows),
        "accuracy": correct / len(valid_rows) if valid_rows else 0.0,
        "domain_coverage_rate": len(covered_rows) / total if total else 0.0,
        "high_risk_recall": _label_recall(valid_rows, "high_risk"),
    }
    label_f1s = [_label_f1(valid_rows, label) for label in _active_labels(valid_rows)]
    metrics["macro_f1"] = _mean(label_f1s)

    per_domain: dict[str, Any] = {}
    domain_macro_f1_values = []
    for domain_id in DOMAIN_IDS:
        domain_rows = [row for row in rows if row.get("domain_id") == domain_id]
        valid_domain_rows = [row for row in domain_rows if row.get("valid_prediction")]
        domain_label_f1s = [_label_f1(valid_domain_rows, label) for label in _active_labels(valid_domain_rows)]
        domain_metrics = {
            "comparison_count": len(domain_rows),
            "covered_count": sum(1 for row in domain_rows if row.get("covered")),
            "valid_prediction_count": len(valid_domain_rows),
            "accuracy": _accuracy(valid_domain_rows),
            "macro_f1": _mean(domain_label_f1s),
            "coverage_rate": (sum(1 for row in domain_rows if row.get("covered")) / len(domain_rows)) if domain_rows else 0.0,
            "confusion": _confusion(valid_domain_rows),
        }
        per_domain[domain_id] = domain_metrics
        domain_macro_f1_values.append(domain_metrics["macro_f1"])
    metrics["domain_macro_f1"] = _mean(domain_macro_f1_values)
    metrics["per_domain"] = per_domain
    metrics["confusion"] = _confusion(valid_rows)
    return metrics


def _accuracy(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if row.get("match")) / len(rows)


def _label_recall(rows: list[dict[str, Any]], label: str) -> float:
    positives = [row for row in rows if row.get("gold_judgement") == label]
    if not positives:
        return 0.0
    return sum(1 for row in positives if row.get("predicted_judgement") == label) / len(positives)


def _label_f1(rows: list[dict[str, Any]], label: str) -> float:
    tp = sum(1 for row in rows if row.get("gold_judgement") == label and row.get("predicted_judgement") == label)
    fp = sum(1 for row in rows if row.get("gold_judgement") != label and row.get("predicted_judgement") == label)
    fn = sum(1 for row in rows if row.get("gold_judgement") == label and row.get("predicted_judgement") != label)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0


def _active_labels(rows: list[dict[str, Any]]) -> list[str]:
    active = {
        str(row.get("gold_judgement") or "")
        for row in rows
        if str(row.get("gold_judgement") or "") in LABELS
    }
    active.update(
        str(row.get("predicted_judgement") or "")
        for row in rows
        if str(row.get("predicted_judgement") or "") in LABELS
    )
    return [label for label in LABELS if label in active]


def _confusion(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    matrix: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        matrix[str(row.get("gold_judgement") or "missing")][str(row.get("predicted_judgement") or "missing")] += 1
    return {gold: dict(sorted(preds.items())) for gold, preds in sorted(matrix.items())}


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
