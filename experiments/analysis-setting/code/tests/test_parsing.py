from __future__ import annotations

from analysis_setting_experiment.parsing import parse_prediction


def test_parse_prediction_accepts_empty_strings_and_arrays() -> None:
    payload = """
    [
      {
        "outcome_concept": "",
        "data_type": "",
        "candidate_effect_measure": "",
        "comparisons": [],
        "arm_pairs": [],
        "subgroup_candidates": [],
        "timepoints": [],
        "reported_outcome_measures": []
      }
    ]
    """
    parsed = parse_prediction(payload)
    assert parsed["parse_status"] == "success"


def test_parse_prediction_rejects_missing_field() -> None:
    payload = """
    [
      {
        "outcome_concept": "x",
        "data_type": "",
        "candidate_effect_measure": "",
        "comparisons": [],
        "arm_pairs": [],
        "subgroup_candidates": [],
        "timepoints": []
      }
    ]
    """
    parsed = parse_prediction(payload)
    assert parsed["parse_status"] == "invalid_output"


def test_parse_prediction_rejects_null() -> None:
    payload = """
    [
      {
        "outcome_concept": "x",
        "data_type": null,
        "candidate_effect_measure": "",
        "comparisons": [],
        "arm_pairs": [],
        "subgroup_candidates": [],
        "timepoints": [],
        "reported_outcome_measures": []
      }
    ]
    """
    parsed = parse_prediction(payload)
    assert parsed["parse_status"] == "invalid_output"

