from __future__ import annotations

from analysis_setting_experiment.conditional_prompting import build_conditional_prompt


def test_comparisons_prompt_includes_review_level_guidance() -> None:
    prompt = build_conditional_prompt(
        {
            "task_name": "comparisons",
            "instance_id": "i-comparisons",
            "review_id": "r1",
            "sr_title": "Example review",
            "sr_pico": {"intervention": ["Drug"], "comparison": ["Placebo"]},
            "outcome_concept": "Smoking cessation",
            "task_metadata": {},
            "study_evidence": [],
        }
    )
    assert "review is actually synthesizing" in prompt
    assert "Do not output subgroup labels, timepoints, effect measures" in prompt
    assert "preserve that grouped comparison" in prompt
    assert "preserve that grouped review-level label" in prompt
    assert "Do not list every concrete study-level pair" in prompt



def test_comparisons_review_level_prompt_branch_includes_stronger_examples_and_few_shots() -> None:
    prompt = build_conditional_prompt(
        {
            "task_name": "comparisons",
            "instance_id": "i-comparisons-branch",
            "review_id": "r1",
            "sr_title": "Example review",
            "sr_pico": {"intervention": ["Therapy"], "comparison": ["Control"]},
            "outcome_concept": "Depressive symptoms",
            "task_metadata": {},
            "study_evidence": [],
        },
        prompt_version="conditional_task_aware_v6_comparisons_review_level",
        few_shot_set="comparisons_boundary_v1",
    )
    assert "under-report rather than over-generate unsupported atomic comparisons" in prompt
    assert "Correct: psychological interventions versus inactive control." in prompt
    assert "Example 4" in prompt
    assert 'Correct output: {"comparisons": []}' in prompt


def test_comparisons_constrained_selection_prompt_includes_candidate_list() -> None:
    prompt = build_conditional_prompt(
        {
            "task_name": "comparisons",
            "instance_id": "i-comparisons-selection",
            "review_id": "r1",
            "sr_title": "Example review",
            "sr_pico": {"intervention": ["Therapy"], "comparison": ["Usual Care", "Waiting list control"]},
            "outcome_concept": "Depressive symptoms",
            "task_metadata": {"comparison_candidates": ["Therapy versus nonactive comparators", "Therapy versus Usual Care"]},
            "study_evidence": [],
        },
        decision_strategy="constrained_selection",
        prompt_version="conditional_task_aware_v7_comparisons_selection",
    )
    assert "Candidate option list" in prompt
    assert "Therapy versus nonactive comparators" in prompt
    assert "copied exactly from the candidate option list" in prompt


def test_comparisons_benchmark_aligned_prompt_branch_includes_single_label_and_family_label_guidance() -> None:
    prompt = build_conditional_prompt(
        {
            "task_name": "comparisons",
            "instance_id": "i-comparisons-benchmark",
            "review_id": "r1",
            "sr_title": "Example review",
            "sr_pico": {"intervention": ["Decision aid"], "comparison": ["Information provision"]},
            "outcome_concept": "Choice for screening",
            "task_metadata": {},
            "study_evidence": [],
        },
        prompt_version="conditional_task_aware_v8_comparisons_benchmark_aligned",
    )
    assert "can be a simple review-level label such as choice" in prompt
    assert "Do not force every comparison into an X versus Y pair" in prompt
    assert "mbis versus active comparators" in prompt
    assert "lower cad/cam nitinol vs rectangular chain retainers at 6 months" in prompt
