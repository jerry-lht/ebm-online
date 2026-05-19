"""Flatten evaluation metrics into CSV-ready readiness rows."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

AUTOMATION_READINESS_COLUMNS = [
    "run_id",
    "method",
    "benchmark",
    "split",
    "input_setting",
    "readiness_profile",
    "sensitivity",
    "specificity",
    "precision",
    "balanced_accuracy",
    "macro_f1",
    "false_negative_count",
    "high_confidence_threshold",
    "high_confidence_false_negative_count",
    "full_text_workload",
    "full_text_workload_reduction",
    "unsupported_exclusion_rate",
    "hallucinated_reason_rate",
    "placeholder_status",
    "reference_sensitivity",
    "sensitivity_gap_vs_reference",
    "decision_ready",
    "overall_ready",
    "blocked_by_placeholder",
    "failed_checks",
]


def metrics_to_readiness_row(metrics: dict[str, Any]) -> dict[str, Any]:
    """Convert one metrics JSON document into a flat readiness row."""
    metadata = metrics.get("metadata", {})
    decision_metrics = metrics.get("decision_metrics", {})
    safety_metrics = metrics.get("safety_metrics", {})
    workload_metrics = metrics.get("workload_metrics", {})
    readiness = metrics.get("readiness", {})

    return {
        "run_id": metadata.get("run_id"),
        "method": metadata.get("method"),
        "benchmark": metadata.get("benchmark"),
        "split": metadata.get("split"),
        "input_setting": metadata.get("input_setting"),
        "readiness_profile": readiness.get("profile"),
        "sensitivity": decision_metrics.get("sensitivity"),
        "specificity": decision_metrics.get("specificity"),
        "precision": decision_metrics.get("precision"),
        "balanced_accuracy": decision_metrics.get("balanced_accuracy"),
        "macro_f1": decision_metrics.get("macro_f1"),
        "false_negative_count": decision_metrics.get("false_negative_count"),
        "high_confidence_threshold": safety_metrics.get("high_confidence_threshold"),
        "high_confidence_false_negative_count": safety_metrics.get(
            "high_confidence_false_negative_count"
        ),
        "full_text_workload": workload_metrics.get("full_text_workload"),
        "full_text_workload_reduction": workload_metrics.get("full_text_workload_reduction"),
        "unsupported_exclusion_rate": safety_metrics.get("unsupported_exclusion_rate"),
        "hallucinated_reason_rate": safety_metrics.get("hallucinated_reason_rate"),
        "placeholder_status": safety_metrics.get("placeholder_status"),
        "reference_sensitivity": readiness.get("reference_sensitivity"),
        "sensitivity_gap_vs_reference": readiness.get("sensitivity_gap_vs_reference"),
        "decision_ready": readiness.get("decision_ready"),
        "overall_ready": readiness.get("overall_ready"),
        "blocked_by_placeholder": readiness.get("blocked_by_placeholder"),
        "failed_checks": ";".join(readiness.get("failed_checks", [])),
    }


def update_automation_readiness_table(path: str | Path, metrics: dict[str, Any]) -> None:
    """Upsert one readiness row keyed by run_id into the readiness CSV."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    row = metrics_to_readiness_row(metrics)
    run_id = row.get("run_id")
    if not run_id:
        raise ValueError("metrics row requires run_id")

    rows: list[dict[str, Any]] = []
    if target.exists():
        with target.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows.extend(reader)

    replaced = False
    normalized_rows: list[dict[str, Any]] = []
    for existing in rows:
        if existing.get("run_id") == run_id:
            normalized_rows.append({column: row.get(column) for column in AUTOMATION_READINESS_COLUMNS})
            replaced = True
        else:
            normalized_rows.append(
                {column: existing.get(column, "") for column in AUTOMATION_READINESS_COLUMNS}
            )
    if not replaced:
        normalized_rows.append({column: row.get(column) for column in AUTOMATION_READINESS_COLUMNS})

    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUTOMATION_READINESS_COLUMNS)
        writer.writeheader()
        writer.writerows(normalized_rows)
