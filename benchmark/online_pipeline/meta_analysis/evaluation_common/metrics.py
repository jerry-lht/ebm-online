"""Metrics for Meta Analysis Subtask 2/3/4/5 evaluation."""

from __future__ import annotations

from typing import Any


NUMERIC_TOLERANCE = 1e-6


def evaluate_predictions(predictions: list[dict[str, Any]], gold_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    comparisons = build_comparisons(predictions=predictions, gold_by_id=gold_by_id)
    subtask2_rows = [row for row in comparisons if row["section"] == "study_result_rows"]
    subtask3_rows = [row for row in comparisons if row["section"] == "analysis_methods"]
    subtask4_rows = [row for row in comparisons if row["section"] == "subgroup_results"]
    subtask5_rows = [row for row in comparisons if row["section"] == "overall_estimates"]
    return {
        "instance_count": len(gold_by_id),
        "comparison_count": len(comparisons),
        "subtask2_comparison_count": len(subtask2_rows),
        "subtask2_exact_row_rate": _mean([row["exact_match"] for row in subtask2_rows]),
        "subtask2_numeric_close_rate": _mean([row["numeric_close"] for row in subtask2_rows]),
        "subtask3_comparison_count": len(subtask3_rows),
        "subtask3_method_exact_rate": _mean([row["exact_match"] for row in subtask3_rows]),
        "subtask4_comparison_count": len(subtask4_rows),
        "subtask4_subgroup_join_rate": _mean([row["covered"] for row in subtask4_rows]),
        "subtask4_estimate_exact_or_close_rate": _mean([row["numeric_close"] for row in subtask4_rows]),
        "subtask5_comparison_count": len(subtask5_rows),
        "subtask5_overall_join_rate": _mean([row["covered"] for row in subtask5_rows]),
        "subtask5_estimate_exact_or_close_rate": _mean([row["numeric_close"] for row in subtask5_rows]),
    }


def build_comparisons(predictions: list[dict[str, Any]], gold_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    predictions_by_id = {str(row["instance_id"]): row for row in predictions}
    rows: list[dict[str, Any]] = []
    for instance_id, gold in gold_by_id.items():
        prediction = predictions_by_id.get(instance_id) or {"instance_id": instance_id}
        rows.extend(_study_result_row_comparisons(instance_id=instance_id, gold=gold, prediction=prediction))
        rows.extend(_analysis_method_comparisons(instance_id=instance_id, gold=gold, prediction=prediction))
        rows.extend(_subgroup_result_comparisons(instance_id=instance_id, gold=gold, prediction=prediction))
        rows.extend(_overall_estimate_comparisons(instance_id=instance_id, gold=gold, prediction=prediction))
    return rows


def _study_result_row_comparisons(*, instance_id: str, gold: dict[str, Any], prediction: dict[str, Any]) -> list[dict[str, Any]]:
    gold_rows = {str(row.get("row_id") or ""): row for row in gold.get("study_result_rows") or []}
    pred_rows = {str(row.get("row_id") or ""): row for row in prediction.get("study_result_rows") or []}
    rows = []
    for row_id, gold_row in gold_rows.items():
        pred_row = pred_rows.get(row_id)
        exact_match = pred_row == gold_row
        numeric_close = pred_row is not None and _result_data_close(gold_row.get("result_data") or {}, pred_row.get("result_data") or {})
        rows.append(
            {
                "instance_id": instance_id,
                "section": "study_result_rows",
                "key": row_id,
                "covered": pred_row is not None,
                "exact_match": exact_match,
                "numeric_close": numeric_close,
            }
        )
    return rows


def _analysis_method_comparisons(*, instance_id: str, gold: dict[str, Any], prediction: dict[str, Any]) -> list[dict[str, Any]]:
    gold_rows = {str(row.get("setting_id") or ""): row for row in gold.get("analysis_methods") or []}
    pred_rows = {str(row.get("setting_id") or ""): row for row in prediction.get("analysis_methods") or []}
    rows = []
    fields = ("effect_measure", "analysis_model", "statistical_method", "ci_level")
    for setting_id, gold_row in gold_rows.items():
        pred_row = pred_rows.get(setting_id)
        exact_match = pred_row is not None and all(str(pred_row.get(field) or "") == str(gold_row.get(field) or "") for field in fields)
        rows.append(
            {
                "instance_id": instance_id,
                "section": "analysis_methods",
                "key": setting_id,
                "covered": pred_row is not None,
                "exact_match": exact_match,
                "numeric_close": exact_match,
            }
        )
    return rows


def _subgroup_result_comparisons(*, instance_id: str, gold: dict[str, Any], prediction: dict[str, Any]) -> list[dict[str, Any]]:
    gold_results = gold.get("subgroup_results") or {}
    pred_results = prediction.get("subgroup_results") or {}
    gold_rows = {str(row.get("subgroup_estimate_id") or ""): row for row in gold_results.get("subgroup_estimates") or []}
    pred_rows = {str(row.get("subgroup_estimate_id") or ""): row for row in pred_results.get("subgroup_estimates") or []}
    rows = []
    for estimate_id, gold_row in gold_rows.items():
        pred_row = pred_rows.get(estimate_id)
        numeric_close = pred_row is not None and all(
            _value_close(gold_row.get(field), pred_row.get(field))
            for field in ("effect_value", "ci_lower", "ci_upper")
        )
        rows.append(
            {
                "instance_id": instance_id,
                "section": "subgroup_results",
                "key": estimate_id,
                "covered": pred_row is not None,
                "exact_match": pred_row == gold_row,
                "numeric_close": numeric_close,
            }
        )
    return rows


def _overall_estimate_comparisons(*, instance_id: str, gold: dict[str, Any], prediction: dict[str, Any]) -> list[dict[str, Any]]:
    gold_rows = {str(row.get("overall_estimate_id") or ""): row for row in gold.get("overall_estimates") or []}
    pred_rows = {str(row.get("overall_estimate_id") or ""): row for row in prediction.get("overall_estimates") or []}
    rows = []
    for estimate_id, gold_row in gold_rows.items():
        pred_row = pred_rows.get(estimate_id)
        numeric_close = pred_row is not None and all(
            _value_close(gold_row.get(field), pred_row.get(field))
            for field in ("effect_value", "ci_lower", "ci_upper")
        )
        rows.append(
            {
                "instance_id": instance_id,
                "section": "overall_estimates",
                "key": estimate_id,
                "covered": pred_row is not None,
                "exact_match": pred_row == gold_row,
                "numeric_close": numeric_close,
            }
        )
    return rows


def _result_data_close(gold: dict[str, Any], prediction: dict[str, Any]) -> bool:
    if set(gold) != set(prediction):
        return False
    return all(_value_close(gold.get(field), prediction.get(field)) for field in gold)


def _value_close(gold: Any, prediction: Any) -> bool:
    if gold is None or gold == "":
        return prediction is None or prediction == ""
    try:
        return abs(float(gold) - float(prediction)) <= NUMERIC_TOLERANCE
    except (TypeError, ValueError):
        return str(gold) == str(prediction)


def _mean(values: list[bool]) -> float:
    return sum(1 for value in values if value) / len(values) if values else 0.0
