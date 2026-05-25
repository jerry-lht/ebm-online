"""CSMeD-FT loader for normalized screening examples."""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from screening.datasets.inventory import CSMED_FT_DIR, CSMED_SAMPLE_ALIAS
from screening.io_utils import read_json, write_json, write_model_jsonl
from screening.schemas import GoldDecision, Pico, ScreeningCriteria, ScreeningExample, TextSection

BENCHMARK = "csmed_ft"
SETTINGS = ("abstract_only", "full_text_only", "abstract_plus_full_text")
EXPECTED_BASELINE = {
    "train": {
        "document_count": 2053,
        "review_count": 148,
        "include_count": 904,
        "exclude_count": 1149,
        "missing_full_text_count": 43,
    },
    "dev": {
        "document_count": 644,
        "review_count": 36,
        "include_count": 202,
        "exclude_count": 442,
        "missing_full_text_count": 11,
    },
    "test": {
        "document_count": 636,
        "review_count": 29,
        "include_count": 278,
        "exclude_count": 358,
        "missing_full_text_count": 16,
    },
    CSMED_SAMPLE_ALIAS: {
        "document_count": 50,
        "review_count": 16,
        "include_count": 22,
        "exclude_count": 28,
        "missing_full_text_count": 3,
    },
}

SECTION_SKIP_KEYWORDS = (
    "outcome",
    "search",
    "appendix",
    "data collection",
    "data extraction",
    "analysis",
    "risk of bias",
    "quality assessment",
    "casp",
    "grade",
    "background",
    "objective",
    "selection of studies",
    "sampling of included studies",
    "electronic searches",
    "searching other",
    "flow chart",
    "figure",
    "prisma",
    "null",
)
SECTION_BOTH_KEYWORDS = (
    "types of studies",
    "study design",
    "design",
    "studies",
)
SECTION_INCLUSION_KEYWORDS = (
    "types of participants",
    "participant",
    "population",
    "types of interventions",
    "intervention",
    "comparator",
    "comparison",
    "setting",
    "types of settings",
    "types of phenomena of interest",
    "phenomena of interest",
    "phenomena",
    "condition",
    "topic",
)
ELIGIBILITY_LIST_CUES = (
    "met the following criteria",
    "meeting the following criteria were eligible",
    "studies meeting the following criteria were eligible",
    "eligible interventions met the following criteria",
    "eligible for inclusion",
    "trial met one of the following criteria",
    "population eligible",
    "considered eligible",
    "would be indicated by",
)
INCLUSION_CUES = (
    "we included",
    "included ",
    "eligible for inclusion",
    "were eligible",
    "met the following criteria",
    "meeting the following criteria",
    "eligible interventions",
    "inclusion criterion",
)
EXCLUSION_CUES = (
    "we excluded",
    "excluded ",
    "exclude ",
    "did not include",
    "ineligible",
    "not eligible",
    "non-randomised",
    "observational methods only",
)
LOW_SIGNAL_CLAUSE_PATTERNS = (
    r"^and$",
    r"^or$",
    r"^but$",
    r"^however$",
    r"^e\.g\.$",
    r"^[\W\d_]+$",
)
NON_ELIGIBILITY_TEXT_PATTERNS = (
    r"\bsearch methods?\b",
    r"\bdata collection\b",
    r"\banalysis\b",
    r"\bgrade approach\b",
    r"\brisk of bias\b",
    r"\boutcomes?\b",
    r"\bmortality\b",
    r"\bquality of life\b",
    r"\bcosts?\b",
    r"\bpatient satisfaction\b",
    r"\bappendix\b",
)


@dataclass(frozen=True)
class ParsedClause:
    text: str
    group: str
    section: str | None
    source_mode: str


@dataclass(frozen=True)
class CSMeDFTArtifacts:
    """Paths written by the CSMeD-FT preparation step."""

    examples_by_split_setting: dict[str, str]
    manifest_csv: str
    data_quality_json: str
    data_quality_md: str
    dataset_summary_csv: str


