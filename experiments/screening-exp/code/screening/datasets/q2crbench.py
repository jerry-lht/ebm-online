"""Q2CRBench-3 loader for normalized screening examples."""

from __future__ import annotations

import ast
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from screening.datasets.inventory import Q2CRBENCH_EXPECTED_SCREENED_DATASETS
from screening.io_utils import write_json, write_model_jsonl
from screening.schemas import GoldDecision, Pico, ScreeningCriteria, ScreeningExample, TextSection

Q2CRBENCH_DIR = "Q2CRBench-3"
DEFAULT_SOURCE_DATASET = "2024 KDIGO CKD"
SOURCE_SPLIT = "train"
BENCHMARK = "q2crbench"
SETTINGS = ("abstract_only", "evidence_profile")


@dataclass(frozen=True)
class Q2CRBenchArtifacts:
    """Paths written by the Q2CRBench preparation step."""

    abstract_only_examples: str | None = None
    evidence_profile_examples: str | None = None
    manifest_csv: str | None = None
    data_quality_json: str | None = None
    dataset_summary_csv: str | None = None
    data_quality_md: str | None = None


@dataclass(frozen=True)
class PreparedQ2CRBench:
    """In-memory Q2CRBench conversion result."""

    source_dataset: str
    abstract_only_examples: list[ScreeningExample]
    evidence_profile_examples: list[ScreeningExample]
    manifest_rows: list[dict[str, Any]]
    summary_rows: list[dict[str, Any]]
    data_quality: dict[str, Any]


@dataclass
class QualityTracker:
    """Small accumulator for loader quality findings."""

    blockers: list[str] = field(default_factory=list)
    missing_title_abstract: list[dict[str, Any]] = field(default_factory=list)
    missing_label: list[dict[str, Any]] = field(default_factory=list)
    invalid_label: list[dict[str, Any]] = field(default_factory=list)
    missing_clinical_question: list[dict[str, Any]] = field(default_factory=list)
    json_parse_errors: list[dict[str, Any]] = field(default_factory=list)
    missing_evidence_profile: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["counts"] = {
            key: len(value)
            for key, value in data.items()
            if isinstance(value, list)
        }
        return data


