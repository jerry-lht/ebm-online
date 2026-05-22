from __future__ import annotations

REQUIRED_FIELDS = (
    "outcome_concept",
    "data_type",
    "candidate_effect_measure",
    "comparisons",
    "arm_pairs",
    "subgroup_candidates",
    "timepoints",
    "reported_outcome_measures",
)

LIST_FIELDS = (
    "comparisons",
    "arm_pairs",
    "subgroup_candidates",
    "timepoints",
    "reported_outcome_measures",
)

STRING_FIELDS = (
    "outcome_concept",
    "data_type",
    "candidate_effect_measure",
)

CORE_MATCH_FIELDS = (
    "outcome_concept",
    "data_type",
    "candidate_effect_measure",
    "comparisons",
    "arm_pairs",
    "subgroup_candidates",
    "timepoints",
)

FIELD_WEIGHTS = {
    "outcome_concept": 0.25,
    "data_type": 0.15,
    "candidate_effect_measure": 0.15,
    "comparisons": 0.20,
    "arm_pairs": 0.15,
    "subgroup_candidates": 0.05,
    "timepoints": 0.05,
}

DEFAULT_MATCH_THRESHOLD = 0.65
DEFAULT_DEV_RATIO = 0.2
DEFAULT_SPLIT_SEED = 20260519
PROMPT_VERSION = "abstract_sr_direct_generation_v2_canonicalized"
SPLIT_VERSION = "abstract_sr_dev_test_v1"