@dataclass(frozen=True)
class PreparedCSMeDFT:
    """In-memory CSMeD-FT conversion result."""

    examples_by_split_setting: dict[str, dict[str, list[ScreeningExample]]]
    manifest_rows: list[dict[str, Any]]
    summary_rows: list[dict[str, Any]]
    data_quality: dict[str, Any]


@dataclass
class QualityTracker:
    """Accumulates loader quality findings."""

    blockers: list[str] = field(default_factory=list)
    invalid_label: list[dict[str, Any]] = field(default_factory=list)
    missing_review_metadata: list[dict[str, Any]] = field(default_factory=list)
    missing_required_ids: list[dict[str, Any]] = field(default_factory=list)
    missing_abstract_text: list[dict[str, Any]] = field(default_factory=list)
    missing_full_text: list[dict[str, Any]] = field(default_factory=list)
    baseline_mismatch: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["counts"] = {
            key: len(value)
            for key, value in data.items()
            if isinstance(value, list)
        }
        return data


def prepare_csmed_ft(
    data_root: str | Path,
    *,
    settings: tuple[str, ...] = SETTINGS,
) -> PreparedCSMeDFT:
    """Read local CSMeD-FT files and build normalized examples."""

    unknown_settings = sorted(set(settings) - set(SETTINGS))
    if unknown_settings:
        raise ValueError(f"unsupported CSMeD-FT setting(s): {', '.join(unknown_settings)}")

    root = Path(data_root)
    dataset_root = root / CSMED_FT_DIR if root.name != CSMED_FT_DIR else root
    if not dataset_root.exists():
        raise FileNotFoundError(f"CSMeD-FT directory not found: {dataset_root}")

    quality = QualityTracker()
    examples_by_split_setting: dict[str, dict[str, list[ScreeningExample]]] = {}
    manifest_rows: list[dict[str, Any]] = []
    split_observed: dict[str, dict[str, Any]] = {}

    for csv_path in sorted(dataset_root.glob("CSMeD-FT-*.csv")):
        raw_split = csv_path.stem.removeprefix("CSMeD-FT-")
        split = CSMED_SAMPLE_ALIAS if raw_split == "sample" else raw_split
        metadata_path = dataset_root / f"CSMeD-FT-{raw_split}_reviews_metadata.json"
        rows = _read_csv_rows(csv_path)
        review_metadata = _read_review_metadata(metadata_path)

        split_examples = {setting: [] for setting in settings}
        split_counter: Counter[str] = Counter()
        split_reviews: set[str] = set()
        missing_full_text_count = 0

        for row_number, row in enumerate(rows, start=2):
            normalized = _normalize_record(
                row=row,
                row_number=row_number,
                split=split,
                raw_split=raw_split,
                source_file=csv_path,
                reviews_metadata_file=metadata_path,
                review_metadata=review_metadata.get(_clean_text(row.get("review_id"))),
                quality=quality,
            )
            manifest_rows.append(normalized["manifest"])
            if normalized["label"] is None:
                continue

            split_counter[normalized["label"].value] += 1
            split_reviews.add(normalized["review_id"])
            if not normalized["has_full_text"]:
                missing_full_text_count += 1

            for setting in settings:
                if normalized["setting_eligibility"][setting]:
                    split_examples[setting].append(
                        _build_example(
                            normalized=normalized,
                            setting=setting,
                        )
                    )

        examples_by_split_setting[split] = split_examples
        split_observed[split] = {
            "raw_split": raw_split,
            "source_file": str(csv_path),
            "reviews_metadata_file": str(metadata_path),
            "document_count": len(rows),
            "review_count": len(split_reviews),
            "include_count": split_counter["include"],
            "exclude_count": split_counter["exclude"],
            "missing_full_text_count": missing_full_text_count,
        }

    _record_baseline_mismatches(split_observed, quality)
    summary_rows = _build_summary_rows(examples_by_split_setting, manifest_rows)
    data_quality = quality.to_dict()
    data_quality["benchmark"] = BENCHMARK
    data_quality["settings"] = list(settings)
    data_quality["splits"] = split_observed

    return PreparedCSMeDFT(
        examples_by_split_setting=examples_by_split_setting,
        manifest_rows=manifest_rows,
        summary_rows=summary_rows,
        data_quality=data_quality,
    )