def prepare_q2crbench(
    data_root: str | Path,
    *,
    source_dataset: str = DEFAULT_SOURCE_DATASET,
    settings: tuple[str, ...] = SETTINGS,
) -> PreparedQ2CRBench:
    """Read local Q2CRBench parquet files and build normalized examples."""

    unknown_settings = sorted(set(settings) - set(SETTINGS))
    if unknown_settings:
        raise ValueError(f"unsupported Q2CRBench setting(s): {', '.join(unknown_settings)}")

    root = Path(data_root)
    q2_root = root / Q2CRBENCH_DIR if root.name != Q2CRBENCH_DIR else root
    frames = _read_q2crbench_parquets(q2_root)
    required = {
        "Clinical_Questions",
        "Screened_Records",
        "Evidence_Profiles-Paper",
        "Evidence_Profiles-Outcome",
        "Search_Strategies",
    }
    missing = sorted(required - set(frames))
    if missing:
        raise FileNotFoundError(f"missing Q2CRBench parquet config(s): {', '.join(missing)}")

    quality = QualityTracker()
    screened_df = frames["Screened_Records"].copy()
    screened_dataset_names = set(_unique_strings(screened_df.get("Dataset", pd.Series(dtype=str))))
    for expected in Q2CRBENCH_EXPECTED_SCREENED_DATASETS:
        if expected not in screened_dataset_names:
            quality.blockers.append(f"Q2CRBench screened records are missing for {expected}.")

    source_records = screened_df[
        screened_df["Dataset"].map(_normalize_text) == source_dataset
    ].copy()
    if source_records.empty:
        quality.blockers.append(f"Q2CRBench screened records are missing for {source_dataset}.")

    clinical_by_key = _clinical_questions_by_key(frames["Clinical_Questions"], source_dataset, quality)
    search_by_id = _search_strategies_by_id(frames["Search_Strategies"], source_dataset)
    evidence_by_paper, evidence_by_pico = _evidence_sections(
        frames["Evidence_Profiles-Paper"],
        frames["Evidence_Profiles-Outcome"],
        source_dataset,
    )

    source_slug = _slug(source_dataset)
    abstract_examples: list[ScreeningExample] = []
    evidence_examples: list[ScreeningExample] = []
    manifest_rows: list[dict[str, Any]] = []
    label_counter: Counter[str] = Counter()
    abstract_label_counter: Counter[str] = Counter()
    evidence_label_counter: Counter[str] = Counter()
    review_ids: set[str] = set()

    for source_row_number, (_, row) in enumerate(source_records.iterrows(), start=1):
        paper_index = _normalize_text(row.get("Paper_Index"))
        pico_idx = _normalize_text(row.get("PICO_IDX"))
        review_id = f"{source_dataset}::{pico_idx}"
        example_id = f"q2crbench::{source_slug}::{pico_idx}::{paper_index}"
        title = _normalize_text_or_none(row.get("Title"))
        abstract = _normalize_text_or_none(row.get("Abstract"))
        label = _normalize_label(row.get("Full-text_Assessment"))
        raw_label = _none_if_blank(row.get("Full-text_Assessment"))
        clinical = clinical_by_key.get(pico_idx)
        search_strategy_id = _normalize_text(row.get("Search_Strategy_ID"))
        search_strategy = search_by_id.get(search_strategy_id)

        has_abstract_text = bool(title or abstract)
        has_clinical = clinical is not None
        if label is None:
            issue = _issue_row(row, source_row_number, "missing_label" if raw_label is None else "invalid_label")
            if raw_label is None:
                quality.missing_label.append(issue)
            else:
                issue["raw_label"] = raw_label
                quality.invalid_label.append(issue)
            manifest_rows.append(
                _manifest_row(
                    row=row,
                    example_id=example_id,
                    review_id=review_id,
                    normalized_label="",
                    has_abstract_text=has_abstract_text,
                    has_clinical=has_clinical,
                    has_evidence=False,
                    blocker_status="blocked",
                    blocker_reasons=[issue["reason"]],
                )
            )
            continue

        label_counter[label.value] += 1
        review_ids.add(review_id)
        if not has_abstract_text:
            quality.missing_title_abstract.append(
                _issue_row(row, source_row_number, "title and abstract are both blank")
            )
        if not has_clinical:
            quality.missing_clinical_question.append(
                _issue_row(row, source_row_number, f"missing Clinical_Questions row for PICO_IDX {pico_idx!r}")
            )

        pico = _pico_from_clinical(clinical, quality, row_context=_row_context(row, source_row_number))
        criteria = _criteria_from_sources(
            clinical=clinical,
            search_strategy=search_strategy,
            row=row,
        )
        metadata = _metadata_from_sources(
            row=row,
            source_dataset=source_dataset,
            pico_idx=pico_idx,
            paper_index=paper_index,
            search_strategy_id=search_strategy_id,
        )
        base_kwargs = {
            "example_id": example_id,
            "benchmark": BENCHMARK,
            "split": SOURCE_SPLIT,
            "review_id": review_id,
            "study_id": paper_index,
            "question": _question_from_clinical(clinical),
            "pico": pico,
            "criteria": criteria,
            "title": title,
            "abstract": abstract,
            "gold_decision": label,
            "gold_reason": _normalize_text_or_none(row.get("Reason_for_Exclusion_at_Full-text")),
            "metadata": metadata,
        }

        evidence_sections = _match_evidence_sections(row, evidence_by_paper, evidence_by_pico)
        if not evidence_sections:
            quality.missing_evidence_profile.append(
                _issue_row(row, source_row_number, "no evidence profile matched by PMID/Paper_Index or PICO_IDX")
            )

        manifest_reasons: list[str] = []
        if not has_abstract_text:
            manifest_reasons.append("title and abstract are both blank")
        if not has_clinical:
            manifest_reasons.append(f"missing Clinical_Questions row for PICO_IDX {pico_idx!r}")
        if not evidence_sections:
            manifest_reasons.append("no evidence profile matched by PMID/Paper_Index or PICO_IDX")
        manifest_rows.append(
            _manifest_row(
                row=row,
                example_id=example_id,
                review_id=review_id,
                normalized_label=label.value,
                has_abstract_text=has_abstract_text,
                has_clinical=has_clinical,
                has_evidence=bool(evidence_sections),
                blocker_status="ready" if not manifest_reasons else "partial",
                blocker_reasons=manifest_reasons,
            )
        )

        if "abstract_only" in settings and has_abstract_text and has_clinical:
            abstract_examples.append(
                ScreeningExample(
                    **base_kwargs,
                    input_setting="abstract_only",
                )
            )
            abstract_label_counter[label.value] += 1

        if "evidence_profile" in settings and has_clinical and evidence_sections:
            evidence_examples.append(
                ScreeningExample(
                    **base_kwargs,
                    evidence_profile=evidence_sections,
                    input_setting="evidence_profile",
                )
            )
            evidence_label_counter[label.value] += 1

    summary_rows = _summary_rows(
        source_dataset=source_dataset,
        source_records_count=len(source_records),
        review_count=len(review_ids),
        label_counter=label_counter,
        abstract_examples=abstract_examples,
        abstract_label_counter=abstract_label_counter,
        evidence_examples=evidence_examples,
        evidence_label_counter=evidence_label_counter,
        quality=quality,
    )
    data_quality = quality.to_dict()
    data_quality["source_dataset"] = source_dataset
    data_quality["source_split"] = SOURCE_SPLIT
    data_quality["source_record_count"] = len(source_records)
    data_quality["settings"] = list(settings)

    return PreparedQ2CRBench(
        source_dataset=source_dataset,
        abstract_only_examples=abstract_examples,
        evidence_profile_examples=evidence_examples,
        manifest_rows=manifest_rows,
        summary_rows=summary_rows,
        data_quality=data_quality,
    )


