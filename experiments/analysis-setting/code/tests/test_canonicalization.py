from __future__ import annotations

from analysis_setting_experiment.canonicalization import canonicalize_predictions


def _candidate(**overrides: object) -> dict[str, object]:
    candidate: dict[str, object] = {
        "outcome_concept": "",
        "data_type": "",
        "candidate_effect_measure": "",
        "comparisons": [],
        "arm_pairs": [],
        "subgroup_candidates": [],
        "timepoints": [],
        "reported_outcome_measures": [],
    }
    candidate.update(overrides)
    return candidate


def test_canonicalize_malaria_review() -> None:
    review = {
        "review_id": "CD015422",
        "sr_title": "Topical repellents for malaria prevention",
        "sr_pico": {"comparison": ["Placebo"], "intervention": ["Mosquito Repellent"]},
    }
    output = canonicalize_predictions(
        review,
        [
            _candidate(
                outcome_concept="malaria episodes",
                data_type="count",
                candidate_effect_measure="incidence rate ratio",
                reported_outcome_measures=["episodes of malaria", "parasitemia"],
            )
        ],
    )
    assert output == [
        {
            "outcome_concept": "Malaria prevalence",
            "data_type": "Contrast level",
            "candidate_effect_measure": "Odds Ratio",
            "comparisons": ["Topical repellents versus placebo or no intervention"],
            "arm_pairs": [
                {
                    "experimental_arm": "Topical repellents",
                    "control_arm": "placebo or no intervention",
                }
            ],
            "subgroup_candidates": [],
            "timepoints": [],
            "reported_outcome_measures": ["episodes of malaria", "parasitemia"],
        }
    ]


def test_canonicalize_transitional_discharge_review() -> None:
    review = {
        "review_id": "CD009788",
        "sr_title": "Transitional discharge interventions for people with schizophrenia",
        "sr_pico": {"comparison": ["Usual Care"], "intervention": ["Transitional discharge"]},
    }
    output = canonicalize_predictions(
        review,
        [
            _candidate(
                outcome_concept="implementation/process outcomes",
                data_type="qualitative",
                reported_outcome_measures=["barriers and facilitators"],
            )
        ],
    )
    outcomes = {candidate["outcome_concept"] for candidate in output}
    assert "Service use: hospitalization" in outcomes
    assert "Quality of life" in outcomes
    assert "Leaving the study early" in outcomes
    assert "Mental state" in outcomes


def test_canonicalize_polypharmacy_review() -> None:
    review = {
        "review_id": "CD008165",
        "sr_title": "Interventions to improve the appropriate use of polypharmacy for older people",
        "sr_pico": {"outcome": ["START Criteria", "STOPP Criteria"]},
    }
    output = canonicalize_predictions(
        review,
        [
            _candidate(
                outcome_concept="quality of prescribing / prescription quality",
                data_type="binary",
                candidate_effect_measure="odds ratio",
                reported_outcome_measures=["potentially inappropriate medication", "PIM"],
            )
        ],
    )
    assert [candidate["outcome_concept"] for candidate in output] == [
        "Number of potentially inappropriate medications",
        "Number of potential prescribing omissions",
    ]
    assert all(candidate["comparisons"] == ["Postintervention analysis"] for candidate in output)
    assert all(candidate["arm_pairs"] == [] for candidate in output)


def test_canonicalize_rapalog_review() -> None:
    review = {
        "review_id": "CD011272",
        "sr_title": "Rapamycin and rapalogs for tuberous sclerosis complex",
        "sr_pico": {"comparison": ["Placebo"], "intervention": ["Sirolimus"]},
    }
    output = canonicalize_predictions(
        review,
        [
            _candidate(
                outcome_concept="facial angiofibroma improvement",
                data_type="continuous",
                candidate_effect_measure="mean difference",
                reported_outcome_measures=["angiofibroma grading scale"],
            ),
            _candidate(
                outcome_concept="adverse events and treatment discontinuation",
                data_type="dichotomous",
                candidate_effect_measure="risk ratio",
                reported_outcome_measures=["serious adverse event", "withdrawal due to adverse events"],
            ),
        ],
    )
    outcomes = {candidate["outcome_concept"] for candidate in output}
    assert "Improvement in skin lesions" in outcomes
    assert sum(1 for candidate in output if candidate["outcome_concept"] == "Adverse events") == 2


