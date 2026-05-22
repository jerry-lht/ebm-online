from meta_extract.normalize import normalize_subgroup, normalize_timepoint_value, normalize_timepoints
from meta_extract.scoring import (
    oracle_extraction_instance_score,
    proposal_instance_score,
    routed_extraction_instance_score,
    support_instance_score,
)


def test_normalization_handles_null_subgroup_and_timepoint_variants():
    assert normalize_subgroup(None) is None
    assert normalize_subgroup("  Adults ") == "adults"
    assert normalize_timepoint_value("at 1 month") == "1 month"
    assert normalize_timepoint_value("post-intervention") == "post intervention"
    assert normalize_timepoints(["post intervention", "post-intervention"]) == ("post intervention",)


def test_support_score_tracks_uncertain_and_joint_consistency():
    gold = {
        "instance_id": "support-1",
        "split": "dev",
        "setting_context": {"data_type": "Continuous"},
        "gold_support": {"subgroup_support_status": "supported", "timepoint_support_status": "supported"},
    }
    prediction = {"subgroup_support_status": "uncertain", "timepoint_support_status": "supported"}
    score = support_instance_score(gold, prediction)
    assert score["subgroup_correct"] is False
    assert score["timepoint_correct"] is True
    assert score["joint_correct"] is False


def test_proposal_score_structured_f1_and_extra_audit():
    gold = {
        "instance_id": "proposal-1",
        "split": "dev",
        "setting_context": {"data_type": "Continuous"},
        "gold_items": [{"subgroup": "Adults", "timepoints": ["1 month"]}],
    }
    prediction = {
        "proposed_items": [
            {"subgroup": "Adults", "timepoints": ["1 month"]},
            {"subgroup": None, "timepoints": []},
            {"subgroup": "Teens", "timepoints": ["6 months"]},
        ]
    }
    score = proposal_instance_score(gold, prediction)
    assert score["structured_metrics"]["f1"] == 0.5
    assert score["error_buckets"]["unsupported_extra_count"] == 1
    assert score["error_buckets"]["conflicting_extra_count"] == 1


def test_oracle_extraction_score_complete_row_and_empty_prediction_rate_inputs():
    gold = {
        "instance_id": "oracle-1",
        "split": "dev",
        "setting_context": {"data_type": "Dichotomous"},
        "official_item": {"match_status": "unique"},
        "gold_extraction_rows": [
            {"direct_extraction_fields": [{"field": "Experimental cases", "value": "4"}, {"field": "Experimental N", "value": "40"}]}
        ],
    }
    prediction = {"predicted_rows": [], "prediction_stats": {"complete_row_count": 0, "partial_row_count": 0}}
    score = oracle_extraction_instance_score(gold, prediction)
    assert score["analysis_buckets"]["empty_prediction_rate"] == 1
    assert score["analysis_buckets"]["complete_row_count"] == 0


def test_oracle_extraction_no_match_stays_out_of_primary_scoring():
    gold = {
        "instance_id": "oracle-2",
        "split": "dev",
        "setting_context": {"data_type": "Contrast level"},
        "official_item": {"match_status": "no_match"},
        "gold_extraction_rows": [],
    }
    prediction = {"predicted_rows": [{"direct_extraction_fields": [{"field": "GIV Mean", "value": "0.5"}]}]}
    score = oracle_extraction_instance_score(gold, prediction)
    assert score["scored"] is False
    assert score["predicted_row_count"] == 1


def test_routed_extraction_score_separates_timepoint_and_extraction_errors():
    gold = {
        "instance_id": "routed-1",
        "split": "test",
        "setting_context": {"data_type": "Continuous"},
        "gold_items": [
            {
                "subgroup": "Adults",
                "timepoints": ["1 month"],
                "gold_extraction_rows": [{"direct_extraction_fields": [{"field": "Experimental mean", "value": "1.0"}, {"field": "Control mean", "value": "2.0"}]}],
            },
            {
                "subgroup": "Adults",
                "timepoints": ["6 months"],
                "gold_extraction_rows": [{"direct_extraction_fields": [{"field": "Experimental mean", "value": "3.0"}, {"field": "Control mean", "value": "4.0"}]}],
            },
        ],
    }
    prediction = {
        "predicted_items": [
            {
                "subgroup": "Adults",
                "timepoints": ["post intervention"],
                "predicted_rows": [{"direct_extraction_fields": [{"field": "Experimental mean", "value": "1.0"}, {"field": "Control mean", "value": "9.0"}]}],
            }
        ]
    }
    score = routed_extraction_instance_score(gold, prediction)
    assert score["error_buckets"]["routing_missing_count"] == 2
    assert score["error_buckets"]["routing_extra_count"] == 1
    assert score["error_buckets"]["timepoint_misalignment_count"] == 1
    assert score["proposal_metrics"]["f1"] == 0.0


def test_routed_extraction_multiset_rows_score_exact_when_rows_match():
    gold = {
        "instance_id": "routed-2",
        "split": "dev",
        "setting_context": {"data_type": "Contrast level"},
        "gold_items": [
            {
                "subgroup": None,
                "timepoints": ["post intervention"],
                "gold_extraction_rows": [
                    {"direct_extraction_fields": [{"field": "GIV Mean", "value": "0.5"}, {"field": "GIV SE", "value": "0.1"}]},
                    {"direct_extraction_fields": [{"field": "GIV Mean", "value": "0.7"}, {"field": "GIV SE", "value": "0.2"}]},
                ],
            }
        ],
    }
    prediction = {
        "predicted_items": [
            {
                "subgroup": None,
                "timepoints": ["post-intervention"],
                "predicted_rows": [
                    {"direct_extraction_fields": [{"field": "GIV Mean", "value": "0.7"}, {"field": "GIV SE", "value": "0.2"}]},
                    {"direct_extraction_fields": [{"field": "GIV Mean", "value": "0.5"}, {"field": "GIV SE", "value": "0.1"}]},
                ],
            }
        ]
    }
    score = routed_extraction_instance_score(gold, prediction)
    assert score["proposal_metrics"]["f1"] == 1.0
    assert score["row_metrics"]["f1"] == 1.0
    assert score["setting_success"] is True
