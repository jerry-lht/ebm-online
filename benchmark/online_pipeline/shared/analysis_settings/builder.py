"""Build shared analysis-setting cleaning artifacts for GRADE-required reviews."""

from __future__ import annotations

import json
import shutil
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from benchmark.online_pipeline.meta_analysis.setting_cleaning.cache import (
    comparison_cache_cleaning_metadata,
    comparison_cache_key,
    comparison_cache_row,
    comparison_cache_metadata,
    is_valid_comparison_cache_row,
    setting_has_valid_comparison_cache,
)
from benchmark.online_pipeline.meta_analysis.setting_cleaning.llm import extract_field_with_llm
from benchmark.online_pipeline.meta_analysis.setting_cleaning.sources import (
    assemble_setting,
    build_analysis_family_sources,
    build_field_candidates,
    method_from_family,
    normalize_official_rows,
)
from benchmark.online_pipeline.shared.building import RAW_DATA_DIR, sha256_file, sha256_json
from benchmark.online_pipeline.shared.jsonl import append_jsonl, read_jsonl, write_jsonl
from benchmark.online_pipeline.shared.report_utils import write_json


ARTIFACT_NAME = "grade_required_v1"
DEFAULT_OUTPUT_ROOT = RAW_DATA_DIR / "analysis_settings" / ARTIFACT_NAME
META_RAW_ROOT = RAW_DATA_DIR / "meta_analysis"
GRADE_RAW_ROOT = RAW_DATA_DIR / "grade"
DOMAIN_NAMES = ("risk_of_bias", "inconsistency", "indirectness", "imprecision")
FIELDS = ("comparison", "outcome", "timepoint")


def build_grade_required_settings(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    meta_raw_root: Path = META_RAW_ROOT,
    grade_raw_root: Path = GRADE_RAW_ROOT,
    llm_config: str | Path | None = None,
    use_llm: bool = False,
    workers: int = 4,
    resume: bool = False,
    reviews: list[str] | None = None,
    limit: int | None = None,
    max_failures: int = 50,
) -> dict[str, Any]:
    """Build reusable setting-cleaning artifacts for GRADE gold reviews.

    Without ``use_llm``, this writes a reusable partial artifact from existing
    cleaned settings and records the missing candidate_ids as failures.
    """
    output_root.mkdir(parents=True, exist_ok=True)
    paths = _paths(output_root)
    if not resume:
        _clear_outputs(paths)

    review_ids = sorted(_grade_gold_review_ids(grade_raw_root))
    target_review_ids = set(reviews or review_ids)
    normalized = normalize_official_rows(meta_raw_root / "source" / "official_analysis_csv_snapshot")
    normalized = _filter_normalized(normalized, review_ids=set(review_ids))
    families = build_analysis_family_sources(
        overall_rows=normalized["overall"],
        data_rows=normalized["data_rows"],
        subgroup_rows=normalized["subgroup_estimates"],
    )
    cleaning_target_families = [family for family in families if str(family.get("review_id")) in target_review_ids]
    if limit is not None:
        cleaning_target_families = cleaning_target_families[: max(0, limit)]
    family_by_candidate = {row["candidate_id"]: row for row in families}
    candidates_by_field = build_field_candidates(families)
    comparison_candidate_by_id = {row["candidate_id"]: row for row in candidates_by_field["comparison"]}

    write_jsonl(paths["family_sources"], families, sort_keys=False)
    for field, rows in candidates_by_field.items():
        write_jsonl(paths["field_candidates"][field], rows, sort_keys=False)

    existing_cleaned = _load_existing_cleaned_settings(
        meta_raw_root=meta_raw_root,
        candidate_lookup=comparison_candidate_by_id,
    )
    if resume and paths["settings"].exists():
        settings_by_candidate = _load_valid_existing_settings(
            paths["settings"],
            candidate_lookup=comparison_candidate_by_id,
            allowed_candidate_ids={family["candidate_id"] for family in families},
        )
        _rewrite_settings(paths["settings"], settings_by_candidate)
    else:
        settings_by_candidate = {}
    completed = set(settings_by_candidate)

    reused = []
    for family in cleaning_target_families:
        candidate_id = family["candidate_id"]
        if candidate_id in completed:
            continue
        setting = existing_cleaned.get(candidate_id)
        if setting and _same_family_identity(setting=setting, family=family):
            reused_setting = _with_reuse_marker(setting)
            append_jsonl(paths["settings"], [reused_setting], sort_keys=False)
            settings_by_candidate[candidate_id] = reused_setting
            completed.add(candidate_id)
            reused.append(candidate_id)

    pending = [family for family in cleaning_target_families if family["candidate_id"] not in completed]
    failures: list[dict[str, Any]] = []
    if pending and use_llm:
        if llm_config is None:
            raise RuntimeError("--use-llm requires --llm-config")
        failures.extend(
            _clean_pending_with_llm(
                pending=pending,
                candidates_by_field=candidates_by_field,
                paths=paths,
                llm_config=llm_config,
                workers=workers,
                max_failures=max_failures,
                settings_by_candidate=settings_by_candidate,
            )
        )
    elif pending:
        failures.extend(
            {
                "candidate_id": family["candidate_id"],
                "review_id": family["review_id"],
                "analysis_group": family["analysis_group"],
                "analysis_number": family["analysis_number"],
                "status": "missing_cleaning_not_run",
            }
            for family in pending
        )
        append_jsonl(paths["failures"], failures, sort_keys=False)

    settings = sorted(settings_by_candidate.values(), key=lambda row: row["candidate_id"])
    _prune_resolved_failures(
        paths["failures"],
        completed_candidate_ids={
            row["candidate_id"]
            for row in settings
            if row.get("candidate_id") in comparison_candidate_by_id
            and setting_has_valid_comparison_cache(row, comparison_candidate_by_id[row["candidate_id"]])
        },
    )
    raw_material = _build_raw_material(families=families, settings=settings)
    write_jsonl(paths["raw_material"], raw_material, sort_keys=False)
    report = _report(
        output_root=output_root,
        review_ids=review_ids,
        target_review_ids=sorted(target_review_ids),
        normalized=normalized,
        families=families,
        settings=settings,
        reused_count=len(reused),
        failures=_read_failures(paths["failures"]),
        meta_raw_root=meta_raw_root,
        grade_raw_root=grade_raw_root,
        use_llm=use_llm,
        llm_config=llm_config,
    )
    write_json(paths["report"], report)
    write_json(paths["source_manifest"], report["source_manifest"])
    _write_grade_projection(output_root=output_root, grade_raw_root=grade_raw_root)
    return report


