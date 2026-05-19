from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from screening.cli.prepare_csmed_ft import main as prepare_csmed_ft_main
from screening.datasets.csmed_ft import (
    _extract_review_clauses,
    prepare_csmed_ft,
    write_csmed_ft_artifacts,
)
from screening.io_utils import read_json, read_model_jsonl, write_json
from screening.schemas import ScreeningExample


def _write_toy_csmed_ft(root: Path) -> None:
    csmed_root = root / "CSMeD-FT"
    csmed_root.mkdir(parents=True, exist_ok=True)
    columns = [
        "review_id",
        "document_id",
        "decision",
        "reason_for_exclusion",
        "publication_date",
        "doi",
        "journal",
        "year",
        "PubMed ID",
        "PDF links",
        "title",
        "authors",
        "abstract",
        "main_text",
        "citation",
        "main_text_word_count",
        "abstract_word_count",
        "title_word_count",
    ]
    pd.DataFrame(
        [
            [
                "CD-TRAIN-1",
                "doc-1",
                "included",
                "",
                "2024-01-01",
                "10.1/train1",
                "Journal 1",
                "2024",
                "111",
                "['https://example.org/1.pdf']",
                "Train title 1",
                "Author A",
                "Train abstract 1",
                "Train full text 1",
                "Citation 1",
                "100",
                "10",
                "3",
            ],
            [
                "CD-TRAIN-1",
                "doc-2",
                "excluded",
                "Wrong population",
                "2024-01-02",
                "10.1/train2",
                "Journal 2",
                "2024",
                "222",
                "",
                "",
                "Author B",
                "Train abstract 2",
                "",
                "Citation 2",
                "",
                "20",
                "",
            ],
            [
                "CD-TRAIN-2",
                "doc-3",
                "maybe",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "Train title 3",
                "",
                "",
                "Train full text 3",
                "",
                "150",
                "",
                "4",
            ],
            [
                "CD-MISSING",
                "doc-4",
                "included",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "Train title 4",
                "",
                "Train abstract 4",
                "Train full text 4",
                "",
                "200",
                "40",
                "4",
            ],
        ],
        columns=columns,
    ).to_csv(csmed_root / "CSMeD-FT-train.csv", index=False)
    pd.DataFrame(
        [
            [
                "CD-SAMPLE-1",
                "doc-s1",
                "included",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "Sample title 1",
                "",
                "Sample abstract 1",
                "Sample full text 1",
                "",
                "120",
                "24",
                "3",
            ]
        ],
        columns=columns,
    ).to_csv(csmed_root / "CSMeD-FT-sample.csv", index=False)
    write_json(
        csmed_root / "CSMeD-FT-train_reviews_metadata.json",
        {
            "CD-TRAIN-1": {
                "title": "Review title 1",
                "abstract": "Review abstract 1",
                "review_type": "Intervention",
                "doi": "10.2/review1",
                "review_id": "CD-TRAIN-1",
                "criteria": {
                    "Types of studies": (
                        "We included randomized trials. "
                        "We excluded observational studies only."
                    ),
                    "Types of participants": (
                        "We included adults with CKD who met the following criteria. "
                        "Adults with chronic kidney disease   Age 18 years or older"
                    ),
                    "Search strategy": "Appendix 1. MEDLINE search terms and operators.",
                },
                "search_strategy": {"database": "MEDLINE"},
                "criteria_text": "Inclusion criteria: adults with CKD; randomized trials\nExclusion criteria: children",
            },
            "CD-TRAIN-2": {
                "title": "Review title 2",
                "abstract": "Review abstract 2",
                "review_type": "Diagnostic",
                "doi": "10.2/review2",
                "review_id": "CD-TRAIN-2",
                "criteria": {"setting": "Primary care"},
                "search_strategy": {"database": "EMBASE"},
                "criteria_text": (
                    "Studies meeting the following criteria were eligible. "
                    "Primary care setting   Adults with hypertension. "
                    "We did not include pediatric populations. "
                    "Search methods: MEDLINE and EMBASE."
                ),
            },
        },
    )
    write_json(
        csmed_root / "CSMeD-FT-sample_reviews_metadata.json",
        {
            "CD-SAMPLE-1": {
                "title": "Review title sample",
                "abstract": "",
                "review_type": "Qualitative",
                "doi": "10.2/review-sample",
                "review_id": "CD-SAMPLE-1",
                "criteria": {"topic": "Sample"},
                "search_strategy": {"database": "CENTRAL"},
                "criteria_text": (
                    "Studies meeting the following criteria were eligible for inclusion. "
                    "Primary care setting   Adults with hypertension. "
                    "We did not include pediatric populations. "
                    "Search methods: CENTRAL."
                ),
            }
        },
    )