def write_q2crbench_artifacts(
    prepared: PreparedQ2CRBench,
    output_dir: str | Path,
    *,
    force: bool = False,
) -> Q2CRBenchArtifacts:
    """Write Q2CRBench examples, manifest, summary, and quality reports."""

    root = Path(output_dir)
    data_dir = root / "data" / "q2crbench"
    tables_dir = root / "tables"
    reports_dir = root / "reports"
    data_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    source_slug = _slug(prepared.source_dataset)
    abstract_path = data_dir / f"{source_slug}.abstract_only.examples.jsonl"
    evidence_path = data_dir / f"{source_slug}.evidence_profile.examples.jsonl"
    manifest_path = data_dir / "manifest.csv"
    quality_json_path = data_dir / "data_quality.json"
    summary_path = tables_dir / "q2crbench_dataset_summary.csv"
    quality_md_path = reports_dir / "q2crbench_data_quality.md"

    targets = [
        abstract_path,
        evidence_path,
        manifest_path,
        quality_json_path,
        summary_path,
        quality_md_path,
    ]
    if not force:
        existing = [str(path) for path in targets if path.exists()]
        if existing:
            raise FileExistsError(
                "Q2CRBench artifacts already exist; pass --force to overwrite: "
                + ", ".join(existing)
            )

    write_model_jsonl(abstract_path, prepared.abstract_only_examples)
    write_model_jsonl(evidence_path, prepared.evidence_profile_examples)
    _write_csv(manifest_path, prepared.manifest_rows)
    write_json(quality_json_path, prepared.data_quality)
    _write_csv(summary_path, prepared.summary_rows)
    quality_md_path.write_text(_format_quality_report(prepared), encoding="utf-8")

    return Q2CRBenchArtifacts(
        abstract_only_examples=str(abstract_path),
        evidence_profile_examples=str(evidence_path),
        manifest_csv=str(manifest_path),
        data_quality_json=str(quality_json_path),
        dataset_summary_csv=str(summary_path),
        data_quality_md=str(quality_md_path),
    )


def _read_q2crbench_parquets(root: Path) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for config_dir in (
        "Clinical_Questions",
        "Screened_Records",
        "Evidence_Profiles-Paper",
        "Evidence_Profiles-Outcome",
        "Search_Strategies",
    ):
        files = sorted((root / config_dir).glob("*.parquet"))
        if files:
            frames[config_dir] = pd.read_parquet(files[0])
    return frames


def _clinical_questions_by_key(
    clinical_df: pd.DataFrame,
    source_dataset: str,
    quality: QualityTracker,
) -> dict[str, dict[str, Any]]:
    clinical: dict[str, dict[str, Any]] = {}
    subset = clinical_df[clinical_df["Dataset"].map(_normalize_text) == source_dataset]
    for _, row in subset.iterrows():
        pico_idx = _normalize_text(row.get("Index"))
        clinical[pico_idx] = row.to_dict()
        _parse_json_like(row.get("O"), quality, _row_context(row, None, source="Clinical_Questions.O"))
    return clinical


def _search_strategies_by_id(search_df: pd.DataFrame, source_dataset: str) -> dict[str, dict[str, Any]]:
    subset = search_df[search_df["Dataset"].map(_normalize_text) == source_dataset]
    return {_normalize_text(row.get("Search_Strategy_ID")): row.to_dict() for _, row in subset.iterrows()}


