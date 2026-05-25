from __future__ import annotations

from analysis_setting_experiment.dataset import build_review_record, make_dev_test_split


def test_build_review_record_keeps_only_title_and_abstract() -> None:
    review = {
        "review_id": "R1",
        "sr_title": "Review",
        "sr_pico": {"population": ["adult"]},
        "included_studies": [
            {
                "study_id": "S1",
                "study_year": "2001",
                "primary_report": {"title": "Study 1"},
                "abstract": "Abstract 1",
            },
            {
                "study_id": "S2",
                "study_year": "2002",
                "primary_report": {"title": "Study 2"},
                "abstract": "",
            },
        ],
        "gold_partial_analysis_settings": [{"outcome_concept": "x"}],
        "evidence_coverage": {"coverage_level": "LOW"},
    }
    record = build_review_record(review)
    assert record["studies"] == [{"title": "Study 1", "abstract": "Abstract 1"}]
    assert "study_id" not in record["studies"][0]
    assert "study_year" not in record["studies"][0]


def test_make_dev_test_split_preserves_all_reviews() -> None:
    records = []
    for index in range(6):
        records.append(
            {
                "review_id": f"R{index}",
                "metadata": {
                    "coverage_level": "HIGH" if index < 3 else "LOW",
                    "gold_candidate_count_bucket": "1-10",
                },
            }
        )
    splits = make_dev_test_split(records, dev_ratio=0.2, seed=1)
    total = len(splits["dev"]) + len(splits["test"])
    assert total == 6
    assert splits["dev"]
    assert splits["test"]

