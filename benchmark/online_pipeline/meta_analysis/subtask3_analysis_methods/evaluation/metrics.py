"""Metrics for Meta Analysis Subtask 3 evaluation."""

from __future__ import annotations

from typing import Any

from benchmark.online_pipeline.meta_analysis.evaluation_common.metrics import _mean


FIELDS = ("effect_measure", "analysis_model", "statistical_method", "ci_level", "analysis_included_study_ids")


def build_comparisons(predictions: list[dict[str, Any]], gold_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    predictions_by_id = {str(row["instance_id"]): row for row in predictions}
    rows: list[dict[str, Any]] = []
    for instance_id, gold in gold_by_id.items():
        prediction = predictions_by_id.get(instance_id) or {"instance_id": instance_id}
        gold_rows = {str(row.get("setting_id") or ""): row for row in gold.get("analysis_methods") or []}
        pred_rows = {str(row.get("setting_id") or ""): row for row in prediction.get("analysis_methods") or []}
        for setting_id, gold_row in gold_rows.items():
            pred_row = pred_rows.get(setting_id)
            exact = pred_row is not None and all(pred_row.get(field) == gold_row.get(field) for field in FIELDS)
            rows.append(
                {
                    "instance_id": instance_id,
                    "key": setting_id,
                    "covered": pred_row is not None,
                    "exact_match": exact,
                }
            )
    return rows


def evaluate_predictions(predictions: list[dict[str, Any]], gold_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows = build_comparisons(predictions, gold_by_id)
    return {
        "instance_count": len(gold_by_id),
        "comparison_count": len(rows),
        "method_exact_rate": _mean([row["exact_match"] for row in rows]),
        "method_join_rate": _mean([row["covered"] for row in rows]),
    }