def _clean_pending_with_llm(
    *,
    pending: list[dict[str, Any]],
    candidates_by_field: dict[str, list[dict[str, Any]]],
    paths: dict[str, Any],
    llm_config: str | Path,
    workers: int,
    max_failures: int,
    settings_by_candidate: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    candidate_lookup = {
        field: {row["candidate_id"]: row for row in rows}
        for field, rows in candidates_by_field.items()
    }
    comparison_cache = _load_comparison_cache(paths["comparison_cache"], candidate_lookup=candidate_lookup["comparison"])
    comparison_cache_lock = threading.Lock()
    failures: list[dict[str, Any]] = []
    failure_count = 0
    total_count = len(pending)
    completed_count = 0
    success_count = 0

    def print_progress(*, force_newline: bool = False) -> None:
        if total_count == 0:
            return
        remaining = total_count - completed_count
        message = (
            f"[analysis-settings] {completed_count}/{total_count} done "
            f"success={success_count} failed={failure_count} remaining={remaining}"
        )
        end = "\n" if force_newline or completed_count == total_count else "\r"
        print(message, end=end, flush=True)

    def clean_one(family: dict[str, Any]) -> dict[str, Any]:
        candidate_id = family["candidate_id"]
        comparison_candidate = candidate_lookup["comparison"][candidate_id]
        comparison_key = comparison_cache_key(comparison_candidate)
        with comparison_cache_lock:
            comparison = comparison_cache.get(comparison_key)
        if comparison is None:
            fetched = extract_field_with_llm(field="comparison", candidate=comparison_candidate, llm_config=llm_config)
            fetched = comparison_cache_row(comparison_candidate, fetched)
            with comparison_cache_lock:
                comparison = comparison_cache.get(comparison_key)
                if comparison is None:
                    comparison = fetched
                    comparison_cache[comparison_key] = comparison
                    append_jsonl(paths["comparison_cache"], [comparison], sort_keys=False)
        fields = {
            "comparison": comparison,
            "outcome": extract_field_with_llm(field="outcome", candidate=candidate_lookup["outcome"][candidate_id], llm_config=llm_config),
            "timepoint": extract_field_with_llm(field="timepoint", candidate=candidate_lookup["timepoint"][candidate_id], llm_config=llm_config),
        }
        setting = assemble_setting(
            family=family,
            comparison=fields["comparison"],
            outcome=fields["outcome"],
            timepoint=fields["timepoint"],
            method=method_from_family(family),
        )
        setting["cleaning"] = {
            **(setting.get("cleaning") or {}),
            "method": "llm_direct_fields_v1",
            "field_methods": {field: fields[field].get("method") for field in FIELDS},
            "field_confidence": {field: fields[field].get("confidence") for field in FIELDS},
            "field_warnings": {field: fields[field].get("warnings") or [] for field in FIELDS},
            **comparison_cache_cleaning_metadata(comparison_candidate),
            "artifact": ARTIFACT_NAME,
        }
        return setting

    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        future_map = {executor.submit(clean_one, family): family for family in pending}
        print_progress()
        for future in as_completed(future_map):
            family = future_map[future]
            try:
                setting = future.result()
            except Exception as exc:  # pragma: no cover - depends on live LLM
                failure_count += 1
                row = {
                    "candidate_id": family["candidate_id"],
                    "review_id": family["review_id"],
                    "analysis_group": family["analysis_group"],
                    "analysis_number": family["analysis_number"],
                    "status": "llm_failed",
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
                failures.append(row)
                append_jsonl(paths["failures"], [row], sort_keys=False)
                completed_count += 1
                print_progress(force_newline=True)
                if max_failures > 0 and failure_count >= max_failures:
                    break
            else:
                append_jsonl(paths["settings"], [setting], sort_keys=False)
                settings_by_candidate[setting["candidate_id"]] = setting
                success_count += 1
                completed_count += 1
                print_progress()
        if completed_count < total_count:
            print_progress(force_newline=True)
    return failures


def _paths(output_root: Path) -> dict[str, Any]:
    return {
        "family_sources": output_root / "family_sources.jsonl",
        "settings": output_root / "setting_cleaned.jsonl",
        "raw_material": output_root / "setting_raw_material.jsonl",
        "comparison_cache": output_root / "comparison_cache.jsonl",
        "failures": output_root / "cleaning_failures.jsonl",
        "report": output_root / "cleaning_report.json",
        "source_manifest": output_root / "source_manifest.json",
        "field_candidates": {
            field: output_root / "field_candidates" / f"{field}_candidates.jsonl"
            for field in FIELDS
        },
    }


def _clear_outputs(paths: dict[str, Any]) -> None:
    values = [
        paths["family_sources"],
        paths["settings"],
        paths["raw_material"],
        paths["comparison_cache"],
        paths["failures"],
        paths["report"],
        paths["source_manifest"],
    ]
    values.extend(paths["field_candidates"].values())
    for path in values:
        if path.exists():
            path.unlink()


def _grade_gold_review_ids(grade_raw_root: Path) -> set[str]:
    path = grade_raw_root / "source" / "legacy_grade_benchmark_v2" / "intermediate" / "05_sof_gold_domains.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"Missing GRADE gold domains: {path}")
    return {str(row["review_id"]) for row in read_jsonl(path)}


def _filter_normalized(normalized: dict[str, list[dict[str, Any]]], *, review_ids: set[str]) -> dict[str, list[dict[str, Any]]]:
    return {
        key: [row for row in rows if str(row.get("review_id")) in review_ids]
        for key, rows in normalized.items()
    }


def _load_existing_cleaned_settings(*, meta_raw_root: Path, candidate_lookup: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    path = meta_raw_root / "intermediate" / "setting_cleaned.jsonl"
    if not path.exists():
        return {}
    return {
        row["candidate_id"]: row
        for row in read_jsonl(path)
        if row.get("candidate_id") in candidate_lookup
        and setting_has_valid_comparison_cache(row, candidate_lookup[row["candidate_id"]])
    }


def _same_family_identity(*, setting: dict[str, Any], family: dict[str, Any]) -> bool:
    return (
        str(setting.get("candidate_id")) == str(family.get("candidate_id"))
        and str(setting.get("review_id")) == str(family.get("review_id"))
        and str(setting.get("analysis_group")) == str(family.get("analysis_group"))
        and str(setting.get("analysis_number")) == str(family.get("analysis_number"))
        and _identity_text(setting.get("analysis_name")) == _identity_text(family.get("analysis_name"))
        and _identity_text(setting.get("analysis_group_name")) == _identity_text(family.get("analysis_group_name"))
    )


def _load_valid_existing_settings(
    path: Path,
    *,
    candidate_lookup: dict[str, dict[str, Any]],
    allowed_candidate_ids: set[str],
) -> dict[str, dict[str, Any]]:
    settings: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(path):
        candidate_id = str(row.get("candidate_id") or "")
        if candidate_id not in allowed_candidate_ids:
            continue
        candidate = candidate_lookup.get(candidate_id)
        if candidate is None or not setting_has_valid_comparison_cache(row, candidate):
            continue
        settings[candidate_id] = row
    return settings


def _rewrite_settings(path: Path, settings_by_candidate: dict[str, dict[str, Any]]) -> None:
    write_jsonl(path, sorted(settings_by_candidate.values(), key=lambda row: row["candidate_id"]), sort_keys=False)


def _with_reuse_marker(setting: dict[str, Any]) -> dict[str, Any]:
    cleaning = dict(setting.get("cleaning") or {})
    cleaning.setdefault("method", "llm_direct_fields_v1")
    cleaning["reused_from"] = "meta_analysis/intermediate/setting_cleaned.jsonl"
    cleaning["artifact"] = ARTIFACT_NAME
    return {**setting, "cleaning": cleaning}


def _completed_candidate_ids(path: Path, *, candidate_lookup: dict[str, dict[str, Any]]) -> set[str]:
    if not path.exists():
        return set()
    completed = set()
    for row in read_jsonl(path):
        candidate_id = str(row.get("candidate_id") or "")
        candidate = candidate_lookup.get(candidate_id)
        if candidate is not None and setting_has_valid_comparison_cache(row, candidate):
            completed.add(candidate_id)
    return completed


def _load_comparison_cache(path: Path, *, candidate_lookup: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    return {
        str(row.get("cache_key")): row
        for row in read_jsonl(path)
        if row.get("cache_key")
        and candidate_lookup.get(str(row.get("candidate_id") or "")) is not None
        and is_valid_comparison_cache_row(row, candidate_lookup[str(row.get("candidate_id") or "")])
    }


def _identity_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _build_raw_material(*, families: list[dict[str, Any]], settings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    family_by_candidate = {row["candidate_id"]: row for row in families}
    material = []
    for setting in sorted(settings, key=lambda row: row["candidate_id"]):
        family = family_by_candidate.get(setting["candidate_id"])
        if not family:
            continue
        material.append(
            {
                "raw_material_id": f"analysis-setting-raw::{setting['review_id']}::{setting['analysis_group']}::{setting['analysis_number']}",
                "candidate_id": setting["candidate_id"],
                "setting_family_id": setting["setting_family_id"],
                "review_id": setting["review_id"],
                "analysis_group": setting["analysis_group"],
                "analysis_number": setting["analysis_number"],
                "source_fields": {
                    "analysis_name": setting.get("analysis_name"),
                    "analysis_group_name": setting.get("analysis_group_name"),
                    "explicit_labels": family.get("explicit_labels") or {},
                },
                "llm_cleaned_setting": {
                    "population_scope": setting.get("population_scope"),
                    "comparison": setting.get("comparison"),
                    "comparison_structure": setting.get("comparison_structure"),
                    "outcome": setting.get("outcome"),
                    "timepoint": setting.get("timepoint"),
                },
                "official_method": setting.get("method") or {},
                "official_study_rows": family.get("study_row_source") or {},
                "official_subgroup_estimates": family.get("subgroup_estimate_source") or {"levels": [], "difference_test": {}},
                "scope_flags": setting.get("scope_flags") or {},
                "setting_quality": setting.get("setting_quality") or {},
                "source_provenance": setting.get("source_provenance") or {},
                "cleaning": setting.get("cleaning") or {},
            }
        )
    return material


def _write_grade_projection(*, output_root: Path, grade_raw_root: Path) -> None:
    target = grade_raw_root / "intermediate" / "setting_cleaning" / ARTIFACT_NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.resolve() != output_root.resolve():
        shutil.rmtree(target)
    if target.resolve() == output_root.resolve():
        return
    shutil.copytree(output_root, target, dirs_exist_ok=True)


def _read_failures(path: Path) -> list[dict[str, Any]]:
    return read_jsonl(path) if path.exists() else []


def _prune_resolved_failures(path: Path, *, completed_candidate_ids: set[str]) -> None:
    if not path.exists():
        return
    unresolved_by_candidate: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(path):
        candidate_id = str(row.get("candidate_id") or "")
        if not candidate_id or candidate_id in completed_candidate_ids:
            continue
        unresolved_by_candidate[candidate_id] = row
    write_jsonl(path, sorted(unresolved_by_candidate.values(), key=lambda row: str(row.get("candidate_id") or "")), sort_keys=False)


def _report(
    *,
    output_root: Path,
    review_ids: list[str],
    target_review_ids: list[str],
    normalized: dict[str, list[dict[str, Any]]],
    families: list[dict[str, Any]],
    settings: list[dict[str, Any]],
    reused_count: int,
    failures: list[dict[str, Any]],
    meta_raw_root: Path,
    grade_raw_root: Path,
    use_llm: bool,
    llm_config: str | Path | None,
) -> dict[str, Any]:
    warning_counts = Counter()
    ready_counts = Counter()
    for setting in settings:
        warning_counts.update((setting.get("cleaning") or {}).get("warnings") or [])
        quality = setting.get("setting_quality") or {}
        ready_counts.update(["ready" if quality.get("ready_for_downstream_setting_build") else "needs_review"])
    completed_ids = {str(row.get("candidate_id")) for row in settings}
    target_ids = {
        str(row.get("candidate_id"))
        for row in families
        if str(row.get("review_id")) in set(target_review_ids)
    }
    source_manifest = {
        "artifact": ARTIFACT_NAME,
        "output_root": str(output_root),
        "meta_raw_root": str(meta_raw_root),
        "grade_raw_root": str(grade_raw_root),
        "review_count": len(review_ids),
        "reviews": review_ids,
        "cleaning_target_review_count": len(target_review_ids),
        "cleaning_target_reviews": target_review_ids,
        "official_overall_row_count": len(normalized["overall"]),
        "official_data_row_count": len(normalized["data_rows"]),
        "official_subgroup_estimate_row_count": len(normalized["subgroup_estimates"]),
        "official_overall_sha256": _optional_sha256(meta_raw_root / "intermediate" / "official_overall_rows.jsonl"),
        "official_data_rows_sha256": _optional_sha256(meta_raw_root / "intermediate" / "official_data_rows.jsonl"),
        "official_subgroup_estimate_sha256": _optional_sha256(meta_raw_root / "intermediate" / "official_subgroup_estimate_rows.jsonl"),
        "llm_config": str(llm_config) if llm_config else None,
        "used_llm": use_llm,
    }
    return {
        "source_manifest": source_manifest,
        "family_count": len(families),
        "completed_count": len(settings),
        "missing_count": max(0, len(families) - len(settings)),
        "target_family_count": len(target_ids),
        "target_completed_count": len(target_ids & completed_ids),
        "target_missing_count": len(target_ids - completed_ids),
        "reused_count": sum(1 for row in settings if (row.get("cleaning") or {}).get("reused_from")),
        "newly_cleaned_count": sum(1 for row in settings if not (row.get("cleaning") or {}).get("reused_from")),
        "failure_count": len(failures),
        "failure_status_counts": dict(sorted(Counter(row.get("status") for row in failures).items())),
        "warning_counts": dict(sorted(warning_counts.items())),
        "setting_quality_counts": dict(sorted(ready_counts.items())),
        "data_type_counts": dict(sorted(Counter(setting.get("data_type") for setting in settings).items())),
        "review_counts": dict(sorted(Counter(setting.get("review_id") for setting in settings).items())),
        "source_hash": sha256_json(source_manifest),
    }


def _optional_sha256(path: Path) -> str | None:
    return sha256_file(path) if path.exists() else None


if __name__ == "__main__":  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(description="Build shared grade-required analysis setting artifacts.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--meta-raw-root", default=str(META_RAW_ROOT))
    parser.add_argument("--grade-raw-root", default=str(GRADE_RAW_ROOT))
    parser.add_argument("--llm-config", default=None)
    parser.add_argument("--use-llm", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--reviews", nargs="*", default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    start = time.time()
    report = build_grade_required_settings(
        output_root=Path(args.output_root),
        meta_raw_root=Path(args.meta_raw_root),
        grade_raw_root=Path(args.grade_raw_root),
        llm_config=args.llm_config,
        use_llm=args.use_llm,
        workers=args.workers,
        resume=args.resume,
        reviews=args.reviews,
        limit=args.limit,
    )
    print(json.dumps({"report": str(Path(args.output_root) / "cleaning_report.json"), "elapsed_seconds": round(time.time() - start, 2), **report}, ensure_ascii=False, indent=2))
