"""Structured report output for benchmark2-v2 experiments."""

from __future__ import annotations

import csv
from pathlib import Path

from .io_utils import ensure_dir, read_json, write_json


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def _load_summary(score_root: Path, filename: str) -> dict:
    return read_json(score_root / filename)


def build_report(*, score_dir: str | Path, output_path: str | Path) -> dict:
    score_root = Path(score_dir)
    output_root = ensure_dir(output_path)
    support = _load_summary(score_root, "support_summary.json")
    proposal = _load_summary(score_root, "proposal_summary.json")
    oracle = _load_summary(score_root, "oracle_extraction_summary.json")
    routed = _load_summary(score_root, "routed_extraction_summary.json")

    manifest = {"score_dir": str(score_root), "tables_dir": str(output_root), "tables": {}}

    main_rows = [
        {
            "experiment": "Official Item Support",
            "metric": "joint_support_consistency",
            "value": support["primary_metrics"]["joint_support_consistency"],
            "instances": support["instances"],
            "notes": f"uncertain_rate={support['primary_metrics']['uncertain_rate']:.4f}",
        },
        {
            "experiment": "Open-world Item Proposal",
            "metric": "structured_f1",
            "value": proposal["primary_metrics"]["structured"]["f1"],
            "instances": proposal["instances"],
            "notes": f"subgroup_f1={proposal['primary_metrics']['subgroup']['f1']:.4f} timepoint_f1={proposal['primary_metrics']['timepoint']['f1']:.4f}",
        },
        {
            "experiment": "Oracle Extraction",
            "metric": "field_f1",
            "value": oracle["primary_metrics"]["field"]["f1"],
            "instances": oracle["scored_instances"],
            "notes": f"row_exact={oracle['primary_metrics']['row_exact_match']:.4f}",
        },
        {
            "experiment": "Routed Extraction",
            "metric": "field_f1",
            "value": routed["primary_metrics"]["field"]["f1"],
            "instances": routed["instances"],
            "notes": f"setting_success_rate={routed['primary_metrics']['setting_success_rate']:.4f}",
        },
    ]
    _write_csv(output_root / "main_table.csv", ["experiment", "metric", "value", "instances", "notes"], main_rows)
    manifest["tables"]["main_table"] = "main_table.csv"

    per_data_type_rows = []
    for task_name, summary in (("support", support), ("proposal", proposal), ("oracle_extraction", oracle), ("routed_extraction", routed)):
        for data_type, metrics in sorted(summary.get("per_data_type", {}).items()):
            metric_value = metrics.get("joint_support_consistency")
            if metric_value is None:
                metric_value = (metrics.get("structured") or metrics.get("field") or metrics.get("proposal_structured") or {}).get("f1", "")
            per_data_type_rows.append({"task": task_name, "data_type": data_type, "instances": metrics.get("instances", ""), "primary_value": metric_value})
    _write_csv(output_root / "per_data_type.csv", ["task", "data_type", "instances", "primary_value"], per_data_type_rows)
    manifest["tables"]["per_data_type"] = "per_data_type.csv"

    per_field_rows = [
        {"field_name": field_name, "precision": metrics["precision"], "recall": metrics["recall"], "f1": metrics["f1"], "tp": metrics["tp"], "fp": metrics["fp"], "fn": metrics["fn"]}
        for field_name, metrics in sorted(oracle.get("per_field", {}).items())
    ]
    _write_csv(output_root / "per_field.csv", ["field_name", "precision", "recall", "f1", "tp", "fp", "fn"], per_field_rows)
    manifest["tables"]["per_field"] = "per_field.csv"

    per_match_status_rows = []
    for match_status, metrics in sorted(oracle.get("per_match_status", {}).items()):
        field_metrics = metrics.get("field", {})
        per_match_status_rows.append({"match_status": match_status, "instances": metrics.get("instances", 0), "scored_instances": metrics.get("scored_instances", 0), "field_f1": field_metrics.get("f1", 0.0)})
    _write_csv(output_root / "per_match_status.csv", ["match_status", "instances", "scored_instances", "field_f1"], per_match_status_rows)
    manifest["tables"]["per_match_status"] = "per_match_status.csv"

    error_bucket_rows = []
    for source, summary in (("support", support), ("proposal", proposal), ("oracle_extraction", oracle), ("routed_extraction", routed)):
        for key, value in sorted(summary.get("error_buckets", {}).items()):
            error_bucket_rows.append({"source": source, "bucket": key, "value": value})
    _write_csv(output_root / "error_buckets.csv", ["source", "bucket", "value"], error_bucket_rows)
    manifest["tables"]["error_buckets"] = "error_buckets.csv"

    representative_rows = []
    for source, summary in (("support", support), ("proposal", proposal), ("oracle_extraction", oracle), ("routed_extraction", routed)):
        for row in summary.get("representative_failures", []):
            representative_rows.append({"source": source, "instance_id": row.get("instance_id"), "split": row.get("split"), "data_type": row.get("data_type")})
    _write_csv(output_root / "representative_failures.csv", ["source", "instance_id", "split", "data_type"], representative_rows)
    manifest["tables"]["representative_failures"] = "representative_failures.csv"

    markdown_lines = [
        "# Benchmark2-v2 Report",
        "",
        "| Experiment | Metric | Value |",
        "| --- | --- | --- |",
    ]
    for row in main_rows:
        markdown_lines.append(f"| {row['experiment']} | {row['metric']} | {row['value']:.4f} |")
    (output_root / "report.md").write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    manifest["tables"]["report"] = "report.md"

    write_json(output_root / "tables_manifest.json", manifest)
    return manifest
