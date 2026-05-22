from __future__ import annotations

from pathlib import Path
from typing import Any

from .conditional_constants import CONDITIONAL_PROMPT_VERSION
from .conditional_normalization import normalize_effect_measure, normalize_text, slugify

EFFECT_MEASURE_TASK = "candidate_effect_measure"
COMPARISONS_TASK = "comparisons"
COMPARISONS_REVIEW_LEVEL_PROMPT_VERSION = "conditional_task_aware_v6_comparisons_review_level"
COMPARISONS_BENCHMARK_PROMPT_VERSION = "conditional_task_aware_v8_comparisons_benchmark_aligned"

EVIDENCE_STRATEGIES = (
    "standard_fulltext_evidence",
    "family_aware_evidence",
)

DECISION_STRATEGIES = (
    "free_generation",
    "constrained_selection",
)

DEFAULT_EVIDENCE_STRATEGY = "standard_fulltext_evidence"
DEFAULT_DECISION_STRATEGY = "free_generation"

CONFIG_ALIASES = {
    (DEFAULT_EVIDENCE_STRATEGY, DEFAULT_DECISION_STRATEGY): "ft_freegen_baseline",
    ("family_aware_evidence", DEFAULT_DECISION_STRATEGY): "ft_familyevidence_freegen",
    (DEFAULT_EVIDENCE_STRATEGY, "constrained_selection"): "ft_constrainedselection",
    ("family_aware_evidence", "constrained_selection"): "ft_familyevidence_constrainedselection",
}

DECISION_PROMPT_VERSIONS = {
    "free_generation": "conditional_task_aware_v4_effect_measure_official_freegen",
    "constrained_selection": "conditional_task_aware_v5_effect_measure_official_selection",
}

COMPARISONS_DECISION_PROMPT_VERSIONS = {
    "free_generation": CONDITIONAL_PROMPT_VERSION,
    "constrained_selection": "conditional_task_aware_v7_comparisons_selection",
}

FEW_SHOT_SET_DIR = Path(__file__).resolve().parent / "prompts" / "conditional_candidate_effect_measure_boundary_few_shots_v1"
COMPARISON_FEW_SHOT_SET_DIR = Path(__file__).resolve().parent / "prompts" / "conditional_comparisons_boundary_few_shots_v1"
FEW_SHOT_SETS = {
    "effect_measure_boundary_v1": FEW_SHOT_SET_DIR / "few_shots.txt",
    "comparisons_boundary_v1": COMPARISON_FEW_SHOT_SET_DIR / "few_shots.txt",
}

EFFECT_MEASURE_FAMILIES = {
    "risk ratio": "dichotomous",
    "odds ratio": "dichotomous",
    "peto odds ratio": "dichotomous",
    "risk difference": "dichotomous",
    "mean difference": "continuous",
    "std mean difference": "continuous",
    "mean difference change from baseline": "continuous",
    "hazard ratio": "contrast level",
    "rate ratio": "contrast level",
}

TARGETED_BOUNDARY_BUCKETS = {
    ("std mean difference", "mean difference"): "std mean difference -> mean difference",
    ("mean difference", "mean difference change from baseline"): "mean difference -> mean difference change from baseline",
    ("odds ratio", "risk ratio"): "odds ratio -> risk ratio",
    ("peto odds ratio", "risk ratio"): "peto odds ratio -> risk ratio",
    ("risk difference", "risk ratio"): "risk difference -> risk ratio",
    ("hazard ratio", "rate ratio"): "hazard ratio -> rate ratio",
    ("rate ratio", "hazard ratio"): "rate ratio -> hazard ratio",
}

