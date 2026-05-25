"""Scoring functions for benchmark2-v2 experiments."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from .constants import ORACLE_EXTRACTION_TASK, PROPOSAL_TASK, ROUTED_EXTRACTION_TASK, SUPPORT_TASK
from .io_utils import ensure_dir, iter_jsonl, write_json, write_jsonl
from .normalize import field_key, normalize_subgroup, normalize_timepoint_value, row_key, structured_item_key
from .runtime import resolve_task_paths


def safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def prf(tp: int, fp: int, fn: int) -> dict:
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    f1 = safe_div(2 * precision * recall, precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}


def macro_f1(labels: list[str], gold: list[str], pred: list[str]) -> float:
    scores = []
    for label in labels:
        tp = sum(1 for g, p in zip(gold, pred) if g == label and p == label)
        fp = sum(1 for g, p in zip(gold, pred) if g != label and p == label)
        fn = sum(1 for g, p in zip(gold, pred) if g == label and p != label)
        scores.append(prf(tp, fp, fn)["f1"])
    return mean(scores) if scores else 0.0


def counter_overlap(left: Counter, right: Counter) -> int:
    return sum((left & right).values())


def _group_by(records: list[dict], field: str) -> dict:
    groups = defaultdict(list)
    for record in records:
        groups[record.get(field, "unknown")].append(record)
    return groups


def _field_counter(rows: list[dict]) -> Counter:
    counter = Counter()
    for row in rows:
        for field in row.get("direct_extraction_fields") or []:
            counter[field_key(field)] += 1
    return counter


def _field_name_breakdown(gold_rows: list[dict], predicted_rows: list[dict]) -> dict:
    by_name = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    gold_counter = _field_counter(gold_rows)
    pred_counter = _field_counter(predicted_rows)
    overlap = gold_counter & pred_counter
    for (field_name, _), count in overlap.items():
        by_name[field_name]["tp"] += count
    for (field_name, _), count in (pred_counter - gold_counter).items():
        by_name[field_name]["fp"] += count
    for (field_name, _), count in (gold_counter - pred_counter).items():
        by_name[field_name]["fn"] += count
    return {field_name: {**counts, **prf(counts["tp"], counts["fp"], counts["fn"])} for field_name, counts in by_name.items()}


def support_instance_score(gold: dict, prediction: dict) -> dict:
    gold_subgroup = gold["gold_support"]["subgroup_support_status"]
    pred_subgroup = prediction.get("subgroup_support_status", "not_supported")
    gold_timepoint = gold["gold_support"]["timepoint_support_status"]
    pred_timepoint = prediction.get("timepoint_support_status", "not_supported")
    return {
        "instance_id": gold["instance_id"],
        "split": gold["split"],
        "data_type": gold["setting_context"].get("data_type"),
        "subgroup_gold": gold_subgroup,
        "subgroup_pred": pred_subgroup,
        "timepoint_gold": gold_timepoint,
        "timepoint_pred": pred_timepoint,
        "subgroup_correct": gold_subgroup == pred_subgroup,
        "timepoint_correct": gold_timepoint == pred_timepoint,
        "joint_correct": gold_subgroup == pred_subgroup and gold_timepoint == pred_timepoint,
    }


def _support_summary(scores: list[dict]) -> dict:
    subgroup_gold = [row["subgroup_gold"] for row in scores]
    subgroup_pred = [row["subgroup_pred"] for row in scores]
    timepoint_gold = [row["timepoint_gold"] for row in scores]
    timepoint_pred = [row["timepoint_pred"] for row in scores]
    return {
        "task": SUPPORT_TASK,
        "instances": len(scores),
        "scored_instances": len(scores),
        "primary_metrics": {
            "subgroup_accuracy": mean(row["subgroup_correct"] for row in scores) if scores else 0.0,
            "timepoint_accuracy": mean(row["timepoint_correct"] for row in scores) if scores else 0.0,
            "subgroup_macro_f1": macro_f1(["supported", "not_supported", "uncertain"], subgroup_gold, subgroup_pred),
            "timepoint_macro_f1": macro_f1(["supported", "not_supported", "uncertain"], timepoint_gold, timepoint_pred),
            "subgroup_supported_recall": prf(
                sum(1 for g, p in zip(subgroup_gold, subgroup_pred) if g == "supported" and p == "supported"),
                sum(1 for g, p in zip(subgroup_gold, subgroup_pred) if g != "supported" and p == "supported"),
                sum(1 for g, p in zip(subgroup_gold, subgroup_pred) if g == "supported" and p != "supported"),
            )["recall"],
            "timepoint_supported_recall": prf(
                sum(1 for g, p in zip(timepoint_gold, timepoint_pred) if g == "supported" and p == "supported"),
                sum(1 for g, p in zip(timepoint_gold, timepoint_pred) if g != "supported" and p == "supported"),
                sum(1 for g, p in zip(timepoint_gold, timepoint_pred) if g == "supported" and p != "supported"),
            )["recall"],
            "uncertain_rate": safe_div(sum(1 for row in scores if row["subgroup_pred"] == "uncertain" or row["timepoint_pred"] == "uncertain"), len(scores)),
            "joint_support_consistency": mean(row["joint_correct"] for row in scores) if scores else 0.0,
        },
        "per_data_type": {
            data_type: {
                "instances": len(records),
                "subgroup_accuracy": mean(record["subgroup_correct"] for record in records) if records else 0.0,
                "timepoint_accuracy": mean(record["timepoint_correct"] for record in records) if records else 0.0,
                "joint_support_consistency": mean(record["joint_correct"] for record in records) if records else 0.0,
            }
            for data_type, records in _group_by(scores, "data_type").items()
        },
        "error_buckets": {
            "subgroup_errors": sum(1 for row in scores if not row["subgroup_correct"]),
            "timepoint_errors": sum(1 for row in scores if not row["timepoint_correct"]),
        },
        "representative_failures": [row for row in scores if not row["joint_correct"]][:10],
        "run_metadata": {"negative_label_note": "Support negatives are incomplete and should be interpreted conservatively."},
    }


def proposal_instance_score(gold: dict, prediction: dict) -> dict:
    gold_items = gold.get("gold_items") or []
    pred_items = prediction.get("proposed_items") or []
    gold_subgroups = Counter(normalize_subgroup(item.get("subgroup")) for item in gold_items)
    pred_subgroups = Counter(normalize_subgroup(item.get("subgroup")) for item in pred_items)
    gold_timepoints = Counter(timepoint for item in gold_items for timepoint in set(item.get("timepoints") or []))
    pred_timepoints = Counter(timepoint for item in pred_items for timepoint in set(item.get("timepoints") or []))
    gold_structured = Counter(structured_item_key(item) for item in gold_items)
    pred_structured = Counter(structured_item_key(item) for item in pred_items)
    structured_tp = counter_overlap(gold_structured, pred_structured)

    observed_gold_subgroups = Counter(
        normalize_subgroup(item.get("subgroup"))
        for item in gold_items
        if normalize_subgroup(item.get("subgroup")) is not None
    )
    observed_gold_timepoints = Counter(
        timepoint
        for item in gold_items
        for timepoint in set(item.get("timepoints") or [])
        if timepoint
    )
    observed_gold_structured = Counter(
        structured_item_key(item)
        for item in gold_items
        if normalize_subgroup(item.get("subgroup")) is not None and any(item.get("timepoints") or [])
    )
    observed_pred_subgroups = Counter(
        normalize_subgroup(item.get("subgroup"))
        for item in pred_items
        if normalize_subgroup(item.get("subgroup")) is not None
    )
    observed_pred_timepoints = Counter(
        timepoint
        for item in pred_items
        for timepoint in set(item.get("timepoints") or [])
        if timepoint
    )
    observed_pred_structured = Counter(
        structured_item_key(item)
        for item in pred_items
        if normalize_subgroup(item.get("subgroup")) is not None and any(item.get("timepoints") or [])
    )

    subgroup_tp = counter_overlap(gold_subgroups, pred_subgroups)
    timepoint_tp = counter_overlap(gold_timepoints, pred_timepoints)
    observed_subgroup_tp = counter_overlap(observed_gold_subgroups, observed_pred_subgroups)
    observed_timepoint_tp = counter_overlap(observed_gold_timepoints, observed_pred_timepoints)
    observed_structured_tp = counter_overlap(observed_gold_structured, observed_pred_structured)

    extra_keys = list((pred_structured - gold_structured).elements())
    unsupported_extra_count = sum(1 for subgroup, timepoints in extra_keys if subgroup is None and not timepoints)
    conflicting_extra_count = len(extra_keys) - unsupported_extra_count
    return {
        "instance_id": gold["instance_id"],
        "split": gold["split"],
        "data_type": gold["setting_context"].get("data_type"),
        "subgroup_metrics": prf(subgroup_tp, sum(pred_subgroups.values()) - subgroup_tp, sum(gold_subgroups.values()) - subgroup_tp),
        "timepoint_metrics": prf(timepoint_tp, sum(pred_timepoints.values()) - timepoint_tp, sum(gold_timepoints.values()) - timepoint_tp),
        "structured_metrics": prf(structured_tp, sum(pred_structured.values()) - structured_tp, sum(gold_structured.values()) - structured_tp),
        "observed_metrics": {
            "subgroup": prf(observed_subgroup_tp, sum(observed_pred_subgroups.values()) - observed_subgroup_tp, sum(observed_gold_subgroups.values()) - observed_subgroup_tp),
            "timepoint": prf(observed_timepoint_tp, sum(observed_pred_timepoints.values()) - observed_timepoint_tp, sum(observed_gold_timepoints.values()) - observed_timepoint_tp),
            "structured": prf(observed_structured_tp, sum(observed_pred_structured.values()) - observed_structured_tp, sum(observed_gold_structured.values()) - observed_structured_tp),
        },
        "observed_counts": {
            "subgroup_items": sum(observed_gold_subgroups.values()),
            "timepoint_items": sum(observed_gold_timepoints.values()),
            "structured_items": sum(observed_gold_structured.values()),
        },
        "error_buckets": {
            "supported_extra_count": 0,
            "unsupported_extra_count": unsupported_extra_count,
            "conflicting_extra_count": conflicting_extra_count,
        },
        "exact_match": gold_structured == pred_structured,
    }


def oracle_extraction_instance_score(gold: dict, prediction: dict) -> dict:
    gold_rows = gold.get("gold_extraction_rows") or []
    predicted_rows = prediction.get("predicted_rows") or []
    gold_row_counter = Counter(row_key(row) for row in gold_rows)
    pred_row_counter = Counter(row_key(row) for row in predicted_rows)
    gold_field_counter = _field_counter(gold_rows)
    pred_field_counter = _field_counter(predicted_rows)
    field_tp = counter_overlap(gold_field_counter, pred_field_counter)
    row_tp = counter_overlap(gold_row_counter, pred_row_counter)
    match_status = gold.get("official_item", {}).get("match_status")
    scored = match_status in {"unique", "multiple"}
    return {
        "instance_id": gold["instance_id"],
        "split": gold["split"],
        "data_type": gold["setting_context"].get("data_type"),
        "match_status": match_status,
        "scored": scored,
        "gold_row_count": len(gold_rows),
        "predicted_row_count": len(predicted_rows),
        "field_metrics": prf(field_tp, sum(pred_field_counter.values()) - field_tp, sum(gold_field_counter.values()) - field_tp),
        "row_metrics": prf(row_tp, sum(pred_row_counter.values()) - row_tp, sum(gold_row_counter.values()) - row_tp),
        "row_exact_match": gold_row_counter == pred_row_counter,
        "item_exact_match": gold_row_counter == pred_row_counter,
        "field_name_breakdown": _field_name_breakdown(gold_rows, predicted_rows),
        "analysis_buckets": {
            "complete_row_count": int((prediction.get("prediction_stats") or {}).get("complete_row_count", 0)),
            "partial_row_count": int((prediction.get("prediction_stats") or {}).get("partial_row_count", 0)),
            "empty_prediction_rate": 1 if not predicted_rows else 0,
        },
    }


def routed_extraction_instance_score(gold: dict, prediction: dict) -> dict:
    gold_items = gold.get("gold_items") or []
    predicted_items = prediction.get("predicted_items") or []
    gold_structured = Counter(structured_item_key(item) for item in gold_items)
    pred_structured = Counter(structured_item_key(item) for item in predicted_items)
    structured_tp = counter_overlap(gold_structured, pred_structured)
    matched_gold = defaultdict(list)
    for item in gold_items:
        matched_gold[structured_item_key(item)].append(item)
    matched_pred = defaultdict(list)
    for item in predicted_items:
        matched_pred[structured_item_key(item)].append(item)
    field_tp = field_fp = field_fn = 0
    row_tp = row_fp = row_fn = 0
    extraction_error_count = 0
    timepoint_misalignment_count = 0
    matched_keys = set(gold_structured) & set(pred_structured)
    for key in matched_keys:
        gold_item = matched_gold[key][0]
        pred_item = matched_pred[key][0]
        gold_rows = gold_item.get("gold_extraction_rows") or []
        pred_rows = pred_item.get("predicted_rows") or []
        gold_field_counter = _field_counter(gold_rows)
        pred_field_counter = _field_counter(pred_rows)
        tp = counter_overlap(gold_field_counter, pred_field_counter)
        fp = sum(pred_field_counter.values()) - tp
        fn = sum(gold_field_counter.values()) - tp
        field_tp += tp
        field_fp += fp
        field_fn += fn
        gold_row_counter = Counter(row_key(row) for row in gold_rows)
        pred_row_counter = Counter(row_key(row) for row in pred_rows)
        row_overlap = counter_overlap(gold_row_counter, pred_row_counter)
        row_tp += row_overlap
        row_fp += sum(pred_row_counter.values()) - row_overlap
        row_fn += sum(gold_row_counter.values()) - row_overlap
        if gold_row_counter != pred_row_counter:
            extraction_error_count += 1
    for pred_item in predicted_items:
        pred_key = structured_item_key(pred_item)
        subgroup_only_matches = [item for item in gold_items if normalize_subgroup(item.get("subgroup")) == pred_key[0]]
        if subgroup_only_matches and pred_key not in matched_keys and pred_key not in gold_structured:
            timepoint_misalignment_count += 1
    setting_success = gold_structured == pred_structured and field_fp == 0 and field_fn == 0
    return {
        "instance_id": gold["instance_id"],
        "split": gold["split"],
        "data_type": gold["setting_context"].get("data_type"),
        "proposal_metrics": prf(structured_tp, sum(pred_structured.values()) - structured_tp, sum(gold_structured.values()) - structured_tp),
        "subgroup_metrics": proposal_instance_score({"gold_items": gold_items, "split": gold["split"], "setting_context": gold["setting_context"], "instance_id": gold["instance_id"]}, {"proposed_items": predicted_items})["subgroup_metrics"],
        "timepoint_metrics": proposal_instance_score({"gold_items": gold_items, "split": gold["split"], "setting_context": gold["setting_context"], "instance_id": gold["instance_id"]}, {"proposed_items": predicted_items})["timepoint_metrics"],
        "field_metrics": prf(field_tp, field_fp, field_fn),
        "row_metrics": prf(row_tp, row_fp, row_fn),
        "setting_success": setting_success,
        "error_buckets": {
            "routing_missing_count": sum((gold_structured - pred_structured).values()),
            "routing_extra_count": sum((pred_structured - gold_structured).values()),
            "timepoint_misalignment_count": timepoint_misalignment_count,
            "extraction_error_count": extraction_error_count,
            "pipeline_propagation_error_count": sum(1 for key in (gold_structured - pred_structured).elements() if matched_gold[key[0] if isinstance(key, tuple) else key]),
        },
    }


def _aggregate_prf(records: list[dict], path: tuple[str, ...]) -> dict:
    tp = fp = fn = 0
    for record in records:
        cursor = record
        for key in path:
            cursor = cursor[key]
        tp += cursor["tp"]
        fp += cursor["fp"]
        fn += cursor["fn"]
    return prf(tp, fp, fn)


def _aggregate_field_breakdown(scores: list[dict]) -> dict:
    counts = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    for score in scores:
        for field_name, metrics in score.get("field_name_breakdown", {}).items():
            counts[field_name]["tp"] += metrics["tp"]
            counts[field_name]["fp"] += metrics["fp"]
            counts[field_name]["fn"] += metrics["fn"]
    return {field_name: {**counts[field_name], **prf(counts[field_name]["tp"], counts[field_name]["fp"], counts[field_name]["fn"])} for field_name in sorted(counts)}


def _aligned_gold_rows(instances_path: str | Path, predictions_path: str | Path) -> tuple[dict[str, dict], dict[str, dict], str | None]:
    gold_rows = {row["instance_id"]: row for row in iter_jsonl(instances_path) or []}
    pred_rows = {row["instance_id"]: row for row in iter_jsonl(predictions_path) or []}
    predicted_splits = {row.get("split") for row in pred_rows.values() if row.get("split") is not None}
    requested_split = next(iter(predicted_splits)) if len(predicted_splits) == 1 else None
    if requested_split is not None:
        gold_rows = {
            instance_id: row
            for instance_id, row in gold_rows.items()
            if row.get("split") == requested_split
        }
    return gold_rows, pred_rows, requested_split


def score_support(*, instances_path: str | Path, predictions_path: str | Path, output_dir: str | Path) -> dict:
    gold_rows, pred_rows, requested_split = _aligned_gold_rows(instances_path, predictions_path)
    scores = [support_instance_score(gold_rows[key], pred_rows.get(key, {})) for key in gold_rows]
    out_dir = ensure_dir(output_dir)
    write_jsonl(out_dir / "support_scores.jsonl", scores)
    summary = _support_summary(scores)
    if requested_split is not None:
        summary["requested_split"] = requested_split
    write_json(out_dir / "support_summary.json", summary)
    return summary


def score_proposal(*, instances_path: str | Path, predictions_path: str | Path, output_dir: str | Path) -> dict:
    gold_rows, pred_rows, requested_split = _aligned_gold_rows(instances_path, predictions_path)
    scores = [proposal_instance_score(gold_rows[key], pred_rows.get(key, {})) for key in gold_rows]
    out_dir = ensure_dir(output_dir)
    write_jsonl(out_dir / "proposal_scores.jsonl", scores)
    summary = {
        "task": PROPOSAL_TASK,
        "instances": len(scores),
        "scored_instances": len(scores),
        "primary_metrics": {
            "subgroup": _aggregate_prf(scores, ("subgroup_metrics",)),
            "timepoint": _aggregate_prf(scores, ("timepoint_metrics",)),
            "structured": _aggregate_prf(scores, ("structured_metrics",)),
        },
        "observed_primary_metrics": {
            "subgroup": _aggregate_prf(scores, ("observed_metrics", "subgroup")),
            "timepoint": _aggregate_prf(scores, ("observed_metrics", "timepoint")),
            "structured": _aggregate_prf(scores, ("observed_metrics", "structured")),
        },
        "observed_counts": {
            "subgroup_items": sum(score["observed_counts"]["subgroup_items"] for score in scores),
            "timepoint_items": sum(score["observed_counts"]["timepoint_items"] for score in scores),
            "structured_items": sum(score["observed_counts"]["structured_items"] for score in scores),
        },
        "per_data_type": {
            data_type: {
                "instances": len(records),
                "structured": _aggregate_prf(records, ("structured_metrics",)),
                "observed_structured": _aggregate_prf(records, ("observed_metrics", "structured")),
                "observed_counts": {
                    "subgroup_items": sum(record["observed_counts"]["subgroup_items"] for record in records),
                    "timepoint_items": sum(record["observed_counts"]["timepoint_items"] for record in records),
                    "structured_items": sum(record["observed_counts"]["structured_items"] for record in records),
                },
            }
            for data_type, records in _group_by(scores, "data_type").items()
        },
        "error_buckets": {
            "supported_extra_count": sum(score["error_buckets"]["supported_extra_count"] for score in scores),
            "unsupported_extra_count": sum(score["error_buckets"]["unsupported_extra_count"] for score in scores),
            "conflicting_extra_count": sum(score["error_buckets"]["conflicting_extra_count"] for score in scores),
        },
        "representative_failures": [row for row in scores if not row["exact_match"]][:10],
        "run_metadata": {},
    }
    if requested_split is not None:
        summary["requested_split"] = requested_split
    write_json(out_dir / "proposal_summary.json", summary)
    return summary


def score_oracle_extraction(*, instances_path: str | Path, predictions_path: str | Path, output_dir: str | Path) -> dict:
    gold_rows, pred_rows, requested_split = _aligned_gold_rows(instances_path, predictions_path)
    scores = [oracle_extraction_instance_score(gold_rows[key], pred_rows.get(key, {})) for key in gold_rows]
    out_dir = ensure_dir(output_dir)
    write_jsonl(out_dir / "oracle_extraction_scores.jsonl", scores)
    scored_records = [record for record in scores if record["scored"]]
    summary = {
        "task": ORACLE_EXTRACTION_TASK,
        "instances": len(scores),
        "scored_instances": len(scored_records),
        "primary_metrics": {
            "field": _aggregate_prf(scored_records, ("field_metrics",)) if scored_records else prf(0, 0, 0),
            "row": _aggregate_prf(scored_records, ("row_metrics",)) if scored_records else prf(0, 0, 0),
            "row_exact_match": mean(record["row_exact_match"] for record in scored_records) if scored_records else 0.0,
            "item_exact_match": mean(record["item_exact_match"] for record in scored_records) if scored_records else 0.0,
            "complete_row_rate": safe_div(sum(record["analysis_buckets"]["complete_row_count"] for record in scored_records), sum(record["predicted_row_count"] for record in scored_records)),
            "empty_prediction_rate": safe_div(sum(record["analysis_buckets"]["empty_prediction_rate"] for record in scored_records), len(scored_records)),
        },
        "per_data_type": {
            data_type: {
                "instances": len(records),
                "field": _aggregate_prf(records, ("field_metrics",)),
                "row": _aggregate_prf(records, ("row_metrics",)),
                "row_exact_match": mean(record["row_exact_match"] for record in records) if records else 0.0,
                "item_exact_match": mean(record["item_exact_match"] for record in records) if records else 0.0,
                "complete_row_rate": safe_div(sum(record["analysis_buckets"]["complete_row_count"] for record in records), sum(record["predicted_row_count"] for record in records)),
                "empty_prediction_rate": safe_div(sum(record["analysis_buckets"]["empty_prediction_rate"] for record in records), len(records)),
            }
            for data_type, records in _group_by(scored_records, "data_type").items()
        },
        "per_field": _aggregate_field_breakdown(scored_records),
        "per_match_status": {
            status: {
                "instances": len(records),
                "scored_instances": len(scored_status_records),
                "field": _aggregate_prf(scored_status_records, ("field_metrics",)) if scored_status_records else prf(0, 0, 0),
                "row": _aggregate_prf(scored_status_records, ("row_metrics",)) if scored_status_records else prf(0, 0, 0),
                "row_exact_match": mean(record["row_exact_match"] for record in scored_status_records) if scored_status_records else 0.0,
                "empty_prediction_rate": safe_div(sum(record["analysis_buckets"]["empty_prediction_rate"] for record in scored_status_records), len(scored_status_records)),
            }
            for status, records in _group_by(scores, "match_status").items()
            for scored_status_records in [[record for record in records if record["scored"]]]
        },
        "error_buckets": {
            "empty_prediction_rate": safe_div(sum(record["analysis_buckets"]["empty_prediction_rate"] for record in scored_records), len(scored_records) if scored_records else 1),
        },
        "representative_failures": [row for row in scored_records if not row["item_exact_match"]][:10],
        "run_metadata": {},
    }
    if requested_split is not None:
        summary["requested_split"] = requested_split
    write_json(out_dir / "oracle_extraction_summary.json", summary)
    return summary


def score_routed_extraction(*, instances_path: str | Path, predictions_path: str | Path, output_dir: str | Path) -> dict:
    gold_rows, pred_rows, requested_split = _aligned_gold_rows(instances_path, predictions_path)
    scores = [routed_extraction_instance_score(gold_rows[key], pred_rows.get(key, {})) for key in gold_rows]
    out_dir = ensure_dir(output_dir)
    write_jsonl(out_dir / "routed_extraction_scores.jsonl", scores)
    summary = {
        "task": ROUTED_EXTRACTION_TASK,
        "instances": len(scores),
        "scored_instances": len(scores),
        "primary_metrics": {
            "proposal_structured": _aggregate_prf(scores, ("proposal_metrics",)),
            "proposal_subgroup": _aggregate_prf(scores, ("subgroup_metrics",)),
            "proposal_timepoint": _aggregate_prf(scores, ("timepoint_metrics",)),
            "field": _aggregate_prf(scores, ("field_metrics",)),
            "row": _aggregate_prf(scores, ("row_metrics",)),
            "setting_success_rate": mean(record["setting_success"] for record in scores) if scores else 0.0,
        },
        "per_data_type": {
            data_type: {
                "instances": len(records),
                "proposal_structured": _aggregate_prf(records, ("proposal_metrics",)),
                "field": _aggregate_prf(records, ("field_metrics",)),
            }
            for data_type, records in _group_by(scores, "data_type").items()
        },
        "error_buckets": {
            key: sum(record["error_buckets"][key] for record in scores)
            for key in ["routing_missing_count", "routing_extra_count", "timepoint_misalignment_count", "extraction_error_count", "pipeline_propagation_error_count"]
        },
        "representative_failures": [row for row in scores if not row["setting_success"]][:10],
        "run_metadata": {},
    }
    if requested_split is not None:
        summary["requested_split"] = requested_split
    write_json(out_dir / "routed_extraction_summary.json", summary)
    return summary


def score_all(*, run_dir: str | Path) -> dict:
    summaries = {}
    for task_name, scorer in (
        (SUPPORT_TASK, score_support),
        (PROPOSAL_TASK, score_proposal),
        (ORACLE_EXTRACTION_TASK, score_oracle_extraction),
        (ROUTED_EXTRACTION_TASK, score_routed_extraction),
    ):
        task_paths = resolve_task_paths(task_name=task_name, run_dir=run_dir)
        summaries[task_name] = scorer(instances_path=task_paths.instances_path, predictions_path=task_paths.predictions_path, output_dir=Path(run_dir) / "scores")
    return summaries
