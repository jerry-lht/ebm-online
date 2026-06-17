"""Metrics for Meta Analysis Subtask 4 evaluation."""

from __future__ import annotations

from typing import Any

from benchmark.online_pipeline.meta_analysis.evaluation_common.metrics import _mean


NUMERIC_TOLERANCE = 5e-3


def build_comparisons(predictions: list[dict[str, Any]], gold_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    predictions_by_id = {str(row["instance_id"]): row for row in predictions}
    rows: list[dict[str, Any]] = []
    for instance_id, gold in gold_by_id.items():
        prediction = predictions_by_id.get(instance_id) or {"instance_id": instance_id}
        gold_results = gold.get("subgroup_results") or {}
        pred_results = prediction.get("subgroup_results") or {}
        gold_rows = {str(row.get("subgroup_estimate_id") or ""): row for row in gold_results.get("subgroup_estimates") or []}
        pred_rows = {str(row.get("subgroup_estimate_id") or ""): row for row in pred_results.get("subgroup_estimates") or []}
        for estimate_id, gold_row in gold_rows.items():
            pred_row = pred_rows.get(estimate_id)
            numeric_close = pred_row is not None and all(
                _estimate_close(gold_row.get(field), pred_row.get(field))
                for field in ("effect_value", "ci_lower", "ci_upper")
            )
            rows.append(
                {
                    "instance_id": instance_id,
                    "section": "subgroup_estimates",
                    "key": estimate_id,
                    "covered": pred_row is not None,
                    "numeric_close": numeric_close,
                    "exact_match": pred_row == gold_row,
                }
            )
        gold_tests = {str(row.get("subgroup_difference_test_id") or row.get("test_id") or ""): row for row in gold_results.get("subgroup_difference_tests") or []}
        pred_tests = {str(row.get("subgroup_difference_test_id") or row.get("test_id") or ""): row for row in pred_results.get("subgroup_difference_tests") or []}
        for test_id, gold_row in gold_tests.items():
            pred_row = pred_tests.get(test_id)
            numeric_close = pred_row is not None and all(
                _estimate_close(gold_row.get(field), pred_row.get(field))
                for field in ("chi2", "df", "p_value", "i2_between_subgroups")
            )
            rows.append(
                {
                    "instance_id": instance_id,
                    "section": "subgroup_difference_tests",
                    "key": test_id,
                    "covered": pred_row is not None,
                    "numeric_close": numeric_close,
                    "exact_match": pred_row == gold_row,
                }
            )
    return rows


def evaluate_predictions(predictions: list[dict[str, Any]], gold_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows = build_comparisons(predictions, gold_by_id)
    estimate_rows = [row for row in rows if row["section"] == "subgroup_estimates"]
    test_rows = [row for row in rows if row["section"] == "subgroup_difference_tests"]
    return {
        "instance_count": len(gold_by_id),
        "comparison_count": len(rows),
        "subgroup_estimate_join_rate": _mean([row["covered"] for row in estimate_rows]),
        "subgroup_estimate_numeric_close_rate": _mean([row["numeric_close"] for row in estimate_rows]),
        "subgroup_difference_test_join_rate": _mean([row["covered"] for row in test_rows]),
        "subgroup_difference_test_numeric_close_rate": _mean([row["numeric_close"] for row in test_rows]),
    }


def _estimate_close(gold: Any, prediction: Any) -> bool:
    if gold is None or gold == "":
        return prediction is None or prediction == ""
    try:
        return abs(float(gold) - float(prediction)) <= NUMERIC_TOLERANCE
    except (TypeError, ValueError):
        return str(gold) == str(prediction)
