from __future__ import annotations

import random
from collections import Counter, defaultdict
from itertools import product
from typing import Any

from .conditional_experiment import effect_measure_family, targeted_boundary_bucket
from .conditional_normalization import (
    arm_pair_key,
    normalize_arm_pairs,
    normalize_comparison_list,
    normalize_effect_measure,
    normalize_string_list,
    normalize_text,
    unordered_arm_pair_key,
)


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _safe_f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


_COMPARISON_STOPWORDS = {
    "vs",
    "versus",
    "compared",
    "comparison",
    "comparisons",
    "intervention",
    "interventions",
}

_GROUPED_MARKERS = (
    " or ",
    " and ",
    "combined",
    "combination",
    "class of",
    "classes of",
    "types of",
    "mixed",
)

_BROAD_COMPARISON_FAMILIES = {
    "inactive control": {"waiting list", "usual care", "standard care", "no treatment", "placebo"},
    "active control": {"usual care", "standard care"},
}


def _comparison_token_set(value: str) -> set[str]:
    return {
        token
        for token in normalize_text(value).split()
        if token and token not in _COMPARISON_STOPWORDS
    }


def _looks_grouped_comparison(value: str) -> bool:
    normalized = f" {normalize_text(value)} "
    return any(marker in normalized for marker in _GROUPED_MARKERS)


def _broad_narrow_match(left: str, right: str) -> bool:
    left_tokens = _comparison_token_set(left)
    right_tokens = _comparison_token_set(right)
    if not left_tokens or not right_tokens or left_tokens == right_tokens:
        return False
    if left_tokens.issubset(right_tokens) or right_tokens.issubset(left_tokens):
        return True
    left_normalized = normalize_text(left)
    right_normalized = normalize_text(right)
    for broad_label, narrow_labels in _BROAD_COMPARISON_FAMILIES.items():
        left_is_broad = broad_label in left_normalized
        right_is_broad = broad_label in right_normalized
        if left_is_broad == right_is_broad:
            continue
        narrow_text = right_normalized if left_is_broad else left_normalized
        if not any(label in narrow_text for label in narrow_labels):
            continue
        shared_tokens = left_tokens & right_tokens
        if shared_tokens:
            return True
    return False


