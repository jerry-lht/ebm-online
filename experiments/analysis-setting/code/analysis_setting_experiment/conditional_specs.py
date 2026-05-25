from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .conditional_constants import CONDITIONAL_TASKS
from .conditional_normalization import normalize_text


@dataclass(frozen=True)
class ConditionalTaskSpec:
    name: str
    prompt_label: str
    target_key: str
    output_schema: dict[str, Any]
    instructions: str


TASK_SPECS = {
    "data_type": ConditionalTaskSpec(
        name="data_type",
        prompt_label="Predict the single best data type for the given outcome concept.",
        target_key="data_type",
        output_schema={"type": "object", "properties": {"data_type": {"type": "string"}}},
        instructions=(
            "Return exactly one JSON object with key data_type. "
            "Choose exactly one benchmark-style label: Dichotomous, Continuous, or Contrast level. "
            "Use the official RevMan/Cochrane distinction between arm-level and contrast-level data. "
            "Arm-level data capture outcomes separately for each study arm, such as events/total in each arm or means in each arm. "
            "Contrast-level data capture the difference between arms as an effect size, such as mean difference, adjusted odds ratio, hazard ratio, or incidence/rate ratio. "
            "Decision rule: choose Contrast level only when the review-level outcome is represented or synthesized as a between-arm effect estimate or contrast-based quantity rather than as raw arm-wise event/mean data. "
            "Strong cues for Contrast level include hazard ratio, adjusted odds ratio, log odds ratio, incidence rate ratio, rate ratio, ratio of rates, mean difference, standardized mean difference, or wording that explicitly frames the target as a between-arm effect estimate. "
            "If the target is a simple event, status, prevalence, count, or mean outcome at the arm level, choose Dichotomous or Continuous instead, even if the abstract later reports a common meta-analytic effect measure. "
            "When uncertain, do not default to Contrast level unless there is explicit evidence that the target itself is contrast-based."
        ),
    ),
    "candidate_effect_measure": ConditionalTaskSpec(
        name="candidate_effect_measure",
        prompt_label="Predict the single best candidate effect measure for the conditioned outcome and data type.",
        target_key="candidate_effect_measure",
        output_schema={"type": "object", "properties": {"candidate_effect_measure": {"type": "string"}}},
        instructions=(
            "Return exactly one JSON object with key candidate_effect_measure. "
            "Respect the conditioned data_type and choose the single most likely review-level meta-analytic effect measure. "
            "Use Cochrane/RevMan-style effect-measure definitions and map the decision onto the benchmark label space only. "
            "Allowed benchmark labels are: Risk Ratio, Odds Ratio, Peto Odds Ratio, Risk Difference, Mean Difference, Std. Mean Difference, Mean Difference Change from Baseline, Hazard Ratio, and Rate Ratio. "
            "Base the decision on how the review-level outcome is represented in the evidence, not on which label is common by default. "
            "Decision rules that matter most: treat ordinary binary event outcomes as Risk Ratio unless the evidence explicitly switches to odds, Peto, or absolute-risk framing; treat endpoint or post-treatment continuous scores as Mean Difference unless the evidence explicitly says change from baseline is synthesized; treat different instruments for the same construct as Std. Mean Difference."
        ),
    ),
    "comparisons": ConditionalTaskSpec(
        name="comparisons",
        prompt_label="Recover the full set of review-level comparisons for the given outcome concept.",
        target_key="comparisons",
        output_schema={"type": "object", "properties": {"comparisons": {"type": "array", "items": "string"}}},
        instructions=(
            "Return exactly one JSON object with key comparisons. "
            "Recover the comparison questions that the review is actually synthesizing for this outcome, not study-level arm labels alone. "
            "Do not output subgroup labels, timepoints, effect measures, or outcome names by themselves as comparisons. "
            "Do not list every concrete study-level pair that appears in the evidence when the review groups them under a broader review-level comparison. "
            "If the review synthesizes categories such as inactive control, active comparators, or other grouped comparator families, preserve that grouped review-level label instead of expanding it into waiting list, usual care, placebo, or other specific controls. "
            "If the review evidence supports a grouped comparison, preserve that grouped comparison rather than forcing it into unsupported atomic pairs. "
            "If the evidence only supports atomic pairwise comparisons, list those atomic comparisons separately. "
            "Use the review's abstraction level whenever possible. "
            "When a candidate list is provided, only return strings copied exactly from that candidate list and do not invent new comparison labels. "
            "Use an empty array when no supported comparison can be recovered."
        ),
    ),
    "arm_pairs": ConditionalTaskSpec(
        name="arm_pairs",
        prompt_label="Recover the structured arm pairs for the given outcome concept and comparison.",
        target_key="arm_pairs",
        output_schema={
            "type": "object",
            "properties": {
                "arm_pairs": {
                    "type": "array",
                    "items": {
                        "experimental_arm": "string",
                        "control_arm": "string"
                    }
                }
            }
        },
        instructions=(
            "Return exactly one JSON object with key arm_pairs. "
            "Each array item must be an object with experimental_arm and control_arm. "
            "Preserve direction when evidence supports it."
        ),
    ),
    "comparisons_and_arm_pairs": ConditionalTaskSpec(
        name="comparisons_and_arm_pairs",
        prompt_label="Recover the structured comparison list with attached arm pairs for the given outcome concept.",
        target_key="items",
        output_schema={
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "comparison": "string",
                        "arm_pairs": [
                            {
                                "experimental_arm": "string",
                                "control_arm": "string"
                            }
                        ]
                    }
                }
            }
        },
        instructions=(
            "Return exactly one JSON object with key items. "
            "Each item must contain comparison and arm_pairs. "
            "Attach each arm pair to the correct comparison."
        ),
    ),
}


