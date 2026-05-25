from __future__ import annotations

from analysis_setting_experiment.conditional_dataset import build_review_evidence, expand_review_to_instances
from analysis_setting_experiment.conditional_experiment import build_stratified_subset, conditional_target_label



def _review() -> dict[str, object]:
    return {
        "review_id": "R1",
        "sr_title": "Review",
        "sr_pico": {"outcome": ["Outcome A"]},
        "included_studies": [
            {
                "study_id": "S1",
                "study_year": "2001",
                "primary_report": {"title": "Study 1"},
                "evidence_tier": "full_text",
                "full_content": {
                    "sections": [
                        {"section": "Methods", "text": "Instrument and questionnaire text"},
                        {"section": "Results", "text": "Result text with odds ratio and hazard ratio mentions"},
                    ],
                    "tables": [{"id": "T1"}],
                },
                "abstract": "Abstract 1",
            },
            {
                "study_id": "S2",
                "study_year": "2002",
                "primary_report": {"title": "Study 2"},
                "evidence_tier": "abstract",
                "abstract": "Abstract 2",
            },
        ],
        "gold_partial_analysis_settings": [
            {
                "candidate_id": "c1",
                "outcome_concept": "Outcome A",
                "data_type": "Dichotomous",
                "candidate_effect_measure": "Risk Ratio",
                "comparisons": ["Drug versus placebo"],
                "arm_pairs": [{"experimental_arm": "Drug", "control_arm": "Placebo"}],
            },
            {
                "candidate_id": "c2",
                "outcome_concept": "Outcome A",
                "data_type": "Continuous",
                "candidate_effect_measure": "Mean Difference",
                "comparisons": ["Drug versus placebo", "Drug versus usual care"],
                "arm_pairs": [{"experimental_arm": "Drug", "control_arm": "Placebo"}],
            },
        ],
        "evidence_coverage": {"coverage_level": "HIGH"},
    }



def test_expand_review_to_instances_splits_data_type_and_effect_measure() -> None:
    instances = expand_review_to_instances(_review(), evidence_mode="full-text")
    by_task: dict[str, list[dict[str, object]]] = {}
    for item in instances:
        by_task.setdefault(str(item["task_name"]), []).append(item)
    assert len(by_task["data_type"]) == 2
    assert len(by_task["candidate_effect_measure"]) == 2
    assert len(by_task["comparisons"]) == 1
    assert len(by_task["arm_pairs"]) == 2
    assert len(by_task["comparisons_and_arm_pairs"]) == 1
    effect_instance = by_task["candidate_effect_measure"][0]
    assert effect_instance["task_metadata"]["linked_data_type_instance_id"]



def test_abstract_only_and_full_text_evidence_modes_behave_as_expected() -> None:
    abstract_evidence = build_review_evidence(_review(), evidence_mode="abstract-only")
    assert len(abstract_evidence) == 2
    assert abstract_evidence[0]["evidence_source"] == "abstract"
    full_text_evidence = build_review_evidence(_review(), evidence_mode="full-text")
    assert full_text_evidence[0]["evidence_source"] == "full_text"
    assert full_text_evidence[0]["has_tables"] is True
    assert "Methods" in full_text_evidence[0]["text"]
    assert full_text_evidence[0]["full_text_sections"][0]["section"] == "Methods"
    assert full_text_evidence[1]["evidence_source"] == "abstract"



def test_stratified_subset_preserves_rare_labels() -> None:
    instances = [
        {"instance_id": f"i-{index}", "review_id": f"r-{index}", "gold_target": {"candidate_effect_measure": label}}
        for index, label in enumerate([
            "Risk Ratio",
            "Risk Ratio",
            "Risk Ratio",
            "Odds Ratio",
            "Peto Odds Ratio",
            "Rate Ratio",
        ])
    ]
    labels = [conditional_target_label("candidate_effect_measure", row) for row in instances]
    subset = build_stratified_subset(instances, size=4, stratify_labels=labels, seed=1)
    kept = {row["gold_target"]["candidate_effect_measure"] for row in subset}
    assert "Peto Odds Ratio" in kept
    assert "Rate Ratio" in kept
