"""Benchmark-side method adapters for meta-analysis subtasks."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from ebm_backend.online_pipeline.infrastructure.methods.meta_analysis.loader import get_meta_analysis_subtask_method
from ebm_backend.online_pipeline.infrastructure.methods.meta_analysis.subtask2_study_results.method_test import predict_study_result_rows_llm

from benchmark.online_pipeline.meta_analysis.evaluation_common.article_store import load_articles_for_instance
from benchmark.online_pipeline.meta_analysis.subtask2_study_results.evaluation.llm import run_llm_extraction


def predict_subtask2(*, instance: dict[str, Any], gold: dict[str, Any], method: str, dataset_dir: str | Path, llm_config: str | Path | None = None) -> dict[str, Any]:
    if method in {"gold", "official_csv_oracle", "subtask2_official_csv_oracle"}:
        return {
            "instance_id": instance["instance_id"],
            "review_id": instance["review_id"],
            "study_result_rows": gold.get("study_result_rows") or [],
        }
    if method in {"method_test", "study_results_rule_v1", "study_results_passthrough_v1"}:
        articles = load_articles_for_instance(dataset_dir=dataset_dir, instance=instance)
        method_obj = get_meta_analysis_subtask_method("study_results", _subtask_method_name(method))
        return {
            "instance_id": instance["instance_id"],
            "review_id": instance["review_id"],
            "study_result_rows": method_obj.run(instance=instance, articles=articles),
        }
    if method == "study_results_llm_extract_v1":
        if llm_config is None:
            raise ValueError("study_results_llm_extract_v1 requires llm_config")
        with tempfile.TemporaryDirectory(prefix="subtask2_llm_") as tmpdir:
            output_path = Path(tmpdir) / "predictions.jsonl"
            failures_path = Path(tmpdir) / "failures.jsonl"
            rows = run_llm_extraction(
                dataset=dataset_dir,
                llm_config=llm_config,
                output_path=output_path,
                failure_output_path=failures_path,
                limit=1,
                workers=1,
                resume=False,
            )
            for row in rows:
                if str(row.get("instance_id")) == str(instance["instance_id"]):
                    return {
                        "instance_id": row["instance_id"],
                        "review_id": row.get("review_id"),
                        "study_result_rows": predict_study_result_rows_llm(instance=instance, llm_rows=row.get("study_result_rows") or []),
                    }
        return {
            "instance_id": instance["instance_id"],
            "review_id": instance["review_id"],
            "study_result_rows": [],
        }
    raise ValueError(f"Unknown Subtask 2 method: {method}")


def predict_subtask3(*, instance: dict[str, Any], gold: dict[str, Any], method: str) -> dict[str, Any]:
    if method in {"gold", "official_csv_oracle", "subtask3_official_csv_oracle"}:
        return {
            "instance_id": instance["instance_id"],
            "review_id": instance["review_id"],
            "analysis_methods": gold.get("analysis_methods") or [],
        }
    if method in {"method_test", "analysis_methods_rule_v1"}:
        method_obj = get_meta_analysis_subtask_method("analysis_methods", _subtask_method_name(method))
        return {
            "instance_id": instance["instance_id"],
            "review_id": instance["review_id"],
            "analysis_methods": method_obj.run(instance=instance),
        }
    raise ValueError(f"Unknown Subtask 3 method: {method}")


def predict_subtask4(*, instances: list[dict[str, Any]], gold_by_id: dict[str, dict[str, Any]], method: str) -> list[dict[str, Any]]:
    if method in {"gold", "official_csv_oracle", "subtask4_official_csv_oracle"}:
        return [
            {
                "instance_id": instance["instance_id"],
                "review_id": instance["review_id"],
                "subgroup_results": (gold_by_id[str(instance["instance_id"])].get("subgroup_results") or {"subgroup_estimates": [], "subgroup_difference_tests": []}),
            }
            for instance in instances
        ]
    if method in {"method_test", "stats_pooling_v1"}:
        method_obj = get_meta_analysis_subtask_method("subgroup_analysis", _subtask_method_name(method))
        grouped: dict[str, list[dict[str, Any]]] = {}
        for instance in instances:
            family_id = str(instance["analysis_setting"]["setting_family_id"])
            grouped.setdefault(family_id, []).append(instance)
        predictions_by_id: dict[str, dict[str, Any]] = {}
        for family_instances in grouped.values():
            family_payload = method_obj.run(instances=family_instances)
            predictions_by_id.update(family_payload)
        return [
            {
                "instance_id": instance["instance_id"],
                "review_id": instance["review_id"],
                "subgroup_results": predictions_by_id.get(str(instance["instance_id"]), {"subgroup_estimates": [], "subgroup_difference_tests": []}),
            }
            for instance in instances
        ]
    raise ValueError(f"Unknown Subtask 4 method: {method}")


def predict_subtask5(*, instance: dict[str, Any], gold: dict[str, Any], method: str) -> dict[str, Any]:
    if method in {"gold", "official_csv_oracle", "subtask5_official_csv_oracle"}:
        return {
            "instance_id": instance["instance_id"],
            "review_id": instance["review_id"],
            "overall_estimates": gold.get("overall_estimates") or [],
        }
    if method in {"method_test", "stats_pooling_v1"}:
        method_obj = get_meta_analysis_subtask_method("overall_estimates", _subtask_method_name(method))
        return {
            "instance_id": instance["instance_id"],
            "review_id": instance["review_id"],
            "overall_estimates": method_obj.run(instance=instance),
        }
    raise ValueError(f"Unknown Subtask 5 method: {method}")


def _subtask_method_name(method: str) -> str:
    if method in {"study_results_rule_v1", "study_results_passthrough_v1", "analysis_methods_rule_v1", "stats_pooling_v1"}:
        return "method_test"
    return method
