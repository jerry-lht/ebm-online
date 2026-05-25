from __future__ import annotations

from analysis_setting_experiment.conditional_evaluator import (
    aggregate_conditional_results,
    build_conditional_error_analysis,
    evaluate_conditional_instance,
)



def _base_instance(task_name: str, gold_target: dict, task_metadata: dict | None = None) -> dict:
    return {
        "instance_id": f"i-{task_name}",
        "review_id": "r1",
        "task_name": task_name,
        "evidence_mode": "abstract-only",
        "gold_target": gold_target,
        "task_metadata": task_metadata or {},
        "metadata": {},
    }



def test_comparisons_are_order_insensitive_and_deduplicated() -> None:
    instance = _base_instance(
        "comparisons",
        {"comparisons": ["drug vs placebo", "exercise vs usual care"]},
    )
    prediction = {
        "parse_status": "success",
        "schema_valid": True,
        "parsed_prediction_json": {
            "comparisons": ["Exercise vs usual care", "drug vs placebo", "drug vs placebo"]
        },
    }
    result = evaluate_conditional_instance(instance, prediction)
    assert result["exact_set_match"] is True
    assert result["f1"] == 1.0



def test_arm_pairs_score_unordered_match_and_direction_accuracy() -> None:
    instance = _base_instance(
        "arm_pairs",
        {"arm_pairs": [{"experimental_arm": "drug", "control_arm": "placebo"}]},
    )
    prediction = {
        "parse_status": "success",
        "schema_valid": True,
        "parsed_prediction_json": {
            "arm_pairs": [{"experimental_arm": "placebo", "control_arm": "drug"}]
        },
    }
    result = evaluate_conditional_instance(instance, prediction)
    assert result["unordered_f1"] == 1.0
    assert result["direction_accuracy"] == 0.0



def test_structured_task_detects_comparison_arm_misattachment() -> None:
    instance = _base_instance(
        "comparisons_and_arm_pairs",
        {
            "items": [
                {
                    "comparison": "drug vs placebo",
                    "arm_pairs": [{"experimental_arm": "drug", "control_arm": "placebo"}],
                },
                {
                    "comparison": "exercise vs usual care",
                    "arm_pairs": [{"experimental_arm": "exercise", "control_arm": "usual care"}],
                },
            ]
        },
    )
    prediction = {
        "parse_status": "success",
        "schema_valid": True,
        "parsed_prediction_json": {
            "items": [
                {
                    "comparison": "drug vs placebo",
                    "arm_pairs": [{"experimental_arm": "exercise", "control_arm": "usual care"}],
                },
                {
                    "comparison": "exercise vs usual care",
                    "arm_pairs": [{"experimental_arm": "drug", "control_arm": "placebo"}],
                },
            ]
        },
    }
    result = evaluate_conditional_instance(instance, prediction)
    assert result["comparison_f1"] == 1.0
    assert result["arm_pair_f1"] == 0.0
    assert result["comparison_arm_coherence_rate"] == 0.0
    assert result["exact_structured_match"] is False



def test_effect_measure_aliases_are_canonicalized() -> None:
    instance = _base_instance(
        "candidate_effect_measure",
        {"candidate_effect_measure": "Std. Mean Difference"},
        {"condition_data_type": "Continuous"},
    )
    prediction = {
        "parse_status": "success",
        "schema_valid": True,
        "parsed_prediction_json": {"candidate_effect_measure": "standardized mean difference"},
    }
    result = evaluate_conditional_instance(instance, prediction)
    assert result["correct"] is True



def test_rate_ratio_alias_is_canonicalized() -> None:
    instance = _base_instance(
        "candidate_effect_measure",
        {"candidate_effect_measure": "Rate Ratio"},
        {"condition_data_type": "Contrast level"},
    )
    prediction = {
        "parse_status": "success",
        "schema_valid": True,
        "parsed_prediction_json": {"candidate_effect_measure": "incidence rate ratio"},
    }
    result = evaluate_conditional_instance(instance, prediction)
    assert result["correct"] is True



def test_effect_measure_aggregate_reports_family_boundary_errors() -> None:
    instance_a = _base_instance(
        "candidate_effect_measure",
        {"candidate_effect_measure": "Odds Ratio"},
        {"condition_data_type": "Dichotomous"},
    )
    instance_b = _base_instance(
        "candidate_effect_measure",
        {"candidate_effect_measure": "Hazard Ratio"},
        {"condition_data_type": "Contrast level"},
    )
    result_a = evaluate_conditional_instance(
        instance_a,
        {
            "parse_status": "success",
            "schema_valid": True,
            "parsed_prediction_json": {"candidate_effect_measure": "Risk Ratio"},
        },
    )
    result_b = evaluate_conditional_instance(
        instance_b,
        {
            "parse_status": "success",
            "schema_valid": True,
            "parsed_prediction_json": {"candidate_effect_measure": "Mean Difference"},
        },
    )
    aggregate = aggregate_conditional_results("candidate_effect_measure", [result_a, result_b])
    assert aggregate["targeted_boundary_errors"]["odds ratio -> risk ratio"] == 1
    assert aggregate["out_of_family_prediction_count"] == 1
    assert aggregate["family_internal_confusions"]["odds ratio -> risk ratio"] == 1