def _evidence_sections(
    paper_df: pd.DataFrame,
    outcome_df: pd.DataFrame,
    source_dataset: str,
) -> tuple[dict[str, list[TextSection]], dict[str, list[TextSection]]]:
    by_paper: dict[str, list[TextSection]] = defaultdict(list)
    by_pico: dict[str, list[TextSection]] = defaultdict(list)

    paper_subset = paper_df[paper_df["Database"].map(_normalize_text) == source_dataset]
    for _, row in paper_subset.iterrows():
        section = _paper_evidence_section(row)
        pico_idx = _normalize_text(row.get("PICO_IDX"))
        paper_uid = _normalize_text(row.get("paper_uid"))
        pmid = _normalize_text(row.get("pmid"))
        by_pico[pico_idx].append(section)
        if paper_uid:
            by_paper[paper_uid].append(section)
        if pmid:
            by_paper[pmid].append(section)

    outcome_subset = outcome_df[outcome_df["Database"].map(_normalize_text) == source_dataset]
    for _, row in outcome_subset.iterrows():
        section = _outcome_evidence_section(row)
        pico_idx = _normalize_text(row.get("PICO_IDX"))
        by_pico[pico_idx].append(section)
        for paper_uid in _parse_list_like(row.get("related_paper_list")):
            by_paper[_normalize_text(paper_uid)].append(section)

    return dict(by_paper), dict(by_pico)


def _paper_evidence_section(row: pd.Series) -> TextSection:
    fields = [
        ("study_design", row.get("study_design")),
        ("characteristics", row.get("characteristics")),
        ("reference", row.get("reference")),
    ]
    return TextSection(
        title=_normalize_text_or_none(row.get("title")) or "Paper evidence profile",
        text=_format_named_fields(fields),
        source="q2crbench:evidence_profile_paper",
        section_id=_normalize_text_or_none(row.get("paper_uid")),
        metadata={
            "paper_uid": _normalize_text_or_none(row.get("paper_uid")),
            "pmid": _normalize_text_or_none(row.get("pmid")),
            "pico_idx": _normalize_text_or_none(row.get("PICO_IDX")),
            "database": _normalize_text_or_none(row.get("Database")),
        },
    )


def _outcome_evidence_section(row: pd.Series) -> TextSection:
    fields = [
        ("clinical_question", row.get("clinical_question")),
        ("population", row.get("population")),
        ("intervention", row.get("intervention")),
        ("comparator", row.get("comparator")),
        ("outcome", row.get("outcome")),
        ("importance", row.get("importance")),
        ("assessment_results", row.get("assessment_results")),
    ]
    title = _normalize_text_or_none(row.get("outcome")) or "Outcome evidence profile"
    return TextSection(
        title=title,
        text=_format_named_fields(fields),
        source="q2crbench:evidence_profile_outcome",
        section_id=_normalize_text_or_none(row.get("outcome_uid")),
        metadata={
            "outcome_uid": _normalize_text_or_none(row.get("outcome_uid")),
            "pico_idx": _normalize_text_or_none(row.get("PICO_IDX")),
            "database": _normalize_text_or_none(row.get("Database")),
            "related_paper_list": _parse_list_like(row.get("related_paper_list")),
        },
    )


def _match_evidence_sections(
    row: pd.Series,
    evidence_by_paper: dict[str, list[TextSection]],
    evidence_by_pico: dict[str, list[TextSection]],
) -> list[TextSection]:
    paper_index = _normalize_text(row.get("Paper_Index"))
    pico_idx = _normalize_text(row.get("PICO_IDX"))
    sections = list(evidence_by_paper.get(paper_index, []))
    sections.extend(evidence_by_pico.get(pico_idx, []))
    return _dedupe_sections(sections)


def _dedupe_sections(sections: list[TextSection]) -> list[TextSection]:
    seen: set[tuple[str | None, str | None, str]] = set()
    deduped: list[TextSection] = []
    for section in sections:
        key = (section.source, section.section_id, section.text)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(section)
    return deduped


def _pico_from_clinical(
    clinical: dict[str, Any] | None,
    quality: QualityTracker,
    *,
    row_context: dict[str, Any],
) -> Pico:
    if clinical is None:
        return Pico()
    outcome = _normalize_text_or_none(clinical.get("O"))
    metadata: dict[str, Any] = {}
    parsed_outcome = _parse_json_like(clinical.get("O"), quality, {**row_context, "source": "Clinical_Questions.O"})
    if parsed_outcome is not None:
        metadata["raw_outcome"] = outcome
        outcome = _json_compact(parsed_outcome)
    return Pico(
        population=_normalize_text_or_none(clinical.get("P")),
        intervention=_normalize_text_or_none(clinical.get("I")),
        comparator=_parse_comparator(clinical.get("C")),
        outcome=outcome,
        study_design=_normalize_text_or_none(clinical.get("S")),
        metadata=metadata,
    )


