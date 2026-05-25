from __future__ import annotations

from analysis_setting_experiment.conditional_parsing import parse_conditional_prediction


def test_parse_data_type_prediction() -> None:
    parsed = parse_conditional_prediction("data_type", '{"data_type": "Dichotomous"}')
    assert parsed["parse_status"] == "success"


def test_parse_effect_measure_prediction() -> None:
    parsed = parse_conditional_prediction(
        "candidate_effect_measure",
        '{"candidate_effect_measure": "Risk Ratio"}',
    )
    assert parsed["parsed_prediction_json"]["candidate_effect_measure"] == "Risk Ratio"


def test_parse_comparisons_prediction() -> None:
    parsed = parse_conditional_prediction("comparisons", '{"comparisons": ["a", "b"]}')
    assert parsed["parsed_prediction_json"]["comparisons"] == ["a", "b"]


def test_parse_arm_pairs_prediction() -> None:
    parsed = parse_conditional_prediction(
        "arm_pairs",
        '{"arm_pairs": [{"experimental_arm": "drug", "control_arm": "placebo"}]}',
    )
    assert parsed["parse_status"] == "success"


def test_parse_structured_prediction() -> None:
    parsed = parse_conditional_prediction(
        "comparisons_and_arm_pairs",
        '{"items": [{"comparison": "drug vs placebo", "arm_pairs": [{"experimental_arm": "drug", "control_arm": "placebo"}]}]}',
    )
    assert parsed["parse_status"] == "success"


def test_parse_rejects_wrong_shape() -> None:
    parsed = parse_conditional_prediction("arm_pairs", '{"arm_pairs": ["bad"]}')
    assert parsed["parse_status"] == "invalid_output"