def test_comparisons_aggregate_reports_normalized_f1_and_error_signals() -> None:
    instance = _base_instance(
        "comparisons",
        {"comparisons": ["psychological interventions vs inactive control"]},
    )
    prediction = {
        "parse_status": "success",
        "schema_valid": True,
        "parsed_prediction_json": {"comparisons": ["psychological interventions vs waiting list"]},
    }
    result = evaluate_conditional_instance(instance, prediction)
    aggregate = aggregate_conditional_results("comparisons", [result])
    assert aggregate["normalized_set_f1"] == 0.0
    assert aggregate["comparison_count_accuracy"] == 1.0
    assert aggregate["missing_comparison_total"] == 1
    assert aggregate["extra_comparison_total"] == 1
    assert aggregate["broad_vs_narrow_error_count"] == 1


def test_comparisons_error_analysis_includes_grouped_and_broad_narrow_tags() -> None:
    grouped_instance = _base_instance(
        "comparisons",
        {"comparisons": ["exercise vs usual care or no treatment"]},
    )
    grouped_prediction = {
        "parse_status": "success",
        "schema_valid": True,
        "parsed_prediction_json": {"comparisons": ["exercise vs usual care"]},
    }
    grouped_result = evaluate_conditional_instance(grouped_instance, grouped_prediction)

    broad_instance = _base_instance(
        "comparisons",
        {"comparisons": ["psychological interventions vs inactive control"]},
    )
    broad_prediction = {
        "parse_status": "success",
        "schema_valid": True,
        "parsed_prediction_json": {"comparisons": ["psychological interventions vs waiting list"]},
    }
    broad_result = evaluate_conditional_instance(broad_instance, broad_prediction)

    cases = build_conditional_error_analysis("comparisons", [grouped_result, broad_result], sample_size=10, seed=1)
    assert any(case["grouped_vs_atomic"] for case in cases)
    assert any(case["broad_vs_narrow"] for case in cases)


def test_comparisons_normalize_vs_and_versus_as_same() -> None:
    instance = _base_instance(
        "comparisons",
        {"comparisons": ["service system approaches vs inactive control"]},
    )
    prediction = {
        "parse_status": "success",
        "schema_valid": True,
        "parsed_prediction_json": {"comparisons": ["Service system approaches versus inactive control"]},
    }
    result = evaluate_conditional_instance(instance, prediction)
    assert result["exact_set_match"] is True
    assert result["normalized_set_f1"] == 1.0



def test_comparisons_aggregate_separates_gold_empty_from_comparison_only() -> None:
    nonempty_instance = _base_instance(
        "comparisons",
        {"comparisons": ["drug vs placebo"]},
    )
    empty_instance = {
        **_base_instance("comparisons", {"comparisons": []}),
        "instance_id": "i-comparisons-empty",
    }
    nonempty_result = evaluate_conditional_instance(
        nonempty_instance,
        {
            "parse_status": "success",
            "schema_valid": True,
            "parsed_prediction_json": {"comparisons": ["drug versus placebo"]},
        },
    )
    empty_result = evaluate_conditional_instance(
        empty_instance,
        {
            "parse_status": "success",
            "schema_valid": True,
            "parsed_prediction_json": {"comparisons": ["made up vs placebo"]},
        },
    )
    aggregate = aggregate_conditional_results("comparisons", [nonempty_result, empty_result])
    assert aggregate["primary_slice"] == "comparison_only"
    assert aggregate["all_instances"]["normalized_set_f1"] == 0.5
    assert aggregate["comparison_only"]["normalized_set_f1"] == 1.0
    assert aggregate["gold_nonempty"]["exact_set_match_rate"] == 1.0
    assert aggregate["gold_empty"]["instance_count"] == 1
    assert aggregate["gold_empty"]["hallucinated_comparison_rate"] == 1.0
    assert aggregate["gold_empty"]["pred_empty_rate"] == 0.0
    assert aggregate["gold_empty"]["mean_predicted_count"] == 1.0


def test_comparisons_alias_normalization_keeps_safe_surface_matches_only() -> None:
    instance = _base_instance(
        "comparisons",
        {"comparisons": ["service system approaches vs placebo", "exercise vs usual care"]},
    )
    prediction = {
        "parse_status": "success",
        "schema_valid": True,
        "parsed_prediction_json": {
            "comparisons": ["service system approaches compared with placebo control", "exercise versus routine care"]
        },
    }
    result = evaluate_conditional_instance(instance, prediction)
    assert result["exact_set_match"] is True
    assert result["normalized_set_f1"] == 1.0