_COMPARISON_VARIANT_ALIASES = {
    (COMPARISONS_REVIEW_LEVEL_PROMPT_VERSION, "", "free_generation"): "comparisons_prompt_review_level_v1",
    (COMPARISONS_REVIEW_LEVEL_PROMPT_VERSION, "comparisons_boundary_v1", "free_generation"): "comparisons_prompt_review_level_v1__fewshot_comparisons_boundary_v1",
    (COMPARISONS_BENCHMARK_PROMPT_VERSION, "", "free_generation"): "comparisons_prompt_benchmark_aligned_v1",
    (COMPARISONS_BENCHMARK_PROMPT_VERSION, "comparisons_boundary_v1", "free_generation"): "comparisons_prompt_benchmark_aligned_v1__fewshot_comparisons_boundary_v1",
    ("conditional_task_aware_v7_comparisons_selection", "", "constrained_selection"): "comparisons_constrained_selection_v1",
    ("conditional_task_aware_v7_comparisons_selection", "comparisons_boundary_v1", "constrained_selection"): "comparisons_constrained_selection_v1__fewshot_comparisons_boundary_v1",
}


def resolve_effect_measure_evidence_strategy(task_name: str, strategy: str | None) -> str:
    if task_name != EFFECT_MEASURE_TASK:
        return DEFAULT_EVIDENCE_STRATEGY
    candidate = (strategy or "").strip() or DEFAULT_EVIDENCE_STRATEGY
    if candidate not in EVIDENCE_STRATEGIES:
        raise ValueError(f"unknown_evidence_strategy:{candidate}")
    return candidate


def resolve_effect_measure_decision_strategy(task_name: str, strategy: str | None) -> str:
    if task_name not in {EFFECT_MEASURE_TASK, COMPARISONS_TASK}:
        return DEFAULT_DECISION_STRATEGY
    candidate = (strategy or "").strip() or DEFAULT_DECISION_STRATEGY
    if candidate not in DECISION_STRATEGIES:
        raise ValueError(f"unknown_decision_strategy:{candidate}")
    return candidate


def resolve_conditional_prompt_version(
    task_name: str,
    *,
    prompt_version: str | None,
    decision_strategy: str,
    default_prompt_version: str,
) -> str:
    explicit = (prompt_version or "").strip()
    if explicit:
        return explicit
    if task_name == EFFECT_MEASURE_TASK:
        return DECISION_PROMPT_VERSIONS[decision_strategy]
    if task_name == COMPARISONS_TASK:
        return COMPARISONS_DECISION_PROMPT_VERSIONS.get(decision_strategy, default_prompt_version)
    return default_prompt_version


def conditional_strategy_dir_name(
    task_name: str,
    *,
    evidence_strategy: str,
    decision_strategy: str,
) -> str | None:
    if task_name != EFFECT_MEASURE_TASK:
        return None
    return CONFIG_ALIASES.get((evidence_strategy, decision_strategy), f"{evidence_strategy}__{decision_strategy}")


def _comparison_result_variant(prompt_version: str, few_shot_set: str, decision_strategy: str) -> str:
    key = (prompt_version, few_shot_set, decision_strategy)
    if key in _COMPARISON_VARIANT_ALIASES:
        return _COMPARISON_VARIANT_ALIASES[key]
    parts: list[str] = []
    if prompt_version and prompt_version != CONDITIONAL_PROMPT_VERSION:
        parts.append(slugify(prompt_version, fallback="prompt"))
    if few_shot_set:
        parts.append(f"fewshot_{slugify(few_shot_set, fallback='set')}")
    return "__".join(parts)


def conditional_result_variant(
    task_name: str,
    *,
    evidence_strategy: str,
    decision_strategy: str,
    few_shot_set: str | None,
    prompt_version: str | None = None,
) -> str:
    base = conditional_strategy_dir_name(
        task_name,
        evidence_strategy=evidence_strategy,
        decision_strategy=decision_strategy,
    )
    normalized_prompt_version = (prompt_version or "").strip()
    normalized_few_shot_set = (few_shot_set or "").strip()
    if task_name == COMPARISONS_TASK:
        return _comparison_result_variant(normalized_prompt_version, normalized_few_shot_set, decision_strategy)
    if base is None:
        return ""
    if not normalized_few_shot_set:
        return base
    return f"{base}__fewshot_{slugify(normalized_few_shot_set, fallback='set')}"