def write_csmed_ft_artifacts(
    prepared: PreparedCSMeDFT,
    output_dir: str | Path,
    *,
    force: bool = False,
) -> CSMeDFTArtifacts:
    """Write CSMeD-FT examples, manifest, summary, and quality reports."""

    root = Path(output_dir)
    data_dir = root / "data" / BENCHMARK
    tables_dir = root / "tables"
    data_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    paths_by_key: dict[str, str] = {}
    targets: list[Path] = []
    for split, by_setting in prepared.examples_by_split_setting.items():
        for setting, examples in by_setting.items():
            path = data_dir / f"{split}.{setting}.examples.jsonl"
            paths_by_key[f"{split}.{setting}"] = str(path)
            targets.append(path)
            if examples or force:
                continue

    manifest_path = data_dir / "manifest.csv"
    quality_json_path = data_dir / "data_quality.json"
    quality_md_path = data_dir / "data_quality.md"
    summary_path = tables_dir / "csmed_ft_dataset_summary.csv"
    targets.extend([manifest_path, quality_json_path, quality_md_path, summary_path])

    if not force:
        existing = [str(path) for path in targets if path.exists()]
        if existing:
            raise FileExistsError(
                "CSMeD-FT artifacts already exist; pass --force to overwrite: "
                + ", ".join(existing)
            )

    for split, by_setting in prepared.examples_by_split_setting.items():
        for setting, examples in by_setting.items():
            write_model_jsonl(data_dir / f"{split}.{setting}.examples.jsonl", examples)
    _write_csv(manifest_path, prepared.manifest_rows)
    write_json(quality_json_path, prepared.data_quality)
    _write_csv(summary_path, prepared.summary_rows)
    quality_md_path.write_text(_format_quality_report(prepared), encoding="utf-8")

    return CSMeDFTArtifacts(
        examples_by_split_setting=paths_by_key,
        manifest_csv=str(manifest_path),
        data_quality_json=str(quality_json_path),
        data_quality_md=str(quality_md_path),
        dataset_summary_csv=str(summary_path),
    )


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    field_limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(field_limit)
            break
        except OverflowError:
            field_limit //= 10
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_review_metadata(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = read_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"CSMeD-FT review metadata must be a dict: {path}")
    return {str(key): value for key, value in data.items() if isinstance(value, dict)}


