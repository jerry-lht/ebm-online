"""Shared item matching helpers for routing and end-to-end scoring."""

from __future__ import annotations

from collections import defaultdict

from .normalize import item_key, normalize_text_loose


def comparison_key(item: dict) -> str:
    return item_key(item, strict=False)[0]


def comparison_subgroup_key(item: dict) -> tuple[str, str]:
    comparison, subgroup, _ = item_key(item, strict=False)
    return comparison, subgroup


def has_empty_timepoints(item: dict) -> bool:
    return len(item_key(item, strict=False)[2]) == 0


def has_empty_subgroup(item: dict) -> bool:
    return item_key(item, strict=False)[1] == ""


def item_has_supported_timepoints(item: dict, evidence_strings: list[str]) -> bool:
    timepoints = item.get("timepoints") or []
    if not timepoints:
        return False
    haystack = "\n".join(evidence_strings)
    return all(normalize_text_loose(value) in haystack for value in timepoints if normalize_text_loose(value))


def item_has_supported_subgroup(item: dict, subgroup_candidates: list[str]) -> bool:
    subgroup = normalize_text_loose(item.get("subgroup"))
    if not subgroup:
        return False
    candidate_keys = {normalize_text_loose(candidate) for candidate in subgroup_candidates or [] if normalize_text_loose(candidate)}
    return subgroup in candidate_keys


def match_items_discovery_aware(gold_items: list[dict], predicted_items: list[dict]) -> dict:
    """Match items with an empty-gold-timepoint fallback.

    First consume exact normalized matches. Remaining predicted items may match
    remaining gold items with empty timepoints using comparison + subgroup only.
    """

    exact_pool = defaultdict(list)
    for gold_index, gold_item in enumerate(gold_items):
        exact_pool[item_key(gold_item, strict=False)].append(gold_index)

    used_gold: set[int] = set()
    used_pred: set[int] = set()
    matches = []

    for pred_index, predicted_item in enumerate(predicted_items):
        key = item_key(predicted_item, strict=False)
        while exact_pool[key] and exact_pool[key][0] in used_gold:
            exact_pool[key].pop(0)
        if exact_pool[key]:
            gold_index = exact_pool[key].pop(0)
            used_gold.add(gold_index)
            used_pred.add(pred_index)
            matches.append(
                {
                    "gold_index": gold_index,
                    "pred_index": pred_index,
                    "match_type": "exact",
                    "used_empty_gold_subgroup": False,
                    "used_empty_gold_timepoint": False,
                }
            )

    relaxed_pool = defaultdict(list)
    for gold_index, gold_item in enumerate(gold_items):
        if gold_index in used_gold or not has_empty_timepoints(gold_item):
            continue
        relaxed_pool[comparison_subgroup_key(gold_item)].append(gold_index)

    for pred_index, predicted_item in enumerate(predicted_items):
        if pred_index in used_pred:
            continue
        key = comparison_subgroup_key(predicted_item)
        if relaxed_pool[key]:
            gold_index = relaxed_pool[key].pop(0)
            used_gold.add(gold_index)
            used_pred.add(pred_index)
            matches.append(
                {
                    "gold_index": gold_index,
                    "pred_index": pred_index,
                    "match_type": "empty_gold_timepoint_discovery",
                    "used_empty_gold_subgroup": False,
                    "used_empty_gold_timepoint": True,
                }
            )

    matches.sort(key=lambda row: row["pred_index"])
    return {
        "matches": matches,
        "missing_gold_indices": [index for index in range(len(gold_items)) if index not in used_gold],
        "extra_pred_indices": [index for index in range(len(predicted_items)) if index not in used_pred],
    }


def match_items_omission_aware(
    gold_items: list[dict],
    predicted_items: list[dict],
    *,
    evidence_strings: list[str] | None = None,
    subgroup_candidates: list[str] | None = None,
) -> dict:
    """Match items while allowing supported subgroup/timepoint recovery.

    Exact normalized matches are consumed first. Remaining predicted items may
    match remaining gold items when gold omitted subgroup and/or timepoint but
    the predicted value is supported by setting-level evidence.
    """

    exact_pool = defaultdict(list)
    for gold_index, gold_item in enumerate(gold_items):
        exact_pool[item_key(gold_item, strict=False)].append(gold_index)

    used_gold: set[int] = set()
    used_pred: set[int] = set()
    matches = []
    evidence_strings = evidence_strings or []
    subgroup_candidates = subgroup_candidates or []

    for pred_index, predicted_item in enumerate(predicted_items):
        key = item_key(predicted_item, strict=False)
        while exact_pool[key] and exact_pool[key][0] in used_gold:
            exact_pool[key].pop(0)
        if exact_pool[key]:
            gold_index = exact_pool[key].pop(0)
            used_gold.add(gold_index)
            used_pred.add(pred_index)
            matches.append(
                {
                    "gold_index": gold_index,
                    "pred_index": pred_index,
                    "match_type": "exact",
                    "used_empty_gold_subgroup": False,
                    "used_empty_gold_timepoint": False,
                }
            )

    for pred_index, predicted_item in enumerate(predicted_items):
        if pred_index in used_pred:
            continue
        pred_comparison, pred_subgroup, pred_timepoints = item_key(predicted_item, strict=False)
        for gold_index, gold_item in enumerate(gold_items):
            if gold_index in used_gold:
                continue
            gold_comparison, gold_subgroup, gold_timepoints = item_key(gold_item, strict=False)
            if pred_comparison != gold_comparison:
                continue
            subgroup_relaxed = has_empty_subgroup(gold_item) and item_has_supported_subgroup(predicted_item, subgroup_candidates)
            timepoint_relaxed = has_empty_timepoints(gold_item) and item_has_supported_timepoints(predicted_item, evidence_strings)
            subgroup_matches = pred_subgroup == gold_subgroup or subgroup_relaxed
            timepoint_matches = pred_timepoints == gold_timepoints or timepoint_relaxed
            if not subgroup_matches or not timepoint_matches:
                continue
            if not subgroup_relaxed and not timepoint_relaxed:
                continue
            used_gold.add(gold_index)
            used_pred.add(pred_index)
            if subgroup_relaxed and timepoint_relaxed:
                match_type = "empty_gold_subgroup_timepoint_discovery"
            elif subgroup_relaxed:
                match_type = "empty_gold_subgroup_discovery"
            else:
                match_type = "empty_gold_timepoint_discovery"
            matches.append(
                {
                    "gold_index": gold_index,
                    "pred_index": pred_index,
                    "match_type": match_type,
                    "used_empty_gold_subgroup": subgroup_relaxed,
                    "used_empty_gold_timepoint": timepoint_relaxed,
                }
            )
            break

    matches.sort(key=lambda row: row["pred_index"])
    return {
        "matches": matches,
        "missing_gold_indices": [index for index in range(len(gold_items)) if index not in used_gold],
        "extra_pred_indices": [index for index in range(len(predicted_items)) if index not in used_pred],
    }
