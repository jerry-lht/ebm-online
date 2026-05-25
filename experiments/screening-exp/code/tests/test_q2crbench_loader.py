from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from screening.cli.prepare_q2crbench import main as prepare_q2crbench_main
from screening.datasets.q2crbench import prepare_q2crbench, write_q2crbench_artifacts
from screening.io_utils import read_json, read_model_jsonl
from screening.schemas import ScreeningExample


def _write_toy_q2crbench(root: Path) -> None:
    q2_root = root / "Q2CRBench-3"
    for dirname in (
        "Clinical_Questions",
        "Screened_Records",
        "Evidence_Profiles-Paper",
        "Evidence_Profiles-Outcome",
        "Search_Strategies",
    ):
        (q2_root / dirname).mkdir(parents=True, exist_ok=True)

    pd.DataFrame(
        [
            {
                "Aspect": "KDIGO aspect",
                "Index": "a1",
                "Question": "Should CKD patients receive biopsy?",
                "P": "Adults with CKD",
                "I": "Kidney biopsy",
                "C": "['Clinical diagnosis']",
                "O": '{"Clinical diagnosis": "Mortality"}',
                "S": "Observational studies",
                "Dataset": "2024 KDIGO CKD",
            },
            {
                "Aspect": "Other",
                "Index": "1",
                "Question": "EAN question",
                "P": "Patients",
                "I": "Treatment",
                "C": "Comparator",
                "O": "Outcome",
                "S": "RCT",
                "Dataset": "2020 EAN Dementia",
            },
        ]
    ).to_parquet(q2_root / "Clinical_Questions" / "train.parquet")
    pd.DataFrame(
        [
            {
                "Paper_Index": "111",
                "Title": "Included record",
                "Published": "2024",
                "Abstract": "Included abstract.",
                "Digital Object Identifier": "10.1/example",
                "Full-text_Assessment": "Included",
                "Record_Screening": "Maybe",
                "Reason_for_Exclusion_at_Full-text": "",
                "Dataset": "2024 KDIGO CKD",
                "Search_Strategy_ID": "1",
                "PICO_IDX": "a1",
            },
            {
                "Paper_Index": "222",
                "Title": "",
                "Published": "2023",
                "Abstract": "",
                "Digital Object Identifier": "",
                "Full-text_Assessment": "Excluded",
                "Record_Screening": "",
                "Reason_for_Exclusion_at_Full-text": "Wrong population",
                "Dataset": "2024 KDIGO CKD",
                "Search_Strategy_ID": "1",
                "PICO_IDX": "a1",
            },
            {
                "Paper_Index": "333",
                "Title": "Excluded record",
                "Published": "2022",
                "Abstract": "Excluded abstract.",
                "Digital Object Identifier": "",
                "Full-text_Assessment": "Excluded",
                "Record_Screening": "",
                "Reason_for_Exclusion_at_Full-text": "Wrong intervention",
                "Dataset": "2024 KDIGO CKD",
                "Search_Strategy_ID": "1",
                "PICO_IDX": "a1",
            },
        ]
    ).to_parquet(q2_root / "Screened_Records" / "train.parquet")
    pd.DataFrame(
        [
            {
                "title": "Included profile",
                "paper_uid": "p-111",
                "reference": "Ref 111",
                "study_design": "Cohort",
                "characteristics": '{"n": "10"}',
                "PICO_IDX": "a1",
                "Database": "2024 KDIGO CKD",
                "pmid": "111",
            }
        ]
    ).to_parquet(q2_root / "Evidence_Profiles-Paper" / "train.parquet")
    pd.DataFrame(
        [
            {
                "outcome_uid": "out-1",
                "clinical_question": "Should CKD patients receive biopsy?",
                "population": "Adults with CKD",
                "intervention": "Kidney biopsy",
                "comparator": "Clinical diagnosis",
                "outcome": "Mortality",
                "importance": "CRITICAL",
                "related_paper_list": "['p-111']",
                "assessment_results": '{"GRADE": {"Certainty": "LOW"}}',
                "PICO_IDX": "a1",
                "Database": "2024 KDIGO CKD",
            }
        ]
    ).to_parquet(q2_root / "Evidence_Profiles-Outcome" / "train.parquet")
    pd.DataFrame(
        [
            {
                "Search_Strategy_ID": "1",
                "Search_Strategy": "kidney biopsy strategy",
                "Platform": "Ovid",
                "Search_for_PICO_IDX": "['a1']",
                "Dataset": "2024 KDIGO CKD",
            }
        ]
    ).to_parquet(q2_root / "Search_Strategies" / "train.parquet")


