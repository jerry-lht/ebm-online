from __future__ import annotations

import math
import random
import re
import string
from collections import Counter, defaultdict
from copy import deepcopy
from typing import Any

from .constants import DEFAULT_MATCH_THRESHOLD, FIELD_WEIGHTS, LIST_FIELDS, REQUIRED_FIELDS, STRING_FIELDS

_PUNCT_TRANSLATION = str.maketrans("", "", string.punctuation.replace("/", ""))
_MULTISPACE_RE = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    lowered = value.strip().lower().translate(_PUNCT_TRANSLATION)
    return _MULTISPACE_RE.sub(" ", lowered).strip()


def normalize_list(values: list[str]) -> list[str]:
    normalized = sorted({normalize_text(value) for value in values if normalize_text(value)})
    return normalized


def normalize_arm_pairs(values: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    normalized: list[dict[str, str]] = []
    for item in values:
        experimental = normalize_text(item.get("experimental_arm", ""))
        control = normalize_text(item.get("control_arm", ""))
        if not experimental and not control:
            continue
        key = (experimental, control)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(
            {
                "experimental_arm": experimental,
                "control_arm": control,
            }
        )
    normalized.sort(key=lambda item: (item["experimental_arm"], item["control_arm"]))
    return normalized


def normalize_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for field in STRING_FIELDS:
        normalized[field] = normalize_text(candidate.get(field, ""))
    for field in LIST_FIELDS:
        if field == "arm_pairs":
            normalized[field] = normalize_arm_pairs(candidate.get(field, []))
        else:
            normalized[field] = normalize_list(candidate.get(field, []))
    return normalized


def normalize_candidates(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    normalized: list[dict[str, Any]] = []
    invalid_candidate_count = 0
    for candidate in candidates:
        item = normalize_candidate(candidate)
        if not item["outcome_concept"]:
            invalid_candidate_count += 1
            continue
        normalized.append(item)
    return normalized, invalid_candidate_count


def deduplicate_candidates(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    duplicates = 0
    for candidate in candidates:
        key = repr(candidate)
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        unique.append(candidate)
    return unique, duplicates


def token_f1(left: str, right: str) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    left_counts = Counter(left.split())
    right_counts = Counter(right.split())
    overlap = sum((left_counts & right_counts).values())
    if overlap == 0:
        return 0.0
    precision = overlap / sum(left_counts.values())
    recall = overlap / sum(right_counts.values())
    return 2 * precision * recall / (precision + recall)


def set_f1(left: list[str], right: list[str]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    left_set = set(left)
    right_set = set(right)
    overlap = len(left_set & right_set)
    if overlap == 0:
        return 0.0
    precision = overlap / len(left_set)
    recall = overlap / len(right_set)
    return 2 * precision * recall / (precision + recall)


def arm_pair_f1(left: list[dict[str, str]], right: list[dict[str, str]]) -> float:
    left_flat = [f'{item["experimental_arm"]}|||{item["control_arm"]}' for item in left]
    right_flat = [f'{item["experimental_arm"]}|||{item["control_arm"]}' for item in right]
    return set_f1(left_flat, right_flat)


def exact_match(left: str, right: str) -> float:
    if not left and not right:
        return 1.0
    return 1.0 if left == right else 0.0


def candidate_similarity(prediction: dict[str, Any], gold: dict[str, Any]) -> tuple[float, dict[str, float]]:
    field_scores = {
        "outcome_concept": token_f1(prediction["outcome_concept"], gold["outcome_concept"]),
        "data_type": exact_match(prediction["data_type"], gold["data_type"]),
        "candidate_effect_measure": exact_match(
            prediction["candidate_effect_measure"], gold["candidate_effect_measure"]
        ),
        "comparisons": set_f1(prediction["comparisons"], gold["comparisons"]),
        "arm_pairs": arm_pair_f1(prediction["arm_pairs"], gold["arm_pairs"]),
        "subgroup_candidates": set_f1(
            prediction["subgroup_candidates"], gold["subgroup_candidates"]
        ),
        "timepoints": set_f1(prediction["timepoints"], gold["timepoints"]),
        "reported_outcome_measures": set_f1(
            prediction["reported_outcome_measures"], gold["reported_outcome_measures"]
        ),
    }
    total = sum(FIELD_WEIGHTS[field] * field_scores[field] for field in FIELD_WEIGHTS)
    return total, field_scores


def _hungarian(costs: list[list[float]]) -> list[int]:
    size = len(costs)
    u = [0.0] * (size + 1)
    v = [0.0] * (size + 1)
    p = [0] * (size + 1)
    way = [0] * (size + 1)
    for i in range(1, size + 1):
        p[0] = i
        j0 = 0
        minv = [math.inf] * (size + 1)
        used = [False] * (size + 1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = math.inf
            j1 = 0
            for j in range(1, size + 1):
                if used[j]:
                    continue
                cur = costs[i0 - 1][j - 1] - u[i0] - v[j]
                if cur < minv[j]:
                    minv[j] = cur
                    way[j] = j0
                if minv[j] < delta:
                    delta = minv[j]
                    j1 = j
            for j in range(size + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    assignment = [-1] * size
    for j in range(1, size + 1):
        if p[j] != 0:
            assignment[p[j] - 1] = j - 1
    return assignment


def match_candidates(
    predictions: list[dict[str, Any]],
    golds: list[dict[str, Any]],
    *,
    threshold: float = DEFAULT_MATCH_THRESHOLD,
) -> tuple[list[dict[str, Any]], list[int], list[int]]:
    if not predictions or not golds:
        return [], list(range(len(predictions))), list(range(len(golds)))
    scores: list[list[tuple[float, dict[str, float]]]] = []
    max_score = 1.0
    for prediction in predictions:
        row: list[tuple[float, dict[str, float]]] = []
        for gold in golds:
            row.append(candidate_similarity(prediction, gold))
        scores.append(row)
    size = max(len(predictions), len(golds))
    costs = [[max_score for _ in range(size)] for _ in range(size)]
    for i in range(len(predictions)):
        for j in range(len(golds)):
            costs[i][j] = max_score - scores[i][j][0]
    assignment = _hungarian(costs)
    matches: list[dict[str, Any]] = []
    matched_pred: set[int] = set()
    matched_gold: set[int] = set()
    for pred_index, gold_index in enumerate(assignment[: len(predictions)]):
        if gold_index < 0 or gold_index >= len(golds):
            continue
        score, field_scores = scores[pred_index][gold_index]
        if score < threshold:
            continue
        matched_pred.add(pred_index)
        matched_gold.add(gold_index)
        matches.append(
            {
                "pred_index": pred_index,
                "gold_index": gold_index,
                "score": score,
                "field_scores": field_scores,
            }
        )
    unmatched_pred = [index for index in range(len(predictions)) if index not in matched_pred]
    unmatched_gold = [index for index in range(len(golds)) if index not in matched_gold]
    return matches, unmatched_pred, unmatched_gold


def _safe_f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def evaluate_review(
    review_id: str,
    prediction_candidates: list[dict[str, Any]],
    gold_candidates: list[dict[str, Any]],
    metadata: dict[str, Any],
    *,
    split: str,
    threshold: float = DEFAULT_MATCH_THRESHOLD,
    schema_valid: bool = True,
    parse_status: str = "success",
) -> dict[str, Any]:
    normalized_predictions, invalid_candidate_count = normalize_candidates(prediction_candidates)
    deduped_predictions, duplicate_prediction_count = deduplicate_candidates(normalized_predictions)
    normalized_gold, gold_invalid_count = normalize_candidates(gold_candidates)
    matches, unmatched_pred, unmatched_gold = match_candidates(
        deduped_predictions,
        normalized_gold,
        threshold=threshold,
    )
    pred_count = len(deduped_predictions)
    gold_count = len(normalized_gold)
    matched_count = len(matches)
    precision = matched_count / pred_count if pred_count else 0.0
    recall = matched_count / gold_count if gold_count else 0.0
    field_empty_counts = {field: 0 for field in REQUIRED_FIELDS}
    for candidate in deduped_predictions:
        for field in STRING_FIELDS:
            if candidate[field] == "":
                field_empty_counts[field] += 1
        for field in LIST_FIELDS:
            if not candidate[field]:
                field_empty_counts[field] += 1
    matched_field_totals = defaultdict(float)
    for match in matches:
        for field, score in match["field_scores"].items():
            matched_field_totals[field] += score
    matched_field_metrics = {
        field: (matched_field_totals[field] / matched_count if matched_count else 0.0)
        for field in (
            "outcome_concept",
            "data_type",
            "candidate_effect_measure",
            "comparisons",
            "arm_pairs",
            "subgroup_candidates",
            "timepoints",
            "reported_outcome_measures",
        )
    }
    return {
        "review_id": review_id,
        "split": split,
        "schema_valid": schema_valid,
        "parse_status": parse_status,
        "invalid_candidate_count": invalid_candidate_count,
        "gold_invalid_candidate_count": gold_invalid_count,
        "pred_candidate_count": pred_count,
        "gold_candidate_count": gold_count,
        "matched_pair_count": matched_count,
        "precision": precision,
        "recall": recall,
        "f1": _safe_f1(precision, recall),
        "count_error": pred_count - gold_count,
        "absolute_count_error": abs(pred_count - gold_count),
        "non_empty_output": pred_count > 0,
        "duplicate_prediction_count": duplicate_prediction_count,
        "duplicate_prediction_rate": (
            duplicate_prediction_count / len(normalized_predictions) if normalized_predictions else 0.0
        ),
        "zero_candidate_review_error": gold_count > 0 and pred_count == 0,
        "field_empty_counts": field_empty_counts,
        "matched_field_metrics": matched_field_metrics,
        "metadata": deepcopy(metadata),
        "unmatched_prediction_indices": unmatched_pred,
        "unmatched_gold_indices": unmatched_gold,
        "normalized_predictions": deduped_predictions,
        "normalized_gold": normalized_gold,
        "matches": matches,
    }


def aggregate_review_metrics(review_results: list[dict[str, Any]]) -> dict[str, Any]:
    if not review_results:
        return {}
    macro_precision = sum(item["precision"] for item in review_results) / len(review_results)
    macro_recall = sum(item["recall"] for item in review_results) / len(review_results)
    macro_f1 = sum(item["f1"] for item in review_results) / len(review_results)
    micro_pred = sum(item["pred_candidate_count"] for item in review_results)
    micro_gold = sum(item["gold_candidate_count"] for item in review_results)
    micro_match = sum(item["matched_pair_count"] for item in review_results)
    micro_precision = micro_match / micro_pred if micro_pred else 0.0
    micro_recall = micro_match / micro_gold if micro_gold else 0.0
    total_candidates = sum(item["pred_candidate_count"] for item in review_results)
    empty_field_counts = defaultdict(int)
    for item in review_results:
        for field, count in item["field_empty_counts"].items():
            empty_field_counts[field] += count
    field_empty_rate = {
        field: (empty_field_counts[field] / total_candidates if total_candidates else 0.0)
        for field in REQUIRED_FIELDS
    }
    field_metric_sums = defaultdict(float)
    matched_reviews = sum(1 for item in review_results if item["matched_pair_count"] > 0)
    total_matches = sum(item["matched_pair_count"] for item in review_results)
    for item in review_results:
        for field, value in item["matched_field_metrics"].items():
            field_metric_sums[field] += value * item["matched_pair_count"]
    field_metrics = {
        field: (field_metric_sums[field] / total_matches if total_matches else 0.0)
        for field in (
            "outcome_concept",
            "data_type",
            "candidate_effect_measure",
            "comparisons",
            "arm_pairs",
            "subgroup_candidates",
            "timepoints",
            "reported_outcome_measures",
        )
    }
    return {
        "review_count": len(review_results),
        "schema_validity": sum(1 for item in review_results if item["schema_valid"]) / len(review_results),
        "non_empty_output_rate": sum(1 for item in review_results if item["non_empty_output"]) / len(review_results),
        "macro_review_precision": macro_precision,
        "macro_review_recall": macro_recall,
        "macro_review_f1": macro_f1,
        "micro_candidate_precision": micro_precision,
        "micro_candidate_recall": micro_recall,
        "micro_candidate_f1": _safe_f1(micro_precision, micro_recall),
        "mean_predicted_candidate_count_error": (
            sum(item["count_error"] for item in review_results) / len(review_results)
        ),
        "mean_absolute_candidate_count_error": (
            sum(item["absolute_count_error"] for item in review_results) / len(review_results)
        ),
        "zero_candidate_review_error_rate": (
            sum(1 for item in review_results if item["zero_candidate_review_error"]) / len(review_results)
        ),
        "invalid_candidate_count": sum(item["invalid_candidate_count"] for item in review_results),
        "duplicate_prediction_rate": (
            sum(item["duplicate_prediction_count"] for item in review_results) / total_candidates
            if total_candidates
            else 0.0
        ),
        "empty_field_rate": field_empty_rate,
        "field_level_metrics": field_metrics,
        "matched_review_count": matched_reviews,
    }


def summarize_by_bucket(
    review_results: list[dict[str, Any]],
    bucket_field: str,
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in review_results:
        grouped[str(item["metadata"].get(bucket_field, ""))].append(item)
    return {bucket: aggregate_review_metrics(rows) for bucket, rows in sorted(grouped.items())}


def build_error_analysis_sample(
    review_results: list[dict[str, Any]],
    *,
    sample_size: int = 50,
    seed: int = 20260519,
) -> list[dict[str, Any]]:
    unmatched_cases: list[dict[str, Any]] = []
    for item in review_results:
        for pred_index in item["unmatched_prediction_indices"]:
            unmatched_cases.append(
                {
                    "review_id": item["review_id"],
                    "case_type": "unmatched_prediction",
                    "candidate": item["normalized_predictions"][pred_index],
                    "proposed_error_type": "",
                }
            )
        for gold_index in item["unmatched_gold_indices"]:
            unmatched_cases.append(
                {
                    "review_id": item["review_id"],
                    "case_type": "unmatched_gold",
                    "candidate": item["normalized_gold"][gold_index],
                    "proposed_error_type": "",
                }
            )
    rng = random.Random(seed)
    if len(unmatched_cases) <= sample_size:
        return unmatched_cases
    rng.shuffle(unmatched_cases)
    return unmatched_cases[:sample_size]