def test_csmed_ft_loader_maps_aliases_and_labels(tmp_path: Path) -> None:
    _write_toy_csmed_ft(tmp_path)

    prepared = prepare_csmed_ft(tmp_path)

    assert "test-small" in prepared.examples_by_split_setting
    sample_example = prepared.examples_by_split_setting["test-small"]["abstract_only"][0]
    assert sample_example.split == "test-small"
    assert sample_example.gold_decision == "include"
    assert sample_example.example_id == "csmed_ft::test-small::CD-SAMPLE-1::doc-s1::abstract_only"


def test_csmed_ft_loader_builds_full_text_sections_and_filters_settings(tmp_path: Path) -> None:
    _write_toy_csmed_ft(tmp_path)

    prepared = prepare_csmed_ft(tmp_path)
    train = prepared.examples_by_split_setting["train"]

    assert len(train["abstract_only"]) == 3
    assert len(train["full_text_only"]) == 2
    assert len(train["abstract_plus_full_text"]) == 2
    abstract_only_ids = {example.study_id for example in train["abstract_only"]}
    full_text_only_ids = {example.study_id for example in train["full_text_only"]}
    assert "doc-2" in abstract_only_ids
    assert "doc-2" not in full_text_only_ids
    full_text_example = next(example for example in train["full_text_only"] if example.study_id == "doc-1")
    assert full_text_example.full_text_sections[0].title == "full_text"
    assert full_text_example.full_text_sections[0].source == "csmed_ft:main_text"


def test_csmed_ft_loader_merges_review_metadata_and_preserves_criteria_raw(tmp_path: Path) -> None:
    _write_toy_csmed_ft(tmp_path)

    example = prepare_csmed_ft(tmp_path).examples_by_split_setting["train"]["abstract_only"][0]

    assert example.question == "Review title 1"
    assert "randomized trials" in example.criteria.inclusion
    assert "Adults with chronic kidney disease" in example.criteria.inclusion
    assert "Age 18 years or older" in example.criteria.inclusion
    assert "observational studies only" in example.criteria.exclusion
    assert example.criteria.raw["criteria"]["Types of studies"].startswith("We included randomized")
    assert example.criteria.raw["search_strategy"]["database"] == "MEDLINE"
    assert any(
        item["section"] == "Types of studies" and item["source_mode"] == "criteria_mapping"
        for item in example.criteria.raw["parsed_review_clauses"]
    )
    assert example.metadata["review_title"] == "Review title 1"
    assert example.metadata["review_type"] == "Intervention"
    assert example.metadata["review_doi"] == "10.2/review1"
    assert example.metadata["pubmed_id"] == "111"
    assert example.metadata["main_text_word_count"] == "100"


def test_csmed_ft_loader_parses_criteria_text_prose_and_skips_non_eligibility_sections(tmp_path: Path) -> None:
    _write_toy_csmed_ft(tmp_path)

    prepared = prepare_csmed_ft(tmp_path)
    example = next(
        item
        for item in prepared.examples_by_split_setting["test-small"]["full_text_only"]
        if item.review_id == "CD-SAMPLE-1"
    )

    assert "Primary care setting" in example.criteria.inclusion
    assert "Adults with hypertension" in example.criteria.inclusion
    assert "pediatric populations" in example.criteria.exclusion
    assert all("Search methods" not in clause for clause in example.criteria.inclusion)
    assert all("Search methods" not in clause for clause in example.criteria.exclusion)


def test_extract_review_clauses_supports_prose_cues_and_filters_noise() -> None:
    parsed = _extract_review_clauses(
        None,
        (
            "Studies meeting the following criteria were eligible for inclusion. "
            "Adults with CKD   Randomized trials. "
            "We did not include case reports. "
            "Data collection and analysis followed Cochrane methods."
        ),
    )

    inclusion = [item.text for item in parsed if item.group == "inclusion"]
    exclusion = [item.text for item in parsed if item.group == "exclusion"]

    assert "Adults with CKD" in inclusion
    assert "Randomized trials" in inclusion
    assert "case reports" in exclusion
    assert all("Data collection" not in clause for clause in inclusion + exclusion)