def _criteria_from_sources(
    *,
    clinical: dict[str, Any] | None,
    search_strategy: dict[str, Any] | None,
    row: pd.Series,
) -> ScreeningCriteria:
    return ScreeningCriteria(
        raw={
            "clinical_question": _clean_raw_dict(clinical or {}),
            "search_strategy": _clean_raw_dict(search_strategy or {}),
            "reason_for_exclusion_at_full_text": _none_if_blank(
                row.get("Reason_for_Exclusion_at_Full-text")
            ),
        }
    )


def _metadata_from_sources(
    *,
    row: pd.Series,
    source_dataset: str,
    pico_idx: str,
    paper_index: str,
    search_strategy_id: str,
) -> dict[str, Any]:
    return {
        "source_dataset": source_dataset,
        "source_split": SOURCE_SPLIT,
        "source_review": f"{source_dataset}::{pico_idx}",
        "pico_idx": pico_idx,
        "paper_index": paper_index,
        "doi": _none_if_blank(row.get("Digital Object Identifier")),
        "published": _none_if_blank(row.get("Published")),
        "search_strategy_id": search_strategy_id or None,
        "record_screening": _none_if_blank(row.get("Record_Screening")),
        "reason_for_exclusion_at_full_text": _none_if_blank(
            row.get("Reason_for_Exclusion_at_Full-text")
        ),
    }


def _summary_rows(
    *,
    source_dataset: str,
    source_records_count: int,
    review_count: int,
    label_counter: Counter[str],
    abstract_examples: list[ScreeningExample],
    abstract_label_counter: Counter[str],
    evidence_examples: list[ScreeningExample],
    evidence_label_counter: Counter[str],
    quality: QualityTracker,
) -> list[dict[str, Any]]:
    base = {
        "benchmark": BENCHMARK,
        "source_dataset": source_dataset,
        "source_split": SOURCE_SPLIT,
        "review_count": review_count,
        "source_record_count": source_records_count,
        "source_include_count": label_counter["include"],
        "source_exclude_count": label_counter["exclude"],
        "missing_title_abstract_count": len(quality.missing_title_abstract),
        "missing_clinical_question_count": len(quality.missing_clinical_question),
        "missing_evidence_profile_count": len(quality.missing_evidence_profile),
        "dataset_blocker_count": len(quality.blockers),
    }
    return [
        {
            **base,
            "setting": "abstract_only",
            "example_count": len(abstract_examples),
            "include_count": abstract_label_counter["include"],
            "exclude_count": abstract_label_counter["exclude"],
            "setting_note": "Main Q2CRBench abstract/title screening examples.",
        },
        {
            **base,
            "setting": "evidence_profile",
            "example_count": len(evidence_examples),
            "include_count": evidence_label_counter["include"],
            "exclude_count": evidence_label_counter["exclude"],
            "setting_note": "Auxiliary evidence-profile setting; not full text.",
        },
    ]


def _manifest_row(
    *,
    row: pd.Series,
    example_id: str,
    review_id: str,
    normalized_label: str,
    has_abstract_text: bool,
    has_clinical: bool,
    has_evidence: bool,
    blocker_status: str,
    blocker_reasons: list[str],
) -> dict[str, Any]:
    return {
        "benchmark": BENCHMARK,
        "source_dataset": _normalize_text(row.get("Dataset")),
        "source_split": SOURCE_SPLIT,
        "example_id": example_id,
        "review_id": review_id,
        "pico_idx": _normalize_text(row.get("PICO_IDX")),
        "study_id": _normalize_text(row.get("Paper_Index")),
        "paper_index": _normalize_text(row.get("Paper_Index")),
        "normalized_label": normalized_label,
        "has_title": bool(_normalize_text(row.get("Title"))),
        "has_abstract": bool(_normalize_text(row.get("Abstract"))),
        "has_abstract_text": has_abstract_text,
        "has_clinical_question": has_clinical,
        "has_evidence_profile": has_evidence,
        "has_full_text": False,
        "blocker_status": blocker_status,
        "blocker_reasons": "; ".join(blocker_reasons),
    }