def _normalize_record(
    *,
    row: dict[str, str],
    row_number: int,
    split: str,
    raw_split: str,
    source_file: Path,
    reviews_metadata_file: Path,
    review_metadata: dict[str, Any] | None,
    quality: QualityTracker,
) -> dict[str, Any]:
    review_id = _clean_text(row.get("review_id"))
    document_id = _clean_text(row.get("document_id"))
    label = _normalize_label(row.get("decision"))
    has_abstract_text = bool(_clean_text(row.get("title")) or _clean_text(row.get("abstract")))
    has_full_text = bool(_clean_text(row.get("main_text")))

    issue_context = {
        "split": split,
        "raw_split": raw_split,
        "row_number": row_number,
        "review_id": review_id,
        "document_id": document_id,
        "source_file": str(source_file),
        "reviews_metadata_file": str(reviews_metadata_file),
    }
    reasons: list[str] = []

    if not review_id or not document_id:
        reasons.append("missing_required_ids")
        quality.missing_required_ids.append(issue_context)
    if review_metadata is None:
        reasons.append("missing_review_metadata")
        quality.missing_review_metadata.append(issue_context)
    if label is None:
        reasons.append("invalid_label")
        quality.invalid_label.append({**issue_context, "raw_label": row.get("decision", "")})
    if not has_abstract_text:
        quality.missing_abstract_text.append(issue_context)
    if not has_full_text:
        quality.missing_full_text.append(issue_context)

    criteria = _criteria_from_review_metadata(review_metadata)
    metadata = _build_metadata(
        row=row,
        split=split,
        raw_split=raw_split,
        source_file=source_file,
        reviews_metadata_file=reviews_metadata_file,
        review_metadata=review_metadata,
    )
    full_text_sections = _full_text_sections(row)
    review_title = _clean_text(review_metadata.get("title")) if review_metadata else ""
    question = review_title or None

    setting_eligibility = {
        "abstract_only": has_abstract_text,
        "full_text_only": has_full_text,
        "abstract_plus_full_text": has_abstract_text and has_full_text,
    }
    setting_blockers = {
        "abstract_only": [] if has_abstract_text else ["missing_abstract_text"],
        "full_text_only": [] if has_full_text else ["missing_full_text"],
        "abstract_plus_full_text": (
            []
            if has_abstract_text and has_full_text
            else [reason for reason, allowed in (
                ("missing_abstract_text", has_abstract_text),
                ("missing_full_text", has_full_text),
            ) if not allowed]
        ),
    }
    for setting in setting_blockers:
        setting_blockers[setting] = reasons + setting_blockers[setting]

    manifest = {
        "benchmark": BENCHMARK,
        "split": split,
        "raw_split": raw_split,
        "review_id": review_id,
        "study_id": document_id,
        "normalized_label": label.value if label else "",
        "has_title": str(bool(_clean_text(row.get("title")))).lower(),
        "has_abstract": str(bool(_clean_text(row.get("abstract")))).lower(),
        "has_abstract_text": str(has_abstract_text).lower(),
        "has_full_text": str(has_full_text).lower(),
        "source_file": str(source_file),
        "reviews_metadata_file": str(reviews_metadata_file) if reviews_metadata_file.exists() else "",
        "review_metadata_present": str(review_metadata is not None).lower(),
        "blocker_status": "blocked" if {"missing_required_ids", "missing_review_metadata", "invalid_label"} & set(reasons) else "ready",
        "blocker_reasons": "; ".join(reasons),
        "abstract_only_available": str(setting_eligibility["abstract_only"]).lower(),
        "abstract_only_reasons": "; ".join(setting_blockers["abstract_only"]),
        "full_text_only_available": str(setting_eligibility["full_text_only"]).lower(),
        "full_text_only_reasons": "; ".join(setting_blockers["full_text_only"]),
        "abstract_plus_full_text_available": str(setting_eligibility["abstract_plus_full_text"]).lower(),
        "abstract_plus_full_text_reasons": "; ".join(setting_blockers["abstract_plus_full_text"]),
    }

    return {
        "manifest": manifest,
        "label": label,
        "review_id": review_id,
        "document_id": document_id,
        "question": question,
        "criteria": criteria,
        "title": _none_if_blank(row.get("title")),
        "abstract": _none_if_blank(row.get("abstract")),
        "full_text_sections": full_text_sections,
        "gold_reason": _none_if_blank(row.get("reason_for_exclusion")),
        "metadata": metadata,
        "has_full_text": has_full_text,
        "setting_eligibility": setting_eligibility,
        "review_metadata": review_metadata or {},
        "split": split,
    }


def _build_example(*, normalized: dict[str, Any], setting: str) -> ScreeningExample:
    return ScreeningExample(
        example_id=(
            f"{BENCHMARK}::{normalized['split']}::{normalized['review_id']}::"
            f"{normalized['document_id']}::{setting}"
        ),
        benchmark=BENCHMARK,
        split=normalized["split"],
        review_id=normalized["review_id"],
        study_id=normalized["document_id"],
        question=normalized["question"],
        pico=Pico(),
        criteria=normalized["criteria"],
        title=normalized["title"],
        abstract=normalized["abstract"],
        full_text_sections=normalized["full_text_sections"] if setting != "abstract_only" else [],
        gold_decision=normalized["label"],
        gold_reason=normalized["gold_reason"],
        input_setting=setting,
        metadata=normalized["metadata"],
    )


