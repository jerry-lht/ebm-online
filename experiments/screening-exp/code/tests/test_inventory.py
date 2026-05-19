from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from screening.cli.inventory_data import main as inventory_main
from screening.datasets.inventory import (
    CSMED_SAMPLE_ALIAS,
    inventory_csmed_ft,
    inventory_datasets,
    inventory_q2crbench,
    write_inventory_artifacts,
)
from screening.io_utils import read_json, write_json


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
            {"Index": "1", "Dataset": "2020 EAN Dementia", "Question": "q1"},
            {"Index": "2", "Dataset": "2021 ACR RA", "Question": "q2"},
            {"Index": "a1", "Dataset": "2024 KDIGO CKD", "Question": "q3"},
        ]
    ).to_parquet(q2_root / "Clinical_Questions" / "train.parquet")
    pd.DataFrame(
        [
            {
                "Paper_Index": "pmid-1",
                "Title": "Included record",
                "Abstract": "Abstract text",
                "Full-text_Assessment": "Included",
                "Dataset": "2024 KDIGO CKD",
                "PICO_IDX": "a1",
            },
            {
                "Paper_Index": "pmid-2",
                "Title": "",
                "Abstract": "",
                "Full-text_Assessment": "Excluded",
                "Dataset": "2024 KDIGO CKD",
                "PICO_IDX": "a1",
            },
        ]
    ).to_parquet(q2_root / "Screened_Records" / "train.parquet")
    pd.DataFrame(
        [
            {"paper_uid": "p1", "Database": "2024 KDIGO CKD", "PICO_IDX": "a1"},
            {"paper_uid": "p2", "Database": "2020 EAN Dementia", "PICO_IDX": "1"},
            {"paper_uid": "p3", "Database": "2021 ACR RA", "PICO_IDX": "2"},
        ]
    ).to_parquet(q2_root / "Evidence_Profiles-Paper" / "train.parquet")
    pd.DataFrame(
        [
            {"outcome_uid": "o1", "Database": "2024 KDIGO CKD", "PICO_IDX": "a1"},
            {"outcome_uid": "o2", "Database": "2020 EAN Dementia", "PICO_IDX": "1"},
            {"outcome_uid": "o3", "Database": "2021 ACR RA", "PICO_IDX": "2"},
        ]
    ).to_parquet(q2_root / "Evidence_Profiles-Outcome" / "train.parquet")
    pd.DataFrame(
        [{"Search_Strategy_ID": "s1", "Dataset": "2024 KDIGO CKD", "Search_for_PICO_IDX": "a1"}]
    ).to_parquet(q2_root / "Search_Strategies" / "train.parquet")


def _write_toy_csmed(root: Path) -> None:
    csmed_root = root / "CSMeD-FT"
    csmed_root.mkdir(parents=True, exist_ok=True)
    columns = ["review_id", "document_id", "decision", "title", "abstract", "main_text"]
    pd.DataFrame(
        [
            ["CD1", "doc-1", "included", "Title 1", "Abstract 1", "Full text"],
            ["CD1", "doc-2", "excluded", "", "Abstract 2", ""],
        ],
        columns=columns,
    ).to_csv(csmed_root / "CSMeD-FT-train.csv", index=False)
    pd.DataFrame(
        [["CD2", "doc-3", "included", "Title 3", "", "Full text 3"]],
        columns=columns,
    ).to_csv(csmed_root / "CSMeD-FT-sample.csv", index=False)
    write_json(csmed_root / "CSMeD-FT-train_reviews_metadata.json", {"CD1": {"criteria": "toy"}})
    write_json(csmed_root / "CSMeD-FT-sample_reviews_metadata.json", {"CD2": {"criteria": "toy"}})


def test_q2crbench_inventory_reports_missing_ean_acr_screened_records(tmp_path: Path) -> None:
    _write_toy_q2crbench(tmp_path)

    inventory = inventory_q2crbench(tmp_path / "Q2CRBench-3")

    rows = {row.split_source_config: row for row in inventory.rows}
    assert rows["2024 KDIGO CKD"].document_count == 2
    assert rows["2024 KDIGO CKD"].include_count == 1
    assert rows["2024 KDIGO CKD"].exclude_count == 1
    assert rows["2024 KDIGO CKD"].missing_full_text_count == 2
    assert rows["2020 EAN Dementia"].blocker_status == "blocked"
    assert rows["2021 ACR RA"].blocker_status == "blocked"
    assert any("2020 EAN Dementia" in blocker for blocker in inventory.blockers)
    assert any("2021 ACR RA" in blocker for blocker in inventory.blockers)
    assert [row.normalized_label for row in inventory.manifest] == ["include", "exclude"]


def test_csmed_inventory_reports_sample_alias_and_blank_main_text(tmp_path: Path) -> None:
    _write_toy_csmed(tmp_path)

    inventory = inventory_csmed_ft(tmp_path / "CSMeD-FT")

    rows = {row.split_source_config: row for row in inventory.rows}
    assert CSMED_SAMPLE_ALIAS in rows
    assert rows["train"].document_count == 2
    assert rows["train"].missing_full_text_count == 1
    assert rows["train"].evidence_availability == "partial"
    assert rows[CSMED_SAMPLE_ALIAS].metadata["raw_split"] == "sample"
    assert any(row.split_source_config == CSMED_SAMPLE_ALIAS for row in inventory.manifest)
    assert any(not row.has_full_text for row in inventory.manifest)


def test_write_inventory_artifacts_creates_expected_files(tmp_path: Path) -> None:
    _write_toy_q2crbench(tmp_path)
    _write_toy_csmed(tmp_path)
    inventory = inventory_datasets(tmp_path, dataset="all")

    artifacts = write_inventory_artifacts(inventory, tmp_path / "results")

    for path in artifacts.values():
        assert Path(path).exists()
    data = read_json(artifacts["dataset_inventory_json"])
    assert data["document_manifest_count"] == 5
    with Path(artifacts["document_manifest_csv"]).open(encoding="utf-8", newline="") as handle:
        manifest_rows = list(csv.DictReader(handle))
    assert "has_full_text" in manifest_rows[0]
    assert "main_text" not in manifest_rows[0]


def test_inventory_cli_toy_run_writes_artifacts(tmp_path: Path) -> None:
    _write_toy_q2crbench(tmp_path)
    _write_toy_csmed(tmp_path)
    output_dir = tmp_path / "out"

    result = inventory_main(["--dataset", "all", "--data-root", str(tmp_path), "--output-dir", str(output_dir)])

    assert result == 0
    assert (output_dir / "data" / "dataset_inventory.json").exists()
    assert (output_dir / "tables" / "dataset_inventory.csv").exists()
    assert (output_dir / "tables" / "document_manifest.csv").exists()
    assert (output_dir / "reports" / "data_blockers.md").exists()
