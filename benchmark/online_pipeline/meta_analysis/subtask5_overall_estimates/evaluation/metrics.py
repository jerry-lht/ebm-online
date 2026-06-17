"""Metrics for Meta Analysis Subtask 5 evaluation."""

from __future__ import annotations

from typing import Any

from benchmark.online_pipeline.meta_analysis.evaluation_common.metrics import _mean


NUMERIC_TOLERANCE = 5e-3


def build_comparisons(predictions: list[dict[str, Any]], gold_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    predictions_by_id = {str(row["instance_id"]): row for row in predictions}
    rows: list[dict[str, Any]] = []
    for instance_id, gold in gold_by_id.items():
        prediction = predictions_by_id.get(instance_id) or {"instance_id": instance_id}
        gold_rows = {str(row.get("overall_estimate_id") or ""): row for row in gold.get("overall_estimates") or []}
        pred_rows = {str(row.get("overall_estimate_id") or ""): row for row in prediction.get("overall_estimates") or []}
        for estimate_id, gold_row in gold_rows.items():
            pred_row = pred_rows.get(estimate_id)
            numeric_close = pred_row is not None and all(
                _estimate_close(gold_row.get(field), pred_row.get(field))
                for field in ("effect_value", "ci_lower", "ci_upper")
            )
            rows.append(
                {
                    "instance_id": instance_id,
                    "key": estimate_id,
                    "covered": pred_row is not None,
                    "numeric_close": numeric_close,
                    "exact_match": pred_row == gold_row,
                }
            )
    return rows


def evaluate_predictions(predictions: list[dict[str, Any]], gold_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows = build_comparisons(predictions, gold_by_id)
    return {
        "instance_count": len(gold_by_id),
        "comparison_count": len(rows),
        "overall_join_rate": _mean([row["covered"] for row in rows]),
        "overall_numeric_close_rate": _mean([row["numeric_close"] for row in rows]),
    }


def _estimate_close(gold: Any, prediction: Any) -> bool:
    if gold is None or gold == "":
        return prediction is None or prediction == ""
    try:
        return abs(float(gold) - float(prediction)) <= NUMERIC_TOLERANCE
    except (TypeError, ValueError):
        return str(gold) == str(prediction)