def test_q2crbench_loader_builds_kdigo_abstract_examples_and_blockers(tmp_path: Path) -> None:
    _write_toy_q2crbench(tmp_path)

    prepared = prepare_q2crbench(tmp_path)

    assert len(prepared.abstract_only_examples) == 2
    assert [item.gold_decision for item in prepared.abstract_only_examples] == ["include", "exclude"]
    assert prepared.abstract_only_examples[0].example_id == "q2crbench::kdigo_ckd::a1::111"
    assert prepared.abstract_only_examples[0].review_id == "2024 KDIGO CKD::a1"
    assert prepared.abstract_only_examples[0].study_id == "111"
    assert any("2020 EAN Dementia" in item for item in prepared.data_quality["blockers"])
    assert any("2021 ACR RA" in item for item in prepared.data_quality["blockers"])
    assert prepared.data_quality["counts"]["missing_title_abstract"] == 1


def test_q2crbench_loader_maps_clinical_question_and_metadata(tmp_path: Path) -> None:
    _write_toy_q2crbench(tmp_path)

    example = prepare_q2crbench(tmp_path).abstract_only_examples[0]

    assert example.question == "Should CKD patients receive biopsy?"
    assert example.pico.population == "Adults with CKD"
    assert example.pico.intervention == "Kidney biopsy"
    assert example.pico.comparator == ["Clinical diagnosis"]
    assert example.pico.outcome == '{"Clinical diagnosis": "Mortality"}'
    assert example.pico.metadata["raw_outcome"] == '{"Clinical diagnosis": "Mortality"}'
    assert example.criteria.raw["search_strategy"]["Search_Strategy"] == "kidney biopsy strategy"
    assert example.metadata["source_dataset"] == "2024 KDIGO CKD"
    assert example.metadata["source_split"] == "train"
    assert example.metadata["source_review"] == "2024 KDIGO CKD::a1"
    assert example.metadata["pico_idx"] == "a1"
    assert example.metadata["paper_index"] == "111"
    assert example.metadata["doi"] == "10.1/example"
    assert example.metadata["published"] == "2024"
    assert example.metadata["search_strategy_id"] == "1"
    assert example.metadata["record_screening"] == "Maybe"
    assert "reason_for_exclusion_at_full_text" in example.metadata


def test_q2crbench_evidence_profile_sections_are_not_full_text(tmp_path: Path) -> None:
    _write_toy_q2crbench(tmp_path)

    prepared = prepare_q2crbench(tmp_path)

    assert len(prepared.evidence_profile_examples) == 3
    example = prepared.evidence_profile_examples[0]
    assert example.input_setting == "evidence_profile"
    assert example.full_text_sections == []
    assert example.evidence_profile
    assert {section.source for section in example.evidence_profile} == {
        "q2crbench:evidence_profile_paper",
        "q2crbench:evidence_profile_outcome",
    }


def test_q2crbench_artifact_writer_counts_match_examples(tmp_path: Path) -> None:
    _write_toy_q2crbench(tmp_path)
    prepared = prepare_q2crbench(tmp_path)

    artifacts = write_q2crbench_artifacts(prepared, tmp_path / "out")

    abstract = read_model_jsonl(artifacts.abstract_only_examples, ScreeningExample)
    evidence = read_model_jsonl(artifacts.evidence_profile_examples, ScreeningExample)
    quality = read_json(artifacts.data_quality_json)
    with Path(artifacts.manifest_csv).open(encoding="utf-8", newline="") as handle:
        manifest_rows = list(csv.DictReader(handle))
    with Path(artifacts.dataset_summary_csv).open(encoding="utf-8", newline="") as handle:
        summary_rows = list(csv.DictReader(handle))

    assert len(abstract) == 2
    assert len(evidence) == 3
    assert len(manifest_rows) == 3
    summary_by_setting = {row["setting"]: row for row in summary_rows}
    assert int(summary_by_setting["abstract_only"]["example_count"]) == len(abstract)
    assert int(summary_by_setting["evidence_profile"]["example_count"]) == len(evidence)
    assert quality["counts"]["missing_title_abstract"] == 1


def test_prepare_q2crbench_cli_writes_all_artifacts(tmp_path: Path) -> None:
    _write_toy_q2crbench(tmp_path)
    output_dir = tmp_path / "results"

    result = prepare_q2crbench_main(
        ["--data-root", str(tmp_path), "--output-dir", str(output_dir), "--force"]
    )

    assert result == 0
    assert (output_dir / "data" / "q2crbench" / "kdigo_ckd.abstract_only.examples.jsonl").exists()
    assert (output_dir / "data" / "q2crbench" / "kdigo_ckd.evidence_profile.examples.jsonl").exists()
    assert (output_dir / "data" / "q2crbench" / "manifest.csv").exists()
    assert (output_dir / "data" / "q2crbench" / "data_quality.json").exists()
    assert (output_dir / "tables" / "q2crbench_dataset_summary.csv").exists()
    assert (output_dir / "reports" / "q2crbench_data_quality.md").exists()