def effect_measure_family(label: str) -> str:
    return EFFECT_MEASURE_FAMILIES.get(normalize_effect_measure(label), "")


def targeted_boundary_bucket(gold: str, prediction: str) -> str:
    return TARGETED_BOUNDARY_BUCKETS.get(
        (normalize_effect_measure(gold), normalize_effect_measure(prediction)),
        "",
    )


def load_few_shot_text(few_shot_set: str | None) -> str:
    key = (few_shot_set or "").strip()
    if not key:
        return ""
    try:
        path = FEW_SHOT_SETS[key]
    except KeyError as exc:
        raise ValueError(f"unknown_few_shot_set:{key}") from exc
    return path.read_text(encoding="utf-8").strip()


def conditional_target_label(task_name: str, row: dict[str, Any]) -> str:
    if task_name == "data_type":
        return str(row.get("gold_target", {}).get("data_type", ""))
    if task_name == "candidate_effect_measure":
        return str(row.get("gold_target", {}).get("candidate_effect_measure", ""))
    if task_name == "comparisons":
        return str(len(row.get("gold_target", {}).get("comparisons", [])))
    if task_name == "arm_pairs":
        return str(len(row.get("gold_target", {}).get("arm_pairs", [])))
    if task_name == "comparisons_and_arm_pairs":
        return str(len(row.get("gold_target", {}).get("items", [])))
    raise ValueError(f"unknown_conditional_task:{task_name}")


def build_stratified_subset(
    rows: list[dict[str, Any]],
    *,
    size: int,
    stratify_labels: list[str],
    seed: int,
) -> list[dict[str, Any]]:
    if size <= 0:
        raise ValueError("size_must_be_positive")
    if len(rows) <= size:
        return list(rows)
    if len(rows) != len(stratify_labels):
        raise ValueError("rows_and_labels_must_align")

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row, label in zip(rows, stratify_labels, strict=True):
        grouped.setdefault(normalize_text(label), []).append(row)

    labels = sorted(grouped)
    if size < len(labels):
        ranked = sorted(labels, key=lambda label: (-len(grouped[label]), label))
        keep = set(ranked[:size])
        grouped = {label: grouped[label] for label in labels if label in keep}
        labels = sorted(grouped)

    allocation = {label: 1 for label in labels}
    remaining = size - len(labels)
    capacities = {label: max(len(grouped[label]) - 1, 0) for label in labels}
    total_capacity = sum(capacities.values())
    remainders: list[tuple[float, str]] = []
    for label in labels:
        capacity = capacities[label]
        if remaining <= 0 or capacity == 0 or total_capacity == 0:
            remainders.append((0.0, label))
            continue
        ideal = remaining * (capacity / total_capacity)
        extra = min(int(ideal), capacity)
        allocation[label] += extra
        remainders.append((ideal - extra, label))

    allocated = sum(allocation.values())
    for _, label in sorted(remainders, key=lambda item: (-item[0], item[1])):
        if allocated >= size:
            break
        if allocation[label] >= len(grouped[label]):
            continue
        allocation[label] += 1
        allocated += 1

    if allocated < size:
        for label in sorted(labels, key=lambda item: (-len(grouped[item]), item)):
            if allocated >= size:
                break
            spare = len(grouped[label]) - allocation[label]
            if spare <= 0:
                continue
            take = min(spare, size - allocated)
            allocation[label] += take
            allocated += take

    selected: list[dict[str, Any]] = []
    for label in labels:
        ordered = sorted(
            grouped[label],
            key=lambda row: (
                normalize_text(str(row.get("review_id", ""))),
                normalize_text(str(row.get("instance_id", ""))),
            ),
        )
        if ordered:
            rotation = sum(ord(ch) for ch in f"{label}:{seed}") % len(ordered)
            ordered = ordered[rotation:] + ordered[:rotation]
        selected.extend(ordered[: allocation[label]])

    selected.sort(key=lambda row: normalize_text(str(row.get("instance_id", ""))))
    return selected[:size]