def _format_quality_report(prepared: PreparedQ2CRBench) -> str:
    quality = prepared.data_quality
    counts = quality.get("counts", {})
    lines = [
        "# Q2CRBench Data Quality",
        "",
        f"Source dataset: `{prepared.source_dataset}`",
        "",
        "## Generated Artifacts",
        "",
        f"- abstract_only examples: {len(prepared.abstract_only_examples)}",
        f"- evidence_profile examples: {len(prepared.evidence_profile_examples)}",
        f"- manifest rows: {len(prepared.manifest_rows)}",
        "",
        "## Notes",
        "",
        "- `evidence_profile` examples use Q2CRBench paper/outcome evidence profiles and are not full text.",
        "- Missing screened records for EAN/ACR remain dataset-level blockers and are not included in main examples.",
        "",
        "## Quality Counts",
        "",
    ]
    for key in sorted(counts):
        lines.append(f"- {key}: {counts[key]}")
    if quality.get("blockers"):
        lines.extend(["", "## Dataset Blockers", ""])
        for blocker in quality["blockers"]:
            lines.append(f"- {blocker}")
    lines.append("")
    return "\n".join(lines)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def _question_from_clinical(clinical: dict[str, Any] | None) -> str | None:
    if not clinical:
        return None
    return _normalize_text_or_none(clinical.get("Question"))


def _normalize_label(value: Any) -> GoldDecision | None:
    text = _normalize_text(value).lower()
    if text == "included":
        return GoldDecision.include
    if text == "excluded":
        return GoldDecision.exclude
    return None


def _parse_comparator(value: Any) -> str | list[str] | None:
    text = _normalize_text(value)
    if not text:
        return None
    parsed = _parse_list_like(value)
    if parsed:
        return parsed
    return text


def _parse_json_like(
    value: Any,
    quality: QualityTracker,
    context: dict[str, Any],
) -> Any | None:
    text = _normalize_text(value)
    if not (text.startswith("{") or text.startswith("[")):
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as json_exc:
        try:
            return ast.literal_eval(text)
        except (ValueError, SyntaxError):
            quality.json_parse_errors.append(
                {**context, "value": text, "error": f"invalid JSON/literal: {json_exc.msg}"}
            )
            return None


def _parse_list_like(value: Any) -> list[str]:
    if hasattr(value, "tolist") and not isinstance(value, str):
        value = value.tolist()
    if isinstance(value, (list, tuple, set)):
        return [_normalize_text(item) for item in value if _normalize_text(item)]
    text = _normalize_text(value)
    if not text:
        return []
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, (list, tuple, set)):
                return [_normalize_text(item) for item in parsed if _normalize_text(item)]
        except (SyntaxError, ValueError):
            inner = text.strip("[]")
            return re.findall(r"[A-Za-z0-9_-]+", inner)
    return []


def _format_named_fields(fields: list[tuple[str, Any]]) -> str:
    lines: list[str] = []
    for name, value in fields:
        text = _normalize_text(value)
        if text:
            lines.append(f"{name}: {text}")
    return "\n".join(lines) or "No evidence profile text available."


def _clean_raw_dict(data: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in data.items():
        if _none_if_blank(value) is not None:
            clean[str(key)] = _json_safe(value)
    return clean


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return str(value)


def _json_compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _issue_row(row: pd.Series, source_row_number: int | None, reason: str) -> dict[str, Any]:
    return {
        **_row_context(row, source_row_number),
        "reason": reason,
    }


def _row_context(row: pd.Series | dict[str, Any], source_row_number: int | None, source: str | None = None) -> dict[str, Any]:
    getter = row.get
    context = {
        "source_row_number": source_row_number,
        "source": source or "Screened_Records",
        "source_dataset": _normalize_text(getter("Dataset")) or _normalize_text(getter("Database")),
        "pico_idx": _normalize_text(getter("PICO_IDX")) or _normalize_text(getter("Index")),
        "paper_index": _normalize_text(getter("Paper_Index")),
    }
    return {key: value for key, value in context.items() if value not in ("", None)}


def _unique_strings(series: pd.Series) -> set[str]:
    return {value for value in (_normalize_text(item) for item in series) if value}


def _none_if_blank(value: Any) -> str | None:
    text = _normalize_text(value)
    return text or None


def _normalize_text_or_none(value: Any) -> str | None:
    return _none_if_blank(value)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value)
    return re.sub(r"\s+", " ", text).strip()


def _slug(value: str) -> str:
    text = re.sub(r"^\s*\d{4}\s+", "", value)
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