def _grouped_atomic_match(left: str, right: str) -> bool:
    left_grouped = _looks_grouped_comparison(left)
    right_grouped = _looks_grouped_comparison(right)
    if left_grouped == right_grouped:
        return False
    left_tokens = _comparison_token_set(left)
    right_tokens = _comparison_token_set(right)
    if not left_tokens or not right_tokens:
        return False
    overlap = len(left_tokens & right_tokens)
    minimum = min(len(left_tokens), len(right_tokens))
    return overlap > 0 and overlap >= max(1, minimum // 2)


def _pair_comparison_errors(missing: list[str], extra: list[str]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    grouped_vs_atomic: list[dict[str, str]] = []
    broad_vs_narrow: list[dict[str, str]] = []
    used_pairs: set[tuple[str, str]] = set()
    for gold_value, pred_value in product(missing, extra):
        if (gold_value, pred_value) in used_pairs:
            continue
        if _grouped_atomic_match(gold_value, pred_value):
            grouped_vs_atomic.append({"gold": gold_value, "prediction": pred_value})
            used_pairs.add((gold_value, pred_value))
            continue
        if _broad_narrow_match(gold_value, pred_value):
            broad_vs_narrow.append({"gold": gold_value, "prediction": pred_value})
            used_pairs.add((gold_value, pred_value))
    return grouped_vs_atomic, broad_vs_narrow


def _classification_result(
    instance: dict[str, Any],
    parsed_prediction: dict[str, Any],
    *,
    target_key: str,
) -> dict[str, Any]:
    gold = normalize_text(instance["gold_target"].get(target_key, ""))
    pred = normalize_text(parsed_prediction.get(target_key, ""))
    if target_key == "candidate_effect_measure":
        gold = normalize_effect_measure(gold)
        pred = normalize_effect_measure(pred)
    correct = gold == pred
    return {
        "instance_id": instance["instance_id"],
        "review_id": instance["review_id"],
        "task_name": instance["task_name"],
        "evidence_mode": instance["evidence_mode"],
        "parse_status": "success",
        "schema_valid": True,
        "gold": gold,
        "prediction": pred,
        "correct": correct,
        "task_metadata": instance.get("task_metadata", {}),
        "metadata": instance.get("metadata", {}),
    }


def evaluate_data_type_instance(instance: dict[str, Any], parsed_prediction: dict[str, Any]) -> dict[str, Any]:
    return _classification_result(instance, parsed_prediction, target_key="data_type")


def evaluate_effect_measure_instance(
    instance: dict[str, Any],
    parsed_prediction: dict[str, Any],
    *,
    cascade_data_type_source: str = "gold",
) -> dict[str, Any]:
    result = _classification_result(instance, parsed_prediction, target_key="candidate_effect_measure")
    result["condition_data_type"] = normalize_text(instance["task_metadata"].get("condition_data_type", ""))
    result["cascade_data_type_source"] = cascade_data_type_source
    gold_family = effect_measure_family(result["gold"])
    pred_family = effect_measure_family(result["prediction"])
    result["gold_effect_measure_family"] = gold_family
    result["predicted_effect_measure_family"] = pred_family
    result["out_of_family_prediction"] = bool(result["prediction"]) and pred_family != gold_family
    result["targeted_boundary_bucket"] = targeted_boundary_bucket(result["gold"], result["prediction"])
    if cascade_data_type_source == "predicted":
        predicted_data_type = normalize_text(parsed_prediction.get("condition_data_type", ""))
        result["condition_data_type_matches"] = predicted_data_type == result["condition_data_type"]
    else:
        result["condition_data_type_matches"] = True
    return result


def evaluate_comparisons_instance(instance: dict[str, Any], parsed_prediction: dict[str, Any]) -> dict[str, Any]:
    gold = normalize_comparison_list(instance["gold_target"].get("comparisons", []))
    pred = normalize_comparison_list(parsed_prediction.get("comparisons", []))
    gold_set = set(gold)
    pred_set = set(pred)
    overlap = len(gold_set & pred_set)
    precision = _safe_div(overlap, len(pred_set))
    recall = _safe_div(overlap, len(gold_set))
    normalized_set_f1 = _safe_f1(precision, recall)
    missing = sorted(gold_set - pred_set)
    extra = sorted(pred_set - gold_set)
    grouped_vs_atomic, broad_vs_narrow = _pair_comparison_errors(missing, extra)
    return {
        "instance_id": instance["instance_id"],
        "review_id": instance["review_id"],
        "task_name": instance["task_name"],
        "evidence_mode": instance["evidence_mode"],
        "parse_status": "success",
        "schema_valid": True,
        "gold": gold,
        "prediction": pred,
        "gold_count": len(gold),
        "predicted_count": len(pred),
        "gold_is_empty": len(gold) == 0,
        "pred_empty": len(pred) == 0,
        "exact_set_match": gold_set == pred_set,
        "precision": precision,
        "recall": recall,
        "f1": normalized_set_f1,
        "normalized_set_f1": normalized_set_f1,
        "count_accuracy": len(gold) == len(pred),
        "comparison_count_accuracy": len(gold) == len(pred),
        "missing": missing,
        "extra": extra,
        "grouped_vs_atomic": grouped_vs_atomic,
        "broad_vs_narrow": broad_vs_narrow,
        "task_metadata": instance.get("task_metadata", {}),
        "metadata": instance.get("metadata", {}),
    }


def evaluate_arm_pairs_instance(instance: dict[str, Any], parsed_prediction: dict[str, Any]) -> dict[str, Any]:
    gold_pairs = normalize_arm_pairs(instance["gold_target"].get("arm_pairs", []))
    pred_pairs = normalize_arm_pairs(parsed_prediction.get("arm_pairs", []))
    gold_unordered = {unordered_arm_pair_key(pair) for pair in gold_pairs}
    pred_unordered = {unordered_arm_pair_key(pair) for pair in pred_pairs}
    overlap = len(gold_unordered & pred_unordered)
    precision = _safe_div(overlap, len(pred_unordered))
    recall = _safe_div(overlap, len(gold_unordered))
    gold_directed = {arm_pair_key(pair) for pair in gold_pairs}
    pred_directed = {arm_pair_key(pair) for pair in pred_pairs}
    direction_correct = len(gold_directed & pred_directed)
    return {
        "instance_id": instance["instance_id"],
        "review_id": instance["review_id"],
        "task_name": instance["task_name"],
        "evidence_mode": instance["evidence_mode"],
        "parse_status": "success",
        "schema_valid": True,
        "gold": gold_pairs,
        "prediction": pred_pairs,
        "unordered_precision": precision,
        "unordered_recall": recall,
        "unordered_f1": _safe_f1(precision, recall),
        "direction_accuracy": _safe_div(direction_correct, len(gold_directed)),
        "exact_pair_set_match": gold_directed == pred_directed,
        "task_metadata": instance.get("task_metadata", {}),
        "metadata": instance.get("metadata", {}),
    }


def evaluate_structured_instance(instance: dict[str, Any], parsed_prediction: dict[str, Any]) -> dict[str, Any]:
    gold_items = instance["gold_target"].get("items", [])
    pred_items = parsed_prediction.get("items", [])
    gold_comparisons = normalize_string_list([item.get("comparison", "") for item in gold_items])
    pred_comparisons = normalize_string_list([item.get("comparison", "") for item in pred_items])
    gold_set = set(gold_comparisons)
    pred_set = set(pred_comparisons)
    comp_overlap = len(gold_set & pred_set)
    comparison_precision = _safe_div(comp_overlap, len(pred_set))
    comparison_recall = _safe_div(comp_overlap, len(gold_set))

    def _map_items(items: list[dict[str, Any]]) -> dict[str, set[tuple[str, str]]]:
        mapping: dict[str, set[tuple[str, str]]] = {}
        for item in items:
            mapping[normalize_text(item.get("comparison", ""))] = {
                arm_pair_key(pair) for pair in normalize_arm_pairs(item.get("arm_pairs", []))
            }
        return mapping

    gold_map = _map_items(gold_items)
    pred_map = _map_items(pred_items)
    arm_tp = 0
    arm_pred_total = 0
    arm_gold_total = 0
    coherent = 0
    shared = sorted(gold_set & pred_set)
    for comparison in shared:
        gold_pairs = gold_map.get(comparison, set())
        pred_pairs = pred_map.get(comparison, set())
        arm_tp += len(gold_pairs & pred_pairs)
        arm_pred_total += len(pred_pairs)
        arm_gold_total += len(gold_pairs)
        if pred_pairs.issubset(gold_pairs):
            coherent += 1
    arm_precision = _safe_div(arm_tp, arm_pred_total)
    arm_recall = _safe_div(arm_tp, arm_gold_total)
    return {
        "instance_id": instance["instance_id"],
        "review_id": instance["review_id"],
        "task_name": instance["task_name"],
        "evidence_mode": instance["evidence_mode"],
        "parse_status": "success",
        "schema_valid": True,
        "gold": gold_items,
        "prediction": pred_items,
        "comparison_precision": comparison_precision,
        "comparison_recall": comparison_recall,
        "comparison_f1": _safe_f1(comparison_precision, comparison_recall),
        "arm_pair_precision": arm_precision,
        "arm_pair_recall": arm_recall,
        "arm_pair_f1": _safe_f1(arm_precision, arm_recall),
        "comparison_arm_coherence_rate": _safe_div(coherent, len(shared)),
        "exact_structured_match": gold_map == pred_map,
        "task_metadata": instance.get("task_metadata", {}),
        "metadata": instance.get("metadata", {}),
    }


def build_invalid_result(instance: dict[str, Any], prediction_payload: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "instance_id": instance["instance_id"],
        "review_id": instance["review_id"],
        "task_name": instance["task_name"],
        "evidence_mode": instance["evidence_mode"],
        "parse_status": prediction_payload.get("parse_status", "missing_prediction"),
        "schema_valid": prediction_payload.get("schema_valid", False),
        "error": prediction_payload.get("error", ""),
        "task_metadata": instance.get("task_metadata", {}),
        "metadata": instance.get("metadata", {}),
    }
    if instance["task_name"] == "comparisons":
        gold = normalize_comparison_list(instance["gold_target"].get("comparisons", []))
        payload["gold"] = gold
        payload["gold_count"] = len(gold)
        payload["gold_is_empty"] = len(gold) == 0
    return payload


def evaluate_conditional_instance(
    instance: dict[str, Any],
    prediction_payload: dict[str, Any],
    *,
    cascade_data_type_source: str = "gold",
) -> dict[str, Any]:
    if prediction_payload.get("parse_status") != "success":
        return build_invalid_result(instance, prediction_payload)
    parsed_prediction = prediction_payload.get("parsed_prediction_json", {})
    task_name = instance["task_name"]
    if task_name == "data_type":
        return evaluate_data_type_instance(instance, parsed_prediction)
    if task_name == "candidate_effect_measure":
        return evaluate_effect_measure_instance(
            instance,
            parsed_prediction,
            cascade_data_type_source=cascade_data_type_source,
        )
    if task_name == "comparisons":
        return evaluate_comparisons_instance(instance, parsed_prediction)
    if task_name == "arm_pairs":
        return evaluate_arm_pairs_instance(instance, parsed_prediction)
    if task_name == "comparisons_and_arm_pairs":
        return evaluate_structured_instance(instance, parsed_prediction)
    raise ValueError(f"unknown_conditional_task:{task_name}")


def _aggregate_classification(results: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [item for item in results if item["parse_status"] == "success"]
    labels = sorted({item["gold"] for item in valid} | {item["prediction"] for item in valid})
    confusion = {
        gold: {pred: 0 for pred in labels}
        for gold in labels
    }
    support = Counter()
    predicted = Counter()
    correct = Counter()
    for item in valid:
        support[item["gold"]] += 1
        predicted[item["prediction"]] += 1
        confusion[item["gold"]][item["prediction"]] += 1
        if item["correct"]:
            correct[item["gold"]] += 1
    per_class = {}
    macro_f1_sum = 0.0
    for label in labels:
        tp = correct[label]
        precision = _safe_div(tp, predicted[label])
        recall = _safe_div(tp, support[label])
        f1 = _safe_f1(precision, recall)
        per_class[label] = {
            "support": support[label],
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
        macro_f1_sum += f1
    accuracy = _safe_div(sum(1 for item in valid if item["correct"]), len(valid))
    return {
        "instance_count": len(results),
        "valid_instance_count": len(valid),
        "schema_validity": _safe_div(sum(1 for item in results if item["schema_valid"]), len(results)),
        "accuracy": accuracy,
        "macro_f1": _safe_div(macro_f1_sum, len(labels)),
        "per_class": per_class,
        "confusion_matrix": confusion,
    }


def _aggregate_comparison_slice(results: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [item for item in results if item["parse_status"] == "success"]
    return {
        "instance_count": len(results),
        "valid_instance_count": len(valid),
        "schema_validity": _safe_div(sum(1 for item in results if item["schema_valid"]), len(results)),
        "exact_set_match_rate": _safe_div(sum(1 for item in valid if item["exact_set_match"]), len(valid)),
        "mean_precision": _safe_div(sum(item["precision"] for item in valid), len(valid)),
        "mean_recall": _safe_div(sum(item["recall"] for item in valid), len(valid)),
        "mean_f1": _safe_div(sum(item["f1"] for item in valid), len(valid)),
        "normalized_set_f1": _safe_div(sum(item["normalized_set_f1"] for item in valid), len(valid)),
        "comparison_count_accuracy": _safe_div(sum(1 for item in valid if item["comparison_count_accuracy"]), len(valid)),
        "missing_comparison_total": sum(len(item["missing"]) for item in valid),
        "extra_comparison_total": sum(len(item["extra"]) for item in valid),
        "grouped_vs_atomic_error_count": sum(len(item["grouped_vs_atomic"]) for item in valid),
        "broad_vs_narrow_error_count": sum(len(item["broad_vs_narrow"]) for item in valid),
    }


def _aggregate_gold_empty_comparisons(results: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [item for item in results if item["parse_status"] == "success"]
    return {
        "instance_count": len(results),
        "valid_instance_count": len(valid),
        "schema_validity": _safe_div(sum(1 for item in results if item["schema_valid"]), len(results)),
        "pred_empty_rate": _safe_div(sum(1 for item in valid if item.get("pred_empty", False)), len(valid)),
        "hallucinated_comparison_rate": _safe_div(sum(1 for item in valid if item.get("predicted_count", 0) > 0), len(valid)),
        "mean_predicted_count": _safe_div(sum(item.get("predicted_count", 0) for item in valid), len(valid)),
    }


def _aggregate_comparisons(results: list[dict[str, Any]]) -> dict[str, Any]:
    all_instances = _aggregate_comparison_slice(results)
    gold_nonempty = [item for item in results if not item.get("gold_is_empty", False)]
    gold_empty = [item for item in results if item.get("gold_is_empty", False)]
    comparison_only = _aggregate_comparison_slice(gold_nonempty)
    aggregate = dict(all_instances)
    aggregate["primary_slice"] = "comparison_only"
    aggregate["all_instances"] = all_instances
    aggregate["comparison_only"] = comparison_only
    aggregate["gold_nonempty"] = comparison_only
    aggregate["gold_empty"] = _aggregate_gold_empty_comparisons(gold_empty)
    return aggregate


def _aggregate_arm_pairs(results: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [item for item in results if item["parse_status"] == "success"]
    return {
        "instance_count": len(results),
        "valid_instance_count": len(valid),
        "schema_validity": _safe_div(sum(1 for item in results if item["schema_valid"]), len(results)),
        "mean_unordered_precision": _safe_div(sum(item["unordered_precision"] for item in valid), len(valid)),
        "mean_unordered_recall": _safe_div(sum(item["unordered_recall"] for item in valid), len(valid)),
        "mean_unordered_f1": _safe_div(sum(item["unordered_f1"] for item in valid), len(valid)),
        "mean_direction_accuracy": _safe_div(sum(item["direction_accuracy"] for item in valid), len(valid)),
        "exact_pair_set_match_rate": _safe_div(sum(1 for item in valid if item["exact_pair_set_match"]), len(valid)),
        "stratified": {
            "parseable_from_comparison": _aggregate_arm_pairs_stratified(valid, "parseable_from_comparison"),
            "requires_evidence_grounding": _aggregate_arm_pairs_stratified(valid, "requires_evidence_grounding"),
        },
    }


def _aggregate_arm_pairs_stratified(results: list[dict[str, Any]], field: str) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in results:
        grouped[str(item.get("task_metadata", {}).get(field, False))].append(item)
    return {
        key: {
            "instance_count": len(rows),
            "mean_unordered_f1": _safe_div(sum(row["unordered_f1"] for row in rows), len(rows)),
            "mean_direction_accuracy": _safe_div(sum(row["direction_accuracy"] for row in rows), len(rows)),
        }
        for key, rows in sorted(grouped.items())
    }


def _aggregate_structured(results: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [item for item in results if item["parse_status"] == "success"]
    return {
        "instance_count": len(results),
        "valid_instance_count": len(valid),
        "schema_validity": _safe_div(sum(1 for item in results if item["schema_valid"]), len(results)),
        "mean_comparison_f1": _safe_div(sum(item["comparison_f1"] for item in valid), len(valid)),
        "mean_arm_pair_f1": _safe_div(sum(item["arm_pair_f1"] for item in valid), len(valid)),
        "mean_comparison_arm_coherence_rate": _safe_div(
            sum(item["comparison_arm_coherence_rate"] for item in valid), len(valid)
        ),
        "exact_structured_match_rate": _safe_div(sum(1 for item in valid if item["exact_structured_match"]), len(valid)),
    }


def _family_internal_confusions(results: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item in results:
        if item["parse_status"] != "success" or item.get("correct") is True:
            continue
        gold_family = item.get("gold_effect_measure_family", "")
        pred_family = item.get("predicted_effect_measure_family", "")
        if gold_family and gold_family == pred_family:
            counts[f"{item['gold']} -> {item['prediction']}"] += 1
    return dict(sorted(counts.items()))


def _targeted_boundary_errors(results: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item in results:
        if item["parse_status"] != "success" or item.get("correct") is True:
            continue
        bucket = item.get("targeted_boundary_bucket", "")
        if bucket:
            counts[bucket] += 1
    for bucket in [
        "std mean difference -> mean difference",
        "mean difference -> mean difference change from baseline",
        "odds ratio -> risk ratio",
        "peto odds ratio -> risk ratio",
        "risk difference -> risk ratio",
        "hazard ratio -> rate ratio",
        "rate ratio -> hazard ratio",
    ]:
        counts.setdefault(bucket, 0)
    return dict(sorted(counts.items()))


def aggregate_conditional_results(
    task_name: str,
    results: list[dict[str, Any]],
    *,
    cascade_data_type_source: str = "gold",
) -> dict[str, Any]:
    if task_name in {"data_type", "candidate_effect_measure"}:
        aggregate = _aggregate_classification(results)
        if task_name == "candidate_effect_measure":
            aggregate["cascade_data_type_source"] = cascade_data_type_source
            valid = [item for item in results if item["parse_status"] == "success"]
            per_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for item in valid:
                per_type[item.get("condition_data_type", "")].append(item)
            aggregate["per_data_type_accuracy"] = {
                key: _safe_div(sum(1 for row in rows if row["correct"]), len(rows))
                for key, rows in sorted(per_type.items())
            }
            aggregate["family_internal_confusions"] = _family_internal_confusions(valid)
            aggregate["out_of_family_prediction_count"] = sum(1 for item in valid if item.get("out_of_family_prediction"))
            aggregate["targeted_boundary_errors"] = _targeted_boundary_errors(valid)
        return aggregate
    if task_name == "comparisons":
        return _aggregate_comparisons(results)
    if task_name == "arm_pairs":
        return _aggregate_arm_pairs(results)
    if task_name == "comparisons_and_arm_pairs":
        return _aggregate_structured(results)
    raise ValueError(f"unknown_conditional_task:{task_name}")


def build_conditional_error_analysis(
    task_name: str,
    results: list[dict[str, Any]],
    *,
    sample_size: int,
    seed: int,
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    cases: list[dict[str, Any]] = []
    for item in results:
        if item["parse_status"] != "success":
            cases.append(
                {
                    "instance_id": item["instance_id"],
                    "review_id": item["review_id"],
                    "error_type": "invalid_output",
                    "details": item.get("error", ""),
                }
            )
            continue
        if task_name in {"data_type", "candidate_effect_measure"} and not item["correct"]:
            payload = {
                "instance_id": item["instance_id"],
                "review_id": item["review_id"],
                "error_type": "classification_mismatch",
                "gold": item["gold"],
                "prediction": item["prediction"],
            }
            if task_name == "candidate_effect_measure":
                payload["condition_data_type"] = item.get("condition_data_type", "")
                payload["gold_effect_measure_family"] = item.get("gold_effect_measure_family", "")
                payload["predicted_effect_measure_family"] = item.get("predicted_effect_measure_family", "")
                payload["out_of_family_prediction"] = item.get("out_of_family_prediction", False)
                payload["targeted_boundary_bucket"] = item.get("targeted_boundary_bucket", "")
            cases.append(payload)
        if task_name == "comparisons" and (item.get("missing") or item.get("extra")):
            cases.append(
                {
                    "instance_id": item["instance_id"],
                    "review_id": item["review_id"],
                    "error_type": "comparison_set_error",
                    "missing": item.get("missing", []),
                    "extra": item.get("extra", []),
                    "grouped_vs_atomic": item.get("grouped_vs_atomic", []),
                    "broad_vs_narrow": item.get("broad_vs_narrow", []),
                }
            )
        if task_name == "arm_pairs" and not item["exact_pair_set_match"]:
            cases.append(
                {
                    "instance_id": item["instance_id"],
                    "review_id": item["review_id"],
                    "error_type": "arm_pair_error",
                    "direction_accuracy": item["direction_accuracy"],
                    "unordered_f1": item["unordered_f1"],
                }
            )
        if task_name == "comparisons_and_arm_pairs" and not item["exact_structured_match"]:
            cases.append(
                {
                    "instance_id": item["instance_id"],
                    "review_id": item["review_id"],
                    "error_type": "structured_attachment_error",
                    "comparison_f1": item["comparison_f1"],
                    "arm_pair_f1": item["arm_pair_f1"],
                }
            )
    if len(cases) <= sample_size:
        return cases
    rng.shuffle(cases)
    return cases[:sample_size]
