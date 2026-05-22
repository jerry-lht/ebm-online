from __future__ import annotations

from analysis_setting_experiment.conditional_comparison_candidates import build_comparison_candidates


def test_build_comparison_candidates_uses_pico_pairs_and_family_summary() -> None:
    instance = {
        "sr_pico": {
            "intervention": ["Therapy"],
            "comparison": ["Usual Care", "Waiting list control", "Placebo"],
        },
        "study_evidence": [],
    }
    candidates = build_comparison_candidates(instance)
    assert "Therapy versus nonactive comparators" in candidates
    assert "Therapy versus Usual Care" in candidates


def test_build_comparison_candidates_extracts_text_pairs() -> None:
    instance = {
        "sr_pico": {},
        "study_evidence": [
            {
                "primary_report_title": "Mindfulness versus usual care for distress",
                "abstract_text": "Participants received mindfulness compared with usual care.",
                "text": "",
            }
        ],
    }
    candidates = build_comparison_candidates(instance)
    assert any("mindfulness versus usual care" == item.lower() for item in candidates)


def test_build_comparison_candidates_recovers_outcome_level_review_family_label() -> None:
    instance = {
        "outcome_concept": "Service system approaches vs inactive control, Outcome 2: Psychological wellbeing",
        "sr_pico": {
            "intervention": ["Parenting Skills Training"],
            "comparison": ["Usual Care", "Waiting list control"],
        },
        "study_evidence": [],
    }
    candidates = build_comparison_candidates(instance)
    assert "service system approaches versus inactive control" in [item.lower() for item in candidates]


def test_build_comparison_candidates_adds_review_level_templates_for_special_cases() -> None:
    ventilation_instance = {
        "sr_pico": {"intervention": ["High-frequency ventilation"], "comparison": ["Non-invasive mechanical ventilation"]},
        "study_evidence": [
            {
                "primary_report_title": "NHFOV compared with NCPAP and NIPPV",
                "abstract_text": "NHFOV reduced reintubation compared with NCPAP in preterm infants and was also compared with NIPPV.",
                "text": "",
            }
        ],
    }
    ventilation_candidates = build_comparison_candidates(ventilation_instance)
    assert "nhfv versus ncpap" in [item.lower() for item in ventilation_candidates]
    assert "initial respiratory support nhfv versus other noninvasive respiratory therapy modalities" in [item.lower() for item in ventilation_candidates]

    mindfulness_instance = {
        "sr_pico": {"intervention": ["Transcendental Meditation Therapy", "Mindfulness"]},
        "study_evidence": [],
    }
    mindfulness_candidates = build_comparison_candidates(mindfulness_instance)
    lowered = [item.lower() for item in mindfulness_candidates]
    assert "tm versus active comparators" in lowered
    assert "mbis versus nonactive comparators" in lowered