def _criteria_from_review_metadata(review_metadata: dict[str, Any] | None) -> ScreeningCriteria:
    if not review_metadata:
        return ScreeningCriteria()

    criteria = review_metadata.get("criteria")
    criteria_text = review_metadata.get("criteria_text")
    parsed_clauses = _extract_review_clauses(criteria, criteria_text)
    inclusion = [clause.text for clause in parsed_clauses if clause.group == "inclusion"]
    exclusion = [clause.text for clause in parsed_clauses if clause.group == "exclusion"]
    raw = {
        "criteria": _clean_raw(criteria),
        "criteria_text": _clean_raw(criteria_text),
        "search_strategy": _clean_raw(review_metadata.get("search_strategy")),
        "parsed_review_clauses": [
            {
                "text": clause.text,
                "group": clause.group,
                "section": clause.section,
                "source_mode": clause.source_mode,
            }
            for clause in parsed_clauses
        ],
    }
    return ScreeningCriteria(
        inclusion=inclusion,
        exclusion=exclusion,
        raw=raw,
    )


def _extract_review_clauses(criteria: Any, criteria_text: Any) -> list[ParsedClause]:
    parsed = _parse_criteria_mapping(criteria)
    if parsed:
        if _should_supplement_from_criteria_text(parsed):
            parsed = _merge_parsed_clauses(parsed, _parse_criteria_text_prose(criteria_text))
        return parsed
    return _parse_criteria_text_prose(criteria_text)


def _parse_criteria_mapping(criteria: Any) -> list[ParsedClause]:
    if not isinstance(criteria, dict):
        return []
    parsed: list[ParsedClause] = []
    for key, value in criteria.items():
        section = _clean_text(key)
        if not section or _section_should_skip(section):
            continue
        parsed.extend(_parse_section_value(section, value, source_mode="criteria_mapping"))
    return _dedupe_parsed_clauses(parsed)


def _parse_section_value(section: str, value: Any, *, source_mode: str) -> list[ParsedClause]:
    if isinstance(value, dict):
        parsed: list[ParsedClause] = []
        for nested_key, nested_value in value.items():
            nested_section = " / ".join(part for part in (section, _clean_text(nested_key)) if part)
            parsed.extend(_parse_section_value(nested_section, nested_value, source_mode=source_mode))
        return parsed
    if isinstance(value, list):
        parsed: list[ParsedClause] = []
        for item in value:
            parsed.extend(_parse_section_value(section, item, source_mode=source_mode))
        return parsed
    if not isinstance(value, str):
        return []
    default_groups = _default_groups_for_section(section)
    if not default_groups:
        return []
    return _parse_prose_clauses(
        value,
        source_mode=source_mode,
        section=section,
        default_groups=default_groups,
    )


def _parse_criteria_text_prose(criteria_text: Any) -> list[ParsedClause]:
    if isinstance(criteria_text, dict):
        return _parse_criteria_mapping(criteria_text)
    if not isinstance(criteria_text, str) or not criteria_text.strip():
        return []
    return _parse_prose_clauses(
        criteria_text,
        source_mode="criteria_text_prose",
        section=None,
        default_groups=("inclusion", "exclusion"),
    )


def _parse_prose_clauses(
    text: str,
    *,
    source_mode: str,
    section: str | None,
    default_groups: tuple[str, ...],
) -> list[ParsedClause]:
    normalized = _normalize_criteria_text(text)
    if not normalized or _looks_like_non_eligibility_block(normalized):
        return []

    clauses: list[ParsedClause] = []
    for block in _split_prose_blocks(normalized):
        if _looks_like_non_eligibility_block(block):
            continue
        list_clauses = _expand_following_criteria_list(block)
        if list_clauses:
            for item in list_clauses:
                group = _classify_clause_group(item, default_groups)
                if group is None:
                    continue
                cleaned = _finalize_clause_text(item)
                if cleaned:
                    clauses.append(
                        ParsedClause(
                            text=cleaned,
                            group=group,
                            section=section,
                            source_mode=source_mode,
                        )
                    )
            continue
        group = _classify_clause_group(block, default_groups)
        if group is None:
            continue
        cleaned = _finalize_clause_text(block)
        if cleaned:
            clauses.append(
                ParsedClause(
                    text=cleaned,
                    group=group,
                    section=section,
                    source_mode=source_mode,
                )
            )
    return _dedupe_parsed_clauses(clauses)


