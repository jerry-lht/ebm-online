"""Metrics for Meta Analysis Subtask 2 evaluation."""

from __future__ import annotations

from typing import Any

from benchmark.online_pipeline.meta_analysis.evaluation_common.metrics import _result_data_close, _mean


def build_comparisons(predictions: list[dict[str, Any]], gold_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    predictions_by_id = {str(row["instance_id"]): row for row in predictions}
    rows: list[dict[str, Any]] = []
    for instance_id, gold in gold_by_id.items():
        prediction = predictions_by_id.get(instance_id) or {"instance_id": instance_id}
        unmatched_predictions = list(prediction.get("study_result_rows") or [])
        for gold_row in gold.get("study_result_rows") or []:
            key = _semantic_row_key(gold_row)
            match_index = next(
                (
                    index
                    for index, pred_row in enumerate(unmatched_predictions)
                    if _semantic_row_key(pred_row) == key
                ),
                None,
            )
            pred_row = unmatched_predictions.pop(match_index) if match_index is not None else None
            rows.append(
                {
                    "instance_id": instance_id,
                    "key": key,
                    "covered": pred_row is not None,
                    "exact_match": pred_row == gold_row,
                    "numeric_close": pred_row is not None
                    and _result_data_close(gold_row.get("result_data") or {}, pred_row.get("result_data") or {}),
                }
            )
    return rows


def evaluate_predictions(predictions: list[dict[str, Any]], gold_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows = build_comparisons(predictions, gold_by_id)
    return {
        "instance_count": len(gold_by_id),
        "comparison_count": len(rows),
        "exact_row_rate": _mean([row["exact_match"] for row in rows]),
        "numeric_close_rate": _mean([row["numeric_close"] for row in rows]),
        "row_join_rate": _mean([row["covered"] for row in rows]),
    }


def _semantic_row_key(row: dict[str, Any]) -> str:
    comparison = row.get("comparison") or {}
    outcome = row.get("outcome") or {}
    subgroup = row.get("subgroup") or {}
    return "||".join(
        [
            str(row.get("study_id") or ""),
            str(row.get("data_type") or ""),
            str(comparison.get("experimental_arm") or ""),
            str(comparison.get("control_arm") or ""),
            str(outcome.get("label") or ""),
            str(outcome.get("timepoint") or ""),
            str(subgroup.get("level") or ""),
            str(subgroup.get("subgroup_number") or ""),
            str(subgroup.get("source") or ""),
        ]
    )
