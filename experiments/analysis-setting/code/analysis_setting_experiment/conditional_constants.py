from __future__ import annotations

CONDITIONAL_TASKS = (
    "data_type",
    "candidate_effect_measure",
    "comparisons",
    "arm_pairs",
    "comparisons_and_arm_pairs",
)

CONDITIONAL_EVIDENCE_MODES = (
    "abstract-only",
    "full-text",
)

CONDITIONAL_PROMPT_VERSION = "conditional_task_aware_v2_official_contrast"
CONDITIONAL_SPLIT_VERSION = "conditional_review_split_v1"
CONDITIONAL_DATASET_VERSION = "conditional_task_instances_v2"
MAX_FULL_TEXT_CHARS_PER_STUDY = 6000