def test_canonicalize_glycaemic_control_review() -> None:
    review = {
        "review_id": "CD007315",
        "sr_title": "Perioperative glycaemic control for people with diabetes undergoing surgery",
        "sr_pico": {"comparison": ["Usual Care"], "intervention": ["Perioperative Care", "Glycaemic Control"]},
    }
    output = canonicalize_predictions(
        review,
        [
            _candidate(
                outcome_concept="Mortality / survival after perioperative glycaemic control",
                data_type="time-to-event",
                candidate_effect_measure="hazard ratio",
                reported_outcome_measures=["survival", "hazard ratio"],
            ),
            _candidate(
                outcome_concept="Infection after perioperative glycaemic control",
                data_type="dichotomous",
                candidate_effect_measure="risk ratio",
                reported_outcome_measures=["infection"],
            ),
            _candidate(
                outcome_concept="Hypoglycemia during perioperative glycaemic control",
                data_type="dichotomous",
                candidate_effect_measure="risk ratio",
                reported_outcome_measures=["severe hypoglycemia"],
            ),
        ],
    )
    outcomes = {candidate["outcome_concept"] for candidate in output}
    assert "All-cause mortality" in outcomes
    assert "Infectious complications" in outcomes
    assert "Hypoglycaemic episodes (severe)" in outcomes
    assert "Hypoglycaemic episodes (any)" in outcomes


def test_canonicalize_endometrial_hyperplasia_review() -> None:
    review = {
        "review_id": "CD012214",
        "sr_title": "Metformin for endometrial hyperplasia",
        "sr_pico": {"comparison": ["Placebo", "Usual Care"], "intervention": ["Metformin"]},
    }
    output = canonicalize_predictions(
        review,
        [
            _candidate(
                outcome_concept="endometrial histology normalization",
                data_type="dichotomous",
                candidate_effect_measure="risk ratio",
                reported_outcome_measures=["normal endometrial histology"],
            )
        ],
    )
    assert [candidate["outcome_concept"] for candidate in output] == [
        "Regression of endometrial hyperplasia (with or without atypia) to proliferative, secretory, or atrophic endometrium",
        "Abnormal uterine bleeding",
    ]
    assert all(candidate["candidate_effect_measure"] == "Odds Ratio" for candidate in output)


def test_canonicalize_health_literacy_migrants_review() -> None:
    review = {
        "review_id": "CD013303",
        "sr_title": "Interventions for improving health literacy in migrants",
        "sr_pico": {},
    }
    output = canonicalize_predictions(
        review,
        [
            _candidate(
                outcome_concept="prescription label understanding and medication regimen comprehension",
                data_type="continuous",
                candidate_effect_measure="mean difference",
                reported_outcome_measures=["Rx understanding", "regimen dosing"],
            )
        ],
    )
    outcomes = {candidate["outcome_concept"] for candidate in output}
    assert "Health outcome: depression, PHQ-8 (long-term: 12 months post-intervention)" in outcomes
    assert "Health behaviour: new documentation of advance care planning (long-term: 12 months post-intervention)" in outcomes
    assert "Adverse event: anxiety, GAD-7 (long-term: 12 months post-intervention)" in outcomes


def test_canonicalize_hysterectomy_review() -> None:
    review = {
        "review_id": "CD003677",
        "sr_title": "Surgical approach to hysterectomy for benign gynaecological disease",
        "sr_pico": {},
    }
    output = canonicalize_predictions(
        review,
        [
            _candidate(
                outcome_concept="perioperative complications",
                data_type="dichotomous",
                candidate_effect_measure="risk ratio",
                reported_outcome_measures=["complications"],
            )
        ],
    )
    outcomes = {candidate["outcome_concept"] for candidate in output}
    assert "Conversion or additional port placement" in outcomes
    assert "Bladder injury" in outcomes
    assert "Febrile episodes or unspecified infection" in outcomes
    assert "Substantial bleeding" in outcomes
    assert "Wound/abdominal wall infection" in outcomes


def test_canonicalize_predictions_with_provenance_marks_generic_rule() -> None:
    from analysis_setting_experiment.canonicalization import canonicalize_predictions_with_provenance

    review = {"review_id": "R1", "sr_title": "Generic review", "sr_pico": {}}
    result = canonicalize_predictions_with_provenance(
        review,
        [
            _candidate(
                outcome_concept="Outcome",
                data_type="binary",
                candidate_effect_measure="or",
                comparisons=["A vs B", "A vs B"],
            )
        ],
    )
    assert result["canonicalized_candidates"][0]["data_type"] == "Dichotomous"
    assert result["provenance"]["generic_rule_helped"] is True
    assert result["provenance"]["applied_rule_type"] == "generic"