def test_extract_review_clauses_ignores_outcome_sections_in_mapping() -> None:
    parsed = _extract_review_clauses(
        {
            "Types of participants": "Adults with asthma.",
            "Types of outcome measures": "Mortality. Quality of life.",
            "Primary outcomes": "Hospital admission.",
        },
        None,
    )

    assert [item.text for item in parsed if item.group == "inclusion"] == ["Adults with asthma"]
    assert not [item.text for item in parsed if item.group == "exclusion"]


def test_extract_review_clauses_ignores_selection_and_sampling_sections() -> None:
    parsed = _extract_review_clauses(
        {
            "Types of studies": "We included randomized trials. We excluded editorials.",
            "Selection of studies": (
                "All titles and abstracts were screened independently. "
                "Studies that were graded yes/yes progressed to full-text review."
            ),
            "Sampling of included studies": (
                "All eligible studies were initially rated on a data richness scale."
            ),
        },
        None,
    )

    inclusion = [item.text for item in parsed if item.group == "inclusion"]
    exclusion = [item.text for item in parsed if item.group == "exclusion"]

    assert inclusion == ["randomized trials"]
    assert exclusion == ["editorials"]


def test_csmed_ft_loader_records_invalid_label_and_missing_metadata_blockers(tmp_path: Path) -> None:
    _write_toy_csmed_ft(tmp_path)

    prepared = prepare_csmed_ft(tmp_path)
    quality = prepared.data_quality
    manifest_by_doc = {row["study_id"]: row for row in prepared.manifest_rows}

    assert quality["counts"]["invalid_label"] == 1
    assert quality["counts"]["missing_review_metadata"] == 1
    assert manifest_by_doc["doc-3"]["blocker_status"] == "blocked"
    assert "invalid_label" in manifest_by_doc["doc-3"]["blocker_reasons"]
    assert manifest_by_doc["doc-4"]["blocker_status"] == "blocked"
    assert "missing_review_metadata" in manifest_by_doc["doc-4"]["blocker_reasons"]


def test_csmed_ft_artifact_writer_counts_match_examples(tmp_path: Path) -> None:
    _write_toy_csmed_ft(tmp_path)
    prepared = prepare_csmed_ft(tmp_path)

    artifacts = write_csmed_ft_artifacts(prepared, tmp_path / "out")

    abstract_train = read_model_jsonl(
        artifacts.examples_by_split_setting["train.abstract_only"],
        ScreeningExample,
    )
    quality = read_json(artifacts.data_quality_json)
    with Path(artifacts.manifest_csv).open(encoding="utf-8", newline="") as handle:
        manifest_rows = list(csv.DictReader(handle))
    with Path(artifacts.dataset_summary_csv).open(encoding="utf-8", newline="") as handle:
        summary_rows = list(csv.DictReader(handle))

    assert len(abstract_train) == 3
    assert len(manifest_rows) == 5
    summary_by_key = {(row["split"], row["setting"]): row for row in summary_rows}
    assert int(summary_by_key[("train", "abstract_only")]["example_count"]) == 3
    assert int(summary_by_key[("train", "full_text_only")]["example_count"]) == 2
    assert int(summary_by_key[("train", "abstract_plus_full_text")]["example_count"]) == 2
    assert quality["counts"]["missing_full_text"] == 1
    assert Path(artifacts.data_quality_md).exists()


def test_prepare_csmed_ft_cli_writes_all_artifacts(tmp_path: Path) -> None:
    _write_toy_csmed_ft(tmp_path)
    output_dir = tmp_path / "results"

    result = prepare_csmed_ft_main(
        ["--data-root", str(tmp_path), "--output-dir", str(output_dir), "--force"]
    )

    assert result == 0
    assert (output_dir / "data" / "csmed_ft" / "train.abstract_only.examples.jsonl").exists()
    assert (output_dir / "data" / "csmed_ft" / "train.full_text_only.examples.jsonl").exists()
    assert (output_dir / "data" / "csmed_ft" / "train.abstract_plus_full_text.examples.jsonl").exists()
    assert (output_dir / "data" / "csmed_ft" / "test-small.abstract_only.examples.jsonl").exists()
    assert (output_dir / "data" / "csmed_ft" / "manifest.csv").exists()
    assert (output_dir / "data" / "csmed_ft" / "data_quality.json").exists()
    assert (output_dir / "data" / "csmed_ft" / "data_quality.md").exists()
    assert (output_dir / "tables" / "csmed_ft_dataset_summary.csv").exists()
