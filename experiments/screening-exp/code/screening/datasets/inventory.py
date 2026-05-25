"""Read-only inventory scanners for local screening datasets."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from screening.io_utils import read_json, write_json

Q2CRBENCH_DIR = "Q2CRBench-3"
CSMED_FT_DIR = "CSMeD-FT"
CSMED_SAMPLE_ALIAS = "test-small"
Q2CRBENCH_EXPECTED_SCREENED_DATASETS = (
    "2020 EAN Dementia",
    "2021 ACR RA",
    "2024 KDIGO CKD",
)


@dataclass(frozen=True)
class InventoryRow:
    """One aggregate inventory row for a dataset split or source config."""

    benchmark: str
    split_source_config: str
    review_count: int
    document_count: int
    include_count: int
    exclude_count: int
    missing_title_count: int
    missing_abstract_count: int
    missing_full_text_count: int
    label_availability: str
    evidence_availability: str
    blocker_status: str
    blocker_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ManifestRow:
    """Lightweight per-document manifest row without source text."""

    benchmark: str
    split_source_config: str
    review_id: str
    pico_group: str
    document_id: str
    normalized_label: str
    has_title: bool
    has_abstract: bool
    has_full_text: bool
    source_file: str
    blocker_status: str
    blocker_reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DatasetInventory:
    """Complete inventory output before artifact serialization."""

    rows: list[InventoryRow]
    manifest: list[ManifestRow]
    blockers: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


def inventory_datasets(data_root: str | Path, dataset: str = "all") -> DatasetInventory:
    """Inventory selected local datasets under ``data_root``."""

    root = Path(data_root)
    rows: list[InventoryRow] = []
    manifest: list[ManifestRow] = []
    blockers: list[str] = []
    metadata: dict[str, Any] = {}

    if dataset in {"all", "q2crbench"}:
        q2 = inventory_q2crbench(root / Q2CRBENCH_DIR)
        rows.extend(q2.rows)
        manifest.extend(q2.manifest)
        blockers.extend(q2.blockers)
        metadata["q2crbench"] = q2.metadata

    if dataset in {"all", "csmed_ft"}:
        csmed = inventory_csmed_ft(root / CSMED_FT_DIR)
        rows.extend(csmed.rows)
        manifest.extend(csmed.manifest)
        blockers.extend(csmed.blockers)
        metadata["csmed_ft"] = csmed.metadata

    return DatasetInventory(rows=rows, manifest=manifest, blockers=blockers, metadata=metadata)


def inventory_q2crbench(root: str | Path) -> DatasetInventory:
    """Inventory local Q2CRBench parquet files without reconstructing records."""

    dataset_root = Path(root)
    parquet_frames = _read_q2crbench_parquets(dataset_root)
    metadata: dict[str, Any] = {
        "root": str(dataset_root),
        "parquet_configs": {
            name: {"file": str(path), "rows": len(frame), "columns": list(frame.columns)}
            for name, (path, frame) in parquet_frames.items()
        },
    }

    screened = parquet_frames.get("Screened_Records")
    if screened is None:
        reason = "Q2CRBench Screened_Records parquet is missing."
        return DatasetInventory(
            rows=[
                InventoryRow(
                    benchmark="q2crbench",
                    split_source_config=name,
                    review_count=0,
                    document_count=0,
                    include_count=0,
                    exclude_count=0,
                    missing_title_count=0,
                    missing_abstract_count=0,
                    missing_full_text_count=0,
                    label_availability="unavailable",
                    evidence_availability=_q2_evidence_status(parquet_frames, name),
                    blocker_status="blocked",
                    blocker_reasons=[reason],
                )
                for name in Q2CRBENCH_EXPECTED_SCREENED_DATASETS
            ],
            manifest=[],
            blockers=[reason],
            metadata=metadata,
        )

    screened_path, screened_df = screened
    screened_datasets = _unique_strings(screened_df.get("Dataset", pd.Series(dtype=str)))
    config_datasets = _q2_config_datasets(parquet_frames)
    all_datasets = sorted(set(Q2CRBENCH_EXPECTED_SCREENED_DATASETS) | config_datasets | screened_datasets)

    rows: list[InventoryRow] = []
    manifest: list[ManifestRow] = []
    blockers: list[str] = []

    for dataset_name in all_datasets:
        subset = screened_df[screened_df["Dataset"].fillna("").astype(str) == dataset_name]
        if subset.empty:
            reason = f"Q2CRBench screened records are missing for {dataset_name}."
            rows.append(
                InventoryRow(
                    benchmark="q2crbench",
                    split_source_config=dataset_name,
                    review_count=_q2_review_count(parquet_frames, dataset_name),
                    document_count=0,
                    include_count=0,
                    exclude_count=0,
                    missing_title_count=0,
                    missing_abstract_count=0,
                    missing_full_text_count=0,
                    label_availability="unavailable",
                    evidence_availability=_q2_evidence_status(parquet_frames, dataset_name),
                    blocker_status="blocked",
                    blocker_reasons=[reason],
                    metadata={"screened_records_present": False},
                )
            )
            blockers.append(reason)
            continue

        labels = [_normalize_q2_label(value) for value in subset["Full-text_Assessment"]]
        label_reasons = [
            f"Unexpected Q2CRBench Full-text_Assessment value at row {idx}: {value!r}"
            for idx, value in zip(subset.index, subset["Full-text_Assessment"], strict=True)
            if _normalize_q2_label(value) == ""
        ]
        blockers.extend(label_reasons)
        label_available = not label_reasons
        document_count = len(subset)
        include_count = labels.count("include")
        exclude_count = labels.count("exclude")
        evidence_status = _q2_evidence_status(parquet_frames, dataset_name)

        rows.append(
            InventoryRow(
                benchmark="q2crbench",
                split_source_config=dataset_name,
                review_count=_series_nunique(subset["PICO_IDX"]),
                document_count=document_count,
                include_count=include_count,
                exclude_count=exclude_count,
                missing_title_count=_blank_count(subset["Title"]),
                missing_abstract_count=_blank_count(subset["Abstract"]),
                missing_full_text_count=document_count,
                label_availability="available" if label_available else "blocked",
                evidence_availability=evidence_status,
                blocker_status="blocked" if label_reasons else "ready",
                blocker_reasons=label_reasons,
                metadata={
                    "screened_records_present": True,
                    "source_file": str(screened_path),
                    "full_text_note": "Q2CRBench screened records do not include full text.",
                },
            )
        )

        for idx, row in subset.iterrows():
            normalized_label = _normalize_q2_label(row.get("Full-text_Assessment"))
            row_reasons = []
            if not normalized_label:
                row_reasons.append(
                    f"Unexpected Full-text_Assessment value: {row.get('Full-text_Assessment')!r}"
                )
            manifest.append(
                ManifestRow(
                    benchmark="q2crbench",
                    split_source_config=dataset_name,
                    review_id=_to_str(row.get("PICO_IDX")),
                    pico_group=_to_str(row.get("PICO_IDX")),
                    document_id=_to_str(row.get("Paper_Index") or idx),
                    normalized_label=normalized_label,
                    has_title=_has_text(row.get("Title")),
                    has_abstract=_has_text(row.get("Abstract")),
                    has_full_text=False,
                    source_file=str(screened_path),
                    blocker_status="blocked" if row_reasons else "ready",
                    blocker_reasons=row_reasons,
                )
            )

    return DatasetInventory(rows=rows, manifest=manifest, blockers=blockers, metadata=metadata)


def inventory_csmed_ft(root: str | Path) -> DatasetInventory:
    """Inventory local CSMeD-FT CSV splits and review metadata."""

    dataset_root = Path(root)
    rows: list[InventoryRow] = []
    manifest: list[ManifestRow] = []
    blockers: list[str] = []
    metadata: dict[str, Any] = {"root": str(dataset_root), "splits": {}}

    for csv_path in sorted(dataset_root.glob("CSMeD-FT-*.csv")):
        raw_split = csv_path.stem.removeprefix("CSMeD-FT-")
        split = CSMED_SAMPLE_ALIAS if raw_split == "sample" else raw_split
        metadata_path = dataset_root / f"CSMeD-FT-{raw_split}_reviews_metadata.json"
        reviews_metadata = read_json(metadata_path) if metadata_path.exists() else {}
        df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)

        labels = [_normalize_csmed_label(value) for value in df["decision"]]
        label_reasons = [
            f"Unexpected CSMeD-FT decision value in {csv_path.name} row {idx}: {value!r}"
            for idx, value in zip(df.index, df["decision"], strict=True)
            if _normalize_csmed_label(value) == ""
        ]
        if not metadata_path.exists():
            label_reasons.append(f"CSMeD-FT metadata file is missing for split {raw_split}.")

        blockers.extend(label_reasons)
        full_text_missing = _blank_count(df["main_text"])
        document_count = len(df)
        include_count = labels.count("include")
        exclude_count = labels.count("exclude")

        rows.append(
            InventoryRow(
                benchmark="csmed_ft",
                split_source_config=split,
                review_count=_series_nunique(df["review_id"]),
                document_count=document_count,
                include_count=include_count,
                exclude_count=exclude_count,
                missing_title_count=_blank_count(df["title"]),
                missing_abstract_count=_blank_count(df["abstract"]),
                missing_full_text_count=full_text_missing,
                label_availability="available" if not label_reasons else "blocked",
                evidence_availability="partial" if full_text_missing else "available",
                blocker_status="blocked" if label_reasons else "ready",
                blocker_reasons=label_reasons,
                metadata={
                    "raw_split": raw_split,
                    "local_alias": CSMED_SAMPLE_ALIAS if raw_split == "sample" else None,
                    "source_file": str(csv_path),
                    "reviews_metadata_file": str(metadata_path) if metadata_path.exists() else None,
                    "reviews_metadata_count": len(reviews_metadata)
                    if hasattr(reviews_metadata, "__len__")
                    else 0,
                    "full_text_note": "Blank main_text rows are unavailable for full-text evaluation.",
                },
            )
        )

        metadata["splits"][split] = {
            "raw_split": raw_split,
            "source_file": str(csv_path),
            "rows": document_count,
            "reviews_metadata_file": str(metadata_path) if metadata_path.exists() else None,
            "reviews_metadata_count": len(reviews_metadata) if hasattr(reviews_metadata, "__len__") else 0,
        }

        for idx, row in df.iterrows():
            normalized_label = _normalize_csmed_label(row.get("decision"))
            row_reasons = []
            if not normalized_label:
                row_reasons.append(f"Unexpected decision value: {row.get('decision')!r}")
            manifest.append(
                ManifestRow(
                    benchmark="csmed_ft",
                    split_source_config=split,
                    review_id=_to_str(row.get("review_id")),
                    pico_group=_to_str(row.get("review_id")),
                    document_id=_to_str(row.get("document_id") or idx),
                    normalized_label=normalized_label,
                    has_title=_has_text(row.get("title")),
                    has_abstract=_has_text(row.get("abstract")),
                    has_full_text=_has_text(row.get("main_text")),
                    source_file=str(csv_path),
                    blocker_status="blocked" if row_reasons else "ready",
                    blocker_reasons=row_reasons,
                )
            )

    return DatasetInventory(rows=rows, manifest=manifest, blockers=blockers, metadata=metadata)


def write_inventory_artifacts(inventory: DatasetInventory, output_dir: str | Path) -> dict[str, str]:
    """Write JSON, CSV, and Markdown inventory artifacts."""

    root = Path(output_dir)
    data_dir = root / "data"
    tables_dir = root / "tables"
    reports_dir = root / "reports"
    data_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    json_path = data_dir / "dataset_inventory.json"
    inventory_csv_path = tables_dir / "dataset_inventory.csv"
    manifest_csv_path = tables_dir / "document_manifest.csv"
    blockers_path = reports_dir / "data_blockers.md"

    write_json(
        json_path,
        {
            "inventory_rows": [asdict(row) for row in inventory.rows],
            "document_manifest_count": len(inventory.manifest),
            "blockers": inventory.blockers,
            "metadata": inventory.metadata,
        },
    )
    _write_csv(inventory_csv_path, [_serialize_csv_row(row) for row in inventory.rows])
    _write_csv(manifest_csv_path, [_serialize_csv_row(row) for row in inventory.manifest])
    blockers_path.write_text(_format_blocker_report(inventory), encoding="utf-8")

    return {
        "dataset_inventory_json": str(json_path),
        "dataset_inventory_csv": str(inventory_csv_path),
        "document_manifest_csv": str(manifest_csv_path),
        "data_blockers_md": str(blockers_path),
    }


def _read_q2crbench_parquets(root: Path) -> dict[str, tuple[Path, pd.DataFrame]]:
    frames: dict[str, tuple[Path, pd.DataFrame]] = {}
    for config_dir in (
        "Clinical_Questions",
        "Screened_Records",
        "Evidence_Profiles-Paper",
        "Evidence_Profiles-Outcome",
        "Search_Strategies",
    ):
        files = sorted((root / config_dir).glob("*.parquet"))
        if not files:
            continue
        frames[config_dir] = (files[0], pd.read_parquet(files[0]))
    return frames


def _q2_config_datasets(parquet_frames: dict[str, tuple[Path, pd.DataFrame]]) -> set[str]:
    datasets: set[str] = set()
    for _, frame in parquet_frames.values():
        if "Dataset" in frame.columns:
            datasets.update(_unique_strings(frame["Dataset"]))
        if "Database" in frame.columns:
            datasets.update(_unique_strings(frame["Database"]))
    return datasets


def _q2_review_count(parquet_frames: dict[str, tuple[Path, pd.DataFrame]], dataset_name: str) -> int:
    clinical = parquet_frames.get("Clinical_Questions")
    if clinical is None:
        return 0
    _, frame = clinical
    if "Dataset" not in frame.columns:
        return 0
    subset = frame[frame["Dataset"].fillna("").astype(str) == dataset_name]
    return len(subset)


def _q2_evidence_status(parquet_frames: dict[str, tuple[Path, pd.DataFrame]], dataset_name: str) -> str:
    counts = []
    for config_dir in ("Evidence_Profiles-Paper", "Evidence_Profiles-Outcome"):
        item = parquet_frames.get(config_dir)
        if item is None:
            counts.append(0)
            continue
        _, frame = item
        column = "Database" if "Database" in frame.columns else "Dataset"
        counts.append(int((frame[column].fillna("").astype(str) == dataset_name).sum()))
    if all(count > 0 for count in counts):
        return "available"
    if any(count > 0 for count in counts):
        return "partial"
    return "unavailable"


def _normalize_q2_label(value: Any) -> str:
    text = _to_str(value).strip().lower()
    if text == "included":
        return "include"
    if text == "excluded":
        return "exclude"
    return ""


def _normalize_csmed_label(value: Any) -> str:
    text = _to_str(value).strip().lower()
    if text == "included":
        return "include"
    if text == "excluded":
        return "exclude"
    return ""


def _unique_strings(series: pd.Series) -> set[str]:
    return {value for value in (_to_str(item).strip() for item in series) if value}


def _series_nunique(series: pd.Series) -> int:
    return len(_unique_strings(series))


def _blank_count(series: pd.Series) -> int:
    return sum(1 for value in series if not _has_text(value))


def _has_text(value: Any) -> bool:
    return bool(_to_str(value).strip())


def _to_str(value: Any) -> str:
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return str(value)


def _serialize_csv_row(item: Any) -> dict[str, Any]:
    data = asdict(item)
    for key, value in list(data.items()):
        if isinstance(value, list):
            data[key] = "; ".join(str(part) for part in value)
        if isinstance(value, bool):
            data[key] = str(value).lower()
    return data


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def _format_blocker_report(inventory: DatasetInventory) -> str:
    lines = [
        "# Data Blockers",
        "",
        "Phase 3 inventories local files only. No external APIs, document reconstruction, or example conversion were run.",
        "",
    ]
    if inventory.blockers:
        lines.append("## Blocking Issues")
        lines.append("")
        for blocker in inventory.blockers:
            lines.append(f"- {blocker}")
    else:
        lines.append("No dataset-level blockers were found.")

    lines.extend(["", "## Notes", ""])
    lines.append(
        "- Q2CRBench screened records are locally available only for 2024 KDIGO CKD; missing EAN/ACR screened records remain blockers."
    )
    lines.append(
        "- CSMeD-FT `sample` is reported as local alias `test-small`; blank `main_text` rows remain in the manifest but are unavailable for full-text evaluation."
    )
    lines.append("")
    return "\n".join(lines)
