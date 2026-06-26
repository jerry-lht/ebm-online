"""Metrics for GRADE domain judgement evaluation."""

from __future__ import annotations

from typing import Any


FIELDS = ("downgraded", "severity", "levels", "level_evaluable")


def build_comparisons(predictions: list[dict[str, Any]], gold_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    predictions_by_id = {str(row.get("instance_id") or ""): row for row in predictions}
    rows: list[dict[str, Any]] = []
    for instance_id, gold in gold_by_id.items():
        prediction = predictions_by_id.get(instance_id) or {"instance_id": instance_id}
        gold_judgement = gold.get("judgement") or {}
        pred_judgement = _prediction_judgement(prediction)
        domain = str(gold.get("domain") or gold_judgement.get("domain") or "")
        for field in FIELDS:
            rows.append(
                {
                    "instance_id": instance_id,
                    "domain": domain,
                    "field": field,
                    "covered": bool(pred_judgement),
                    "gold": gold_judgement.get(field),
                    "prediction": pred_judgement.get(field),
                    "exact_match": _value_equal(gold_judgement.get(field), pred_judgement.get(field)),
                }
            )
    return rows


def evaluate_predictions(predictions: list[dict[str, Any]], gold_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows = build_comparisons(predictions, gold_by_id)
    by_field = {field: [row for row in rows if row["field"] == field] for field in FIELDS}
    missing_prediction_count = sum(1 for instance_id in gold_by_id if instance_id not in {str(row.get("instance_id") or "") for row in predictions})
    return {
        "instance_count": len(gold_by_id),
        "comparison_count": len(rows),
        "missing_prediction_count": missing_prediction_count,
        "judgement_join_rate": _mean([row["covered"] for row in by_field["downgraded"]]),
        "downgraded_exact_rate": _mean([row["exact_match"] for row in by_field["downgraded"]]),
        "severity_exact_rate": _mean([row["exact_match"] for row in by_field["severity"]]),
        "levels_exact_rate": _mean([row["exact_match"] for row in by_field["levels"]]),
        "evaluable_exact_rate": _mean([row["exact_match"] for row in by_field["level_evaluable"]]),
        "all_fields_exact_rate": _all_fields_exact_rate(rows),
    }


def _prediction_judgement(prediction: dict[str, Any]) -> dict[str, Any]:
    if isinstance(prediction.get("judgement"), dict):
        return prediction["judgement"]
    payload = prediction.get("prediction")
    if isinstance(payload, dict):
        if isinstance(payload.get("judgement"), dict):
            return payload["judgement"]
        domain = prediction.get("domain") or payload.get("domain")
        sof_row_id = prediction.get("sof_row_id") or payload.get("sof_row_id")
        for row in payload.get("sof_rows") or []:
            if sof_row_id and row.get("sof_row_id") != sof_row_id:
                continue
            judgements = row.get("domain_judgements") or {}
            if domain and isinstance(judgements.get(str(domain)), dict):
                return judgements[str(domain)]
    return {}


def _all_fields_exact_rate(rows: list[dict[str, Any]]) -> float:
    by_instance: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_instance.setdefault(str(row["instance_id"]), []).append(row)
    return _mean([all(row["exact_match"] for row in instance_rows) for instance_rows in by_instance.values()])


def _value_equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return bool(left) is bool(right)
    return str(left) == str(right)


def _mean(values: list[bool]) -> float:
    return sum(1 for value in values if value) / len(values) if values else 0.0