def _should_supplement_from_criteria_text(parsed: list[ParsedClause]) -> bool:
    inclusion_count = sum(1 for clause in parsed if clause.group == "inclusion")
    exclusion_count = sum(1 for clause in parsed if clause.group == "exclusion")
    return inclusion_count == 0 or exclusion_count == 0 or len(parsed) < 2


def _merge_parsed_clauses(base: list[ParsedClause], extra: list[ParsedClause]) -> list[ParsedClause]:
    return _dedupe_parsed_clauses([*base, *extra])


def _section_should_skip(section: str) -> bool:
    lowered = section.lower()
    return any(token in lowered for token in SECTION_SKIP_KEYWORDS)


def _default_groups_for_section(section: str) -> tuple[str, ...]:
    lowered = section.lower()
    if "exclusion" in lowered or "exclude" in lowered:
        return ("exclusion",)
    if "inclusion" in lowered or "include" in lowered:
        return ("inclusion",)
    if any(token in lowered for token in SECTION_BOTH_KEYWORDS):
        return ("inclusion", "exclusion")
    if any(token in lowered for token in SECTION_INCLUSION_KEYWORDS):
        return ("inclusion",)
    return ()


def _normalize_criteria_text(text: str) -> str:
    cleaned = text.replace("\u00a0", " ").replace("\u2010", "-")
    cleaned = re.sub(r" {3,}", "\n", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\s*\n\s*", "\n", cleaned)
    return cleaned.strip()


def _split_prose_blocks(text: str) -> list[str]:
    seeded = re.sub(r"(?<=[.?!])\s+(?=[A-Z])", "\n", text)
    seeded = re.sub(r"\s{3,}", "\n", seeded)
    seeded = re.sub(r"(?:^|\n)\s*(?:[-*•]|\(?\d+[.)]\)?|[A-Za-z][.)])\s+", "\n", seeded)
    parts = [part.strip(" -•\t\r\n") for part in seeded.split("\n")]
    blocks: list[str] = []
    for part in parts:
        if not part:
            continue
        blocks.extend(_split_semicolon_lists(part))
    return [part for part in blocks if part]


def _split_semicolon_lists(text: str) -> list[str]:
    parts = [part.strip(" -•\t\r\n") for part in re.split(r";\s+", text)]
    return [part for part in parts if part]


def _expand_following_criteria_list(text: str) -> list[str]:
    lowered = text.lower()
    if not any(cue in lowered for cue in ELIGIBILITY_LIST_CUES):
        return []
    for separator in (".", ":"):
        if separator in text:
            prefix, suffix = text.split(separator, 1)
            if any(cue in prefix.lower() for cue in ELIGIBILITY_LIST_CUES):
                items = _split_prose_blocks(suffix)
                return [item for item in items if _finalize_clause_text(item)]
    return []


def _classify_clause_group(text: str, default_groups: tuple[str, ...]) -> str | None:
    lowered = text.lower()
    if any(cue in lowered for cue in EXCLUSION_CUES):
        return "exclusion"
    if any(cue in lowered for cue in INCLUSION_CUES):
        return "inclusion"
    if "exclusion" in default_groups and _contains_explicit_negative_constraint(lowered):
        return "exclusion"
    if "inclusion" in default_groups:
        return "inclusion"
    if "exclusion" in default_groups:
        return "exclusion"
    return None


def _contains_explicit_negative_constraint(text: str) -> bool:
    return bool(
        re.search(
            r"\b(non-|not |no |without |excluded |exclude |did not include |ineligible|observational only)\b",
            text,
        )
    )


def _finalize_clause_text(text: str) -> str:
    cleaned = text.strip(" -•\t\r\n")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return ""
    for pattern in LOW_SIGNAL_CLAUSE_PATTERNS:
        if re.fullmatch(pattern, cleaned, flags=re.IGNORECASE):
            return ""
    if len(cleaned) < 8:
        return ""
    if _looks_like_non_eligibility_block(cleaned):
        return ""
    cleaned = re.sub(
        r"^(?:we included|we excluded|we did not include|included|excluded|eligible interventions met the following criteria|studies meeting the following criteria were eligible(?: for inclusion)?|were eligible for inclusion|eligible for inclusion|met the following criteria|the trial met one of the following criteria|the comparison for this review was)\s*[:.-]?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    cleaned = re.sub(
        r"(?:who\s+)?(?:met the following criteria|meeting the following criteria were eligible|eligible for inclusion)\.?\s*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    cleaned = cleaned.strip(" .:;,-")
    return cleaned if len(cleaned) >= 8 else ""


def _looks_like_non_eligibility_block(text: str) -> bool:
    lowered = text.lower()
    if any(re.search(pattern, lowered) for pattern in NON_ELIGIBILITY_TEXT_PATTERNS):
        if not any(cue in lowered for cue in INCLUSION_CUES + EXCLUSION_CUES + ELIGIBILITY_LIST_CUES):
            return True
    return False


def _dedupe_parsed_clauses(clauses: list[ParsedClause]) -> list[ParsedClause]:
    seen: set[tuple[str, str]] = set()
    deduped: list[ParsedClause] = []
    for clause in clauses:
        normalized_text = re.sub(r"\s+", " ", clause.text).strip().lower()
        key = (clause.group, normalized_text)
        if not normalized_text or key in seen:
            continue
        seen.add(key)
        deduped.append(clause)
    return deduped


def _build_metadata(
    *,
    row: dict[str, str],
    split: str,
    raw_split: str,
    source_file: Path,
    reviews_metadata_file: Path,
    review_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    metadata = {
        "raw_split": raw_split,
        "source_file": str(source_file),
        "reviews_metadata_file": str(reviews_metadata_file) if reviews_metadata_file.exists() else None,
        "review_title": _none_if_blank(review_metadata.get("title")) if review_metadata else None,
        "review_type": _none_if_blank(review_metadata.get("review_type")) if review_metadata else None,
        "review_doi": _none_if_blank(review_metadata.get("doi")) if review_metadata else None,
        "search_strategy": _clean_raw(review_metadata.get("search_strategy")) if review_metadata else None,
        "criteria": _clean_raw(review_metadata.get("criteria")) if review_metadata else None,
        "criteria_text": _clean_raw(review_metadata.get("criteria_text")) if review_metadata else None,
        "review_abstract": _none_if_blank(review_metadata.get("abstract")) if review_metadata else None,
        "split": split,
    }
    for field_name in (
        "publication_date",
        "doi",
        "journal",
        "year",
        "PubMed ID",
        "PDF links",
        "authors",
        "citation",
        "main_text_word_count",
        "abstract_word_count",
        "title_word_count",
    ):
        metadata[_slug_metadata_key(field_name)] = _none_if_blank(row.get(field_name))
    return metadata


def _full_text_sections(row: dict[str, str]) -> list[TextSection]:
    main_text = _none_if_blank(row.get("main_text"))
    if main_text is None:
        return []
    return [
        TextSection(
            title="full_text",
            text=main_text,
            source="csmed_ft:main_text",
        )
    ]


def _normalize_label(value: Any) -> GoldDecision | None:
    text = _clean_text(value).lower()
    if text == "included":
        return GoldDecision.include
    if text == "excluded":
        return GoldDecision.exclude
    return None


def _record_baseline_mismatches(split_observed: dict[str, dict[str, Any]], quality: QualityTracker) -> None:
    for split, expected in EXPECTED_BASELINE.items():
        observed = split_observed.get(split)
        if observed is None:
            issue = {"split": split, "reason": "missing_split"}
            quality.baseline_mismatch.append(issue)
            quality.blockers.append(f"CSMeD-FT baseline split missing from local data: {split}.")
            continue
        for key, expected_value in expected.items():
            observed_value = observed.get(key)
            if observed_value != expected_value:
                issue = {
                    "split": split,
                    "field": key,
                    "expected": expected_value,
                    "observed": observed_value,
                }
                quality.baseline_mismatch.append(issue)
                quality.blockers.append(
                    f"CSMeD-FT baseline mismatch for {split} {key}: expected {expected_value}, observed {observed_value}."
                )


def _build_summary_rows(
    examples_by_split_setting: dict[str, dict[str, list[ScreeningExample]]],
    manifest_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    manifest_by_split: dict[str, list[dict[str, Any]]] = {}
    for row in manifest_rows:
        manifest_by_split.setdefault(row["split"], []).append(row)

    for split, by_setting in sorted(examples_by_split_setting.items()):
        base_rows = manifest_by_split.get(split, [])
        for setting, examples in sorted(by_setting.items()):
            rows.append(
                {
                    "split": split,
                    "setting": setting,
                    "example_count": len(examples),
                    "review_count": len({example.review_id for example in examples}),
                    "include_count": sum(1 for example in examples if example.gold_decision == "include"),
                    "exclude_count": sum(1 for example in examples if example.gold_decision == "exclude"),
                    "missing_full_text_count": sum(
                        1 for row in base_rows if row[f"{setting}_available"] == "false" and "missing_full_text" in row[f"{setting}_reasons"]
                    ),
                    "missing_abstract_text_count": sum(
                        1 for row in base_rows if row[f"{setting}_available"] == "false" and "missing_abstract_text" in row[f"{setting}_reasons"]
                    ),
                    "avg_title_words": _avg_numeric(example.metadata.get("title_word_count") for example in examples),
                    "avg_abstract_words": _avg_numeric(example.metadata.get("abstract_word_count") for example in examples),
                    "avg_full_text_words": _avg_numeric(example.metadata.get("main_text_word_count") for example in examples),
                }
            )
    return rows


def _avg_numeric(values: Any) -> float:
    numbers: list[float] = []
    for value in values:
        text = _clean_text(value)
        if not text:
            continue
        try:
            numbers.append(float(text))
        except ValueError:
            continue
    if not numbers:
        return 0.0
    return round(sum(numbers) / len(numbers), 3)


def _format_quality_report(prepared: PreparedCSMeDFT) -> str:
    quality = prepared.data_quality
    lines = [
        "# CSMeD-FT Data Quality",
        "",
        f"- Benchmark: `{quality.get('benchmark', BENCHMARK)}`",
        f"- Settings: {', '.join(quality.get('settings', []))}",
        f"- Manifest rows: {len(prepared.manifest_rows)}",
        "",
        "## Counts",
        "",
    ]
    for key, value in sorted(quality.get("counts", {}).items()):
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Blockers", ""])
    blockers = quality.get("blockers", [])
    if blockers:
        for blocker in blockers:
            lines.append(f"- {blocker}")
    else:
        lines.append("No dataset-level blockers were found.")
    lines.extend(["", "## Split Summary", ""])
    for split, data in sorted(quality.get("splits", {}).items()):
        lines.append(
            f"- `{split}`: docs={data['document_count']}, reviews={data['review_count']}, "
            f"include={data['include_count']}, exclude={data['exclude_count']}, "
            f"blank_main_text={data['missing_full_text_count']}"
        )
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


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _none_if_blank(value: Any) -> str | None:
    text = _clean_text(value)
    return text or None


def _clean_raw(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _clean_raw(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean_raw(item) for item in value]
    if isinstance(value, str):
        return value.strip()
    return value


def _slug_metadata_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