_EFFECT_MEASURE_SELECTION_OPTIONS = {
    "dichotomous": [
        "Risk Ratio",
        "Odds Ratio",
        "Peto Odds Ratio",
        "Risk Difference",
    ],
    "continuous": [
        "Mean Difference",
        "Std. Mean Difference",
        "Mean Difference Change from Baseline",
    ],
    "contrast level": [
        "Hazard Ratio",
        "Rate Ratio",
    ],
}

_EFFECT_MEASURE_SELECTION_GUIDANCE = {
    "dichotomous": [
        "Risk Ratio: default for ordinary binary risk or event outcomes when the review does not explicitly frame results in odds, Peto, or absolute-risk terms.",
        "Odds Ratio: only when the evidence explicitly uses odds, adjusted odds, logistic regression, odds-based models, or odds-ratio wording.",
        "Peto Odds Ratio: only when the evidence explicitly mentions the Peto rare-events method or a Peto odds-ratio analysis.",
        "Risk Difference: only when the review target is explicitly an absolute difference in risk or absolute risk reduction/increase.",
    ],
    "continuous": [
        "Mean Difference: choose this when studies use the same scale or directly comparable units, including endpoint or post-treatment scores when change-from-baseline synthesis is not explicit.",
        "Std. Mean Difference: choose this when studies measure the same construct but use different scales, instruments, questionnaires, or score ranges.",
        "Mean Difference Change from Baseline: choose this only when the target is explicitly a change-from-baseline contrast; do not use it for endpoint or post-treatment scores alone.",
    ],
    "contrast level": [
        "Hazard Ratio: choose this for time-to-event, survival, or hazard-based outcomes.",
        "Rate Ratio: choose this for incidence-rate, person-time, or count-rate contrasts.",
    ],
}



def get_conditional_task_spec(task_name: str) -> ConditionalTaskSpec:
    if task_name not in TASK_SPECS:
        raise ValueError(f"unknown_conditional_task:{task_name}")
    return TASK_SPECS[task_name]



def validate_task_name(task_name: str) -> str:
    if task_name not in CONDITIONAL_TASKS:
        raise ValueError(f"unknown_conditional_task:{task_name}")
    return task_name



def get_effect_measure_selection_options(data_type: str) -> list[str]:
    return list(_EFFECT_MEASURE_SELECTION_OPTIONS.get(normalize_text(data_type), []))



def get_effect_measure_selection_guidance(data_type: str) -> list[str]:
    return list(_EFFECT_MEASURE_SELECTION_GUIDANCE.get(normalize_text(data_type), []))
