from __future__ import annotations

from analysis_setting_experiment.evaluator import evaluate_review


def _candidate(**overrides: object) -> dict[str, object]:
    candidate: dict[str, object] = {
        "outcome_concept": "smoking cessation",
        "data_type": "dichotomous",
        "candidate_effect_measure": "odds ratio",
        "comparisons": ["drug versus placebo"],
        "arm_pairs": [{"experimental_arm": "drug", "control_arm": "placebo"}],
        "subgroup_candidates": [],
        "timepoints": [],
        "reported_outcome_measures": [],
    }
    candidate.update(overrides)
    return candidate


def test_empty_fields_match_when_both_empty() -> None:
    result = evaluate_review(
        "R1",
        [_candidate(subgroup_candidates=[], timepoints=[])],
        [_candidate(subgroup_candidates=[], timepoints=[])],
        {"coverage_level": "HIGH"},
        split="dev",
    )
    assert result["matched_pair_count"] == 1
    assert result["f1"] == 1.0


def test_gold_empty_prediction_non_empty_is_penalized() -> None:
    result = evaluate_review(
        "R1",
        [_candidate(subgroup_candidates=["men"])],
        [_candidate(subgroup_candidates=[])],
        {"coverage_level": "HIGH"},
        split="dev",
    )
    assert result["matched_pair_count"] == 1
    assert result["matches"][0]["field_scores"]["subgroup_candidates"] == 0.0


def test_empty_outcome_candidate_marked_invalid() -> None:
    result = evaluate_review(
        "R1",
        [_candidate(outcome_concept="")],
        [_candidate()],
        {"coverage_level": "HIGH"},
        split="dev",
    )
    assert result["invalid_candidate_count"] == 1
    assert result["pred_candidate_count"] == 0


def test_duplicate_candidates_counted() -> None:
    candidate = _candidate()
    result = evaluate_review(
        "R1",
        [candidate, candidate],
        [_candidate()],
        {"coverage_level": "HIGH"},
        split="dev",
    )
    assert result["duplicate_prediction_count"] == 1


def test_zero_candidate_review_error() -> None:
    result = evaluate_review(
        "R1",
        [],
        [_candidate()],
        {"coverage_level": "HIGH"},
        split="dev",
    )
    assert result["zero_candidate_review_error"] is True

