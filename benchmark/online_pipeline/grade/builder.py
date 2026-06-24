"""Build GRADE benchmark datasets aligned to SoF-row workflow output."""

from __future__ import annotations

import json
import re
import shutil
import time
import unicodedata
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from benchmark.online_pipeline.shared.building import (
    DEFAULT_SEED,
    RAW_DATA_DIR,
    ROOT,
    select_records,
    sha256_file,
    sha256_json,
    source_manifest,
    stable_order,
    ssl_context,
)
from benchmark.online_pipeline.shared.jsonl import read_jsonl, write_jsonl
from benchmark.online_pipeline.shared.jsonl import append_jsonl
from benchmark.online_pipeline.shared.report_utils import write_json
from benchmark.online_pipeline.shared.analysis_settings.builder import (
    build_grade_required_settings,
)
from benchmark.online_pipeline.meta_analysis.builder import build_raw as build_meta_analysis_raw


MODULE = "grade"
SOURCE = "grade_v1"
SOURCE_V2 = "grade_v2"
SOURCE_V3 = "grade_v4"
LEGACY_SOURCE_V3 = "grade_v3"
BUILDER_VERSION_V3 = "online-pipeline-builder-v4-grade"
ALIGNMENT_BUILDER_VERSION_V3 = "online-pipeline-builder-v4-grade-alignment"
ALIGNMENT_TASK_CACHE_VERSION = "grade-alignment-task-v2"
SMOKE_SIZE = 5
DEFAULT_V2_REVIEWS = (
    "CD000031",
    "CD010001",
    "CD013830",
)
UPSTREAM_GRADE_ROOT = Path("sr-cleaned/data/final/grade_benchmark_v2")
LEGACY_RELEASE_ROOT = Path("benchmark/GRADE")

DOMAIN_NAMES = (
    "risk_of_bias",
    "inconsistency",
    "indirectness",
    "imprecision",
)
DEFAULT_ALIGNMENT_REVIEWS = (
    "CD000031",
    "CD001431",
    "CD001506",
    "CD012079",
    "CD013827",
)


def _default_shared_settings_root() -> Path:
    return RAW_DATA_DIR / "analysis_settings" / "grade_required_v1"


def _grade_meta_workflow_root(raw_root: Path, *, alignment_name: str) -> Path:
    return raw_root / "intermediate" / f"meta_analysis_workflow_for_{alignment_name}"


def _prepare_grade_meta_workflow_root(*, workflow_root: Path) -> None:
    meta_root = RAW_DATA_DIR / "meta_analysis"
    source_root = meta_root / "source"
    if not (source_root / "official_analysis_csv_snapshot").exists():
        raise FileNotFoundError(f"Missing meta-analysis source snapshot: {source_root / 'official_analysis_csv_snapshot'}")
    target_source = workflow_root / "source"
    target_source.mkdir(parents=True, exist_ok=True)
    target_snapshot = target_source / "official_analysis_csv_snapshot"
    if not target_snapshot.exists():
        shutil.copytree(source_root / "official_analysis_csv_snapshot", target_snapshot)
    source_manifest = meta_root / "source_manifest.json"
    if source_manifest.exists():
        shutil.copy2(source_manifest, workflow_root / "source_manifest.json")


def _alignment_summary_path(raw_root: Path, *, alignment_name: str) -> Path:
    return raw_root / "intermediate" / alignment_name / "alignment_summary.json"


def _load_alignment_summary(raw_root: Path, *, alignment_name: str) -> dict[str, Any]:
    summary_path = _alignment_summary_path(raw_root, alignment_name=alignment_name)
    if not summary_path.exists():
        return {}
    try:
        return json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _required_alignment_builder_version(*, alignment_name: str, source: str = SOURCE_V3) -> str | None:
    if source == SOURCE_V3 and alignment_name.startswith("alignment_v3"):
        return ALIGNMENT_BUILDER_VERSION_V3
    return None


def _alignment_version_is_current(*, raw_root: Path, alignment_name: str, source: str = SOURCE_V3) -> bool:
    required = _required_alignment_builder_version(alignment_name=alignment_name, source=source)
    if required is None:
        return True
    summary = _load_alignment_summary(raw_root, alignment_name=alignment_name)
    return summary.get("builder_version") == required


def _alignment_is_formal_source(*, raw_root: Path, alignment_name: str, source: str = SOURCE_V3) -> bool:
    if source != SOURCE_V3:
        return True
    summary = _load_alignment_summary(raw_root, alignment_name=alignment_name)
    return summary.get("mode") == "llm"


def _task_cache_metadata(task: dict[str, Any]) -> dict[str, str]:
    return {
        "task_cache_version": ALIGNMENT_TASK_CACHE_VERSION,
        "task_payload_sha256": sha256_json(
            {
                "task_type": task.get("task_type"),
                "task_id": task.get("task_id"),
                "payload": task.get("payload") or {},
            }
        ),
    }


def build_alignment_v2(
    *,
    raw_root: Path = RAW_DATA_DIR / MODULE,
    reviews: list[str] | None = None,
    use_llm: bool = False,
    api_key: str | None = None,
    base_url: str = "https://api.openai.com",
    api_mode: str = "responses",
    model: str = "gpt-4.1-mini",
    workers: int = 1,
    resume: bool = False,
    limit_tables: int | None = None,
    limit_rows: int | None = None,
    timeout: int = 90,
    retries: int = 2,
    alignment_name: str = "alignment_v2",
    workflow_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build conservative SoF-row to workflow-setting alignment artifacts."""
    freeze_raw_snapshot(raw_root=raw_root)
    alignment_dir = raw_root / "intermediate" / alignment_name
    alignment_dir.mkdir(parents=True, exist_ok=True)

    raw_workflow_rows = workflow_rows or _build_workflow_row_universe(raw_data_root=RAW_DATA_DIR / "meta_analysis")
    workflow_rows, workflow_filter_report = _filter_workflow_rows_for_grade_alignment(raw_workflow_rows)
    settings_by_review = _workflow_groups_by_review(workflow_rows)
    sof_rows = _load_sof_rows_for_alignment(raw_root=raw_root)
    gold_by_sample = _load_sof_gold_by_sample(raw_root=raw_root)
    requested_reviews = set(reviews or DEFAULT_V2_REVIEWS)
    setting_reviews = set(settings_by_review)
    selected_rows = []
    for row in sof_rows:
        if row.get("review_id") not in requested_reviews or row.get("review_id") not in setting_reviews:
            continue
        alignment_input = _alignment_input_from_sof_row(row, gold_by_sample=gold_by_sample)
        if alignment_input.get("gold_available"):
            selected_rows.append(alignment_input)
    if limit_rows is not None:
        selected_rows = selected_rows[: max(0, limit_rows)]
    tables = _alignment_tables_from_rows(selected_rows)
    if limit_tables is not None:
        allowed_table_keys = {
            (table["review_id"], table["sof_table_id"])
            for table in tables[: max(0, limit_tables)]
        }
        selected_rows = [
            row for row in selected_rows if (row["review_id"], row["sof_table_id"]) in allowed_table_keys
        ]
        tables = _alignment_tables_from_rows(selected_rows)

    write_jsonl(alignment_dir / "workflow_setting_universe.raw.jsonl", raw_workflow_rows, sort_keys=False)
    write_jsonl(alignment_dir / "workflow_setting_universe.jsonl", workflow_rows, sort_keys=False)
    write_json(alignment_dir / "workflow_setting_filter_report.json", workflow_filter_report)
    write_jsonl(alignment_dir / "sof_alignment_inputs.jsonl", selected_rows, sort_keys=False)
    write_jsonl(alignment_dir / "review_candidate_families.jsonl", _candidate_family_records(settings_by_review, requested_reviews), sort_keys=False)

    table_tasks = _table_family_tasks(tables=tables, settings_by_review=settings_by_review)
    write_jsonl(alignment_dir / "table_family_tasks.jsonl", table_tasks, sort_keys=False)
    table_predictions_path = alignment_dir / "table_family_predictions.jsonl"
    if not resume and table_predictions_path.exists():
        table_predictions_path.unlink()
    table_task_ids = {task["task_id"] for task in table_tasks}
    table_predictions = (
        _load_existing_predictions(
            table_predictions_path,
            key_fields=("task_id",),
            allowed_keys=table_task_ids,
            expected_task_metadata={task["task_id"]: _task_cache_metadata(task) for task in table_tasks},
            reusable_statuses={"ok"},
        )
        if resume
        else {}
    )
    pending_table_tasks = [task for task in table_tasks if task["task_id"] not in table_predictions]
    if use_llm:
        if not api_key:
            raise RuntimeError("--use-llm requires --llm-config or --api-key")
        new_table_predictions = _run_llm_tasks(
            tasks=pending_table_tasks,
            task_type="table_family",
            api_key=api_key,
            base_url=base_url,
            api_mode=api_mode,
            model=model,
            workers=workers,
            timeout=timeout,
            retries=retries,
            output_path=table_predictions_path,
        )
    else:
        new_table_predictions = [_dry_table_prediction(task) for task in pending_table_tasks]
        append_jsonl(table_predictions_path, new_table_predictions, sort_keys=False)
    all_table_predictions = list(table_predictions.values()) + new_table_predictions
    write_jsonl(table_predictions_path, all_table_predictions, sort_keys=False)

    matched_family_keys = {
        (prediction["review_id"], prediction["sof_table_id"], prediction["analysis_group"])
        for prediction in all_table_predictions
        if prediction.get("match") is True and prediction.get("confidence") in {"high", "medium"}
    }
    row_tasks = _row_setting_tasks(
        alignment_inputs=selected_rows,
        settings_by_review=settings_by_review,
        matched_family_keys=matched_family_keys,
    )
    write_jsonl(alignment_dir / "row_setting_tasks.jsonl", row_tasks, sort_keys=False)
    row_predictions_path = alignment_dir / "row_setting_predictions.jsonl"
    if not resume and row_predictions_path.exists():
        row_predictions_path.unlink()
    row_task_ids = {task["task_id"] for task in row_tasks}
    row_predictions = (
        _load_existing_predictions(
            row_predictions_path,
            key_fields=("task_id",),
            allowed_keys=row_task_ids,
            expected_task_metadata={task["task_id"]: _task_cache_metadata(task) for task in row_tasks},
            reusable_statuses={"ok"},
        )
        if resume
        else {}
    )
    pending_row_tasks = [task for task in row_tasks if task["task_id"] not in row_predictions]
    if use_llm:
        new_row_predictions = _run_llm_tasks(
            tasks=pending_row_tasks,
            task_type="row_setting",
            api_key=api_key or "",
            base_url=base_url,
            api_mode=api_mode,
            model=model,
            workers=workers,
            timeout=timeout,
            retries=retries,
            output_path=row_predictions_path,
        )
    else:
        new_row_predictions = [_dry_row_prediction(task) for task in pending_row_tasks]
        append_jsonl(row_predictions_path, new_row_predictions, sort_keys=False)
    all_row_predictions = list(row_predictions.values()) + new_row_predictions
    write_jsonl(row_predictions_path, all_row_predictions, sort_keys=False)

    results, audit_rows = _resolve_alignment_results_v2(
        alignment_inputs=selected_rows,
        workflow_rows=workflow_rows,
        table_predictions=all_table_predictions,
        row_predictions=all_row_predictions,
    )
    summary = _alignment_v2_summary(
        alignment_name=alignment_name,
        alignment_inputs=selected_rows,
        tables=tables,
        workflow_rows=workflow_rows,
        table_tasks=table_tasks,
        table_predictions=all_table_predictions,
        row_tasks=row_tasks,
        row_predictions=all_row_predictions,
        results=results,
        audit_rows=audit_rows,
        workflow_filter_report=workflow_filter_report,
        use_llm=use_llm,
        model=model,
        api_mode=api_mode if use_llm else None,
    )
    write_jsonl(alignment_dir / "alignment_results.jsonl", results, sort_keys=False)
    write_jsonl(alignment_dir / "alignment_audit.jsonl", audit_rows, sort_keys=False)
    write_jsonl(alignment_dir / "matched_examples.jsonl", _alignment_examples(results=results, alignment_inputs=selected_rows, workflow_rows=workflow_rows, status="matched"), sort_keys=False)
    write_jsonl(alignment_dir / "rejected_examples.jsonl", _alignment_examples(results=audit_rows, alignment_inputs=selected_rows, workflow_rows=workflow_rows, status=None), sort_keys=False)
    write_json(alignment_dir / "alignment_summary.json", summary)
    return summary


def build_dataset_v2(
    *,
    dataset_name: str,
    raw_root: Path = RAW_DATA_DIR / MODULE,
    sample_size: int | None = None,
    seed: str = DEFAULT_SEED,
    reviews: list[str] | None = None,
    use_llm: bool = False,
    api_key: str | None = None,
    base_url: str = "https://api.openai.com",
    api_mode: str = "responses",
    model: str = "gpt-4.1-mini",
    workers: int = 1,
    resume: bool = False,
    limit_tables: int | None = None,
    limit_rows: int | None = None,
    timeout: int = 90,
    retries: int = 2,
) -> dict[str, Any]:
    alignment_dir = raw_root / "intermediate" / "alignment_v2"
    if not (alignment_dir / "alignment_results.jsonl").exists() or use_llm:
        build_alignment_v2(
            raw_root=raw_root,
            reviews=reviews,
            use_llm=use_llm,
            api_key=api_key,
            base_url=base_url,
            api_mode=api_mode,
            model=model,
            workers=workers,
            resume=resume,
            limit_tables=limit_tables,
            limit_rows=limit_rows,
            timeout=timeout,
            retries=retries,
        )
    records, manifest, analysis = load_source_v2(raw_root=raw_root)
    selected = select_records(records, sample_size=sample_size, seed=seed, module=MODULE)
    splits = build_splits(selected, seed=seed, legacy_split_root=raw_root / "source" / "legacy_release_splits")
    dataset_result = write_dataset(
        dataset_name=dataset_name,
        records=selected,
        splits=splits,
        source=SOURCE_V2,
        source_manifest_data=manifest,
        seed=seed,
        sample_size=sample_size,
        source_record_count=analysis["matched_row_count"],
        dataset_analysis_data=analysis,
    )
    return {
        **dataset_result,
        "source_manifest": manifest,
    }


def build_alignment_v3(
    *,
    raw_root: Path = RAW_DATA_DIR / MODULE,
    shared_settings_root: Path | None = None,
    reviews: list[str] | None = None,
    use_llm: bool = False,
    api_key: str | None = None,
    base_url: str = "https://api.openai.com",
    api_mode: str = "responses",
    model: str = "gpt-4.1-mini",
    workers: int = 1,
    resume: bool = False,
    limit_tables: int | None = None,
    limit_rows: int | None = None,
    timeout: int = 90,
    retries: int = 2,
    alignment_name: str = "alignment_v3",
) -> dict[str, Any]:
    settings_root = shared_settings_root or _default_shared_settings_root()
    if not (settings_root / "setting_cleaned.jsonl").exists():
        build_grade_required_settings(output_root=settings_root, use_llm=False, resume=True)
    workflow_root = _grade_meta_workflow_root(raw_root, alignment_name=alignment_name)
    _prepare_grade_meta_workflow_root(workflow_root=workflow_root)
    build_meta_analysis_raw(
        raw_root=workflow_root,
        shared_settings_root=settings_root,
    )
    workflow_rows = _build_workflow_row_universe(raw_data_root=workflow_root)
    target_reviews = reviews or _all_gold_review_ids_for_alignment(raw_root=raw_root)
    return build_alignment_v2(
        raw_root=raw_root,
        reviews=target_reviews,
        use_llm=use_llm,
        api_key=api_key,
        base_url=base_url,
        api_mode=api_mode,
        model=model,
        workers=workers,
        resume=resume,
        limit_tables=limit_tables,
        limit_rows=limit_rows,
        timeout=timeout,
        retries=retries,
        alignment_name=alignment_name,
        workflow_rows=workflow_rows,
    )


def build_dataset_v3(
    *,
    dataset_name: str,
    source: str = SOURCE_V3,
    raw_root: Path = RAW_DATA_DIR / MODULE,
    shared_settings_root: Path | None = None,
    sample_size: int | None = None,
    seed: str = DEFAULT_SEED,
    reviews: list[str] | None = None,
    use_llm: bool = False,
    api_key: str | None = None,
    base_url: str = "https://api.openai.com",
    api_mode: str = "responses",
    model: str = "gpt-4.1-mini",
    workers: int = 1,
    resume: bool = False,
    limit_tables: int | None = None,
    limit_rows: int | None = None,
    timeout: int = 90,
    retries: int = 2,
    alignment_name: str = "alignment_v3",
) -> dict[str, Any]:
    alignment_dir = raw_root / "intermediate" / alignment_name
    if (
        not (alignment_dir / "alignment_results.jsonl").exists()
        or use_llm
        or not _alignment_version_is_current(raw_root=raw_root, alignment_name=alignment_name, source=source)
        or not _alignment_is_formal_source(raw_root=raw_root, alignment_name=alignment_name, source=source)
    ):
        if source == SOURCE_V3 and not use_llm:
            summary = _load_alignment_summary(raw_root, alignment_name=alignment_name)
            if not (alignment_dir / "alignment_results.jsonl").exists():
                raise RuntimeError(
                    f"{SOURCE_V3} requires a live LLM alignment. Build it first with "
                    "`grade/raw_builder.py build-alignment-v3 --use-llm --resume`, then rerun dataset build."
                )
            required = _required_alignment_builder_version(alignment_name=alignment_name, source=source)
            if summary.get("builder_version") != required:
                raise RuntimeError(
                    f"Existing {alignment_name} was built with builder_version={summary.get('builder_version')!r}; "
                    f"{SOURCE_V3} requires {required!r}. Rebuild alignment with --use-llm --resume after "
                    "the shared GRADE settings are complete, or build legacy source grade_v3 explicitly."
                )
            raise RuntimeError(
                f"Existing {alignment_name} has mode={summary.get('mode')!r}; {SOURCE_V3} requires a live LLM alignment. "
                "Rebuild alignment with --use-llm --resume after the shared GRADE settings are complete."
            )
        build_alignment_v3(
            raw_root=raw_root,
            shared_settings_root=shared_settings_root,
            reviews=reviews,
            use_llm=use_llm,
            api_key=api_key,
            base_url=base_url,
            api_mode=api_mode,
            model=model,
            workers=workers,
            resume=resume,
            limit_tables=limit_tables,
            limit_rows=limit_rows,
            timeout=timeout,
            retries=retries,
            alignment_name=alignment_name,
        )
    records, manifest, analysis = load_source_v3(raw_root=raw_root, alignment_name=alignment_name, source=source)
    selected = select_records(records, sample_size=sample_size, seed=seed, module=MODULE)
    splits = build_splits(selected, seed=seed, legacy_split_root=raw_root / "source" / "legacy_release_splits")
    dataset_result = write_dataset(
        dataset_name=dataset_name,
        records=selected,
        splits=splits,
        source=source,
        source_manifest_data=manifest,
        seed=seed,
        sample_size=sample_size,
        source_record_count=analysis["matched_row_count"],
        dataset_analysis_data=analysis,
    )
    return {
        **dataset_result,
        "source_manifest": manifest,
    }


def load_source_v2(*, raw_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    alignment_dir = raw_root / "intermediate" / "alignment_v2"
    results_path = alignment_dir / "alignment_results.jsonl"
    if not results_path.exists():
        build_alignment_v2(raw_root=raw_root)
    records = _records_from_alignment_v2(raw_root=raw_root)
    analysis = json.loads((alignment_dir / "alignment_summary.json").read_text(encoding="utf-8"))
    manifest = source_manifest(
        source=SOURCE_V2,
        records=records,
        source_url=str(raw_root),
        raw_sha256=_raw_snapshot_sha256_v2(raw_root),
        extra={
            "loader": "sof_rows_gold_domains_plus_meta_analysis_workflow_rows_alignment_v2",
            "raw_root": str(raw_root),
            "alignment_dir": str(alignment_dir),
            "matched_row_count": analysis["matched_row_count"],
            "input_row_count": analysis["input_row_count"],
            "workflow_row_universe_count": analysis["workflow_row_universe_count"],
            "question_text_policy": "review.title",
            "question_pico_policy": "review.pico",
        },
    )
    return records, manifest, analysis


def load_source_v3(*, raw_root: Path, alignment_name: str = "alignment_v3", source: str = SOURCE_V3) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    alignment_dir = raw_root / "intermediate" / alignment_name
    results_path = alignment_dir / "alignment_results.jsonl"
    if not results_path.exists():
        build_alignment_v3(raw_root=raw_root, alignment_name=alignment_name)
    if not _alignment_version_is_current(raw_root=raw_root, alignment_name=alignment_name, source=source):
        required = _required_alignment_builder_version(alignment_name=alignment_name, source=source)
        existing = _load_alignment_summary(raw_root, alignment_name=alignment_name).get("builder_version")
        raise RuntimeError(
            f"Existing {alignment_name} was built with builder_version={existing!r}; "
            f"{source} requires {required!r}. Rebuild the alignment before loading this source."
        )
    if not _alignment_is_formal_source(raw_root=raw_root, alignment_name=alignment_name, source=source):
        mode = _load_alignment_summary(raw_root, alignment_name=alignment_name).get("mode")
        raise RuntimeError(
            f"Existing {alignment_name} has mode={mode!r}; {SOURCE_V3} requires a live LLM alignment. "
            "Use a non-default alignment_name for dry-run smoke artifacts."
        )
    records = _records_from_alignment(raw_root=raw_root, alignment_name=alignment_name)
    analysis = json.loads((alignment_dir / "alignment_summary.json").read_text(encoding="utf-8"))
    analysis = {**analysis, "dataset_input_coverage": _grade_dataset_input_coverage(records)}
    manifest = source_manifest(
        source=source,
        records=records,
        source_url=str(raw_root),
        raw_sha256=_raw_snapshot_sha256_alignment(raw_root, alignment_name=alignment_name),
        extra={
            "builder_version": BUILDER_VERSION_V3,
            "loader": "sof_rows_gold_domains_plus_shared_grade_required_analysis_settings_alignment_v3",
            "raw_root": str(raw_root),
            "alignment_dir": str(alignment_dir),
            "alignment_name": alignment_name,
            "matched_row_count": analysis["matched_row_count"],
            "input_row_count": analysis["input_row_count"],
            "workflow_row_universe_count": analysis["workflow_row_universe_count"],
            "question_text_policy": "review.title",
            "question_pico_policy": "review.pico",
        },
    )
    return records, manifest, analysis


def run_alignment_probe(
    *,
    raw_root: Path = RAW_DATA_DIR / MODULE,
    reviews: list[str] | None = None,
    use_llm: bool = False,
    api_key: str | None = None,
    base_url: str = "https://api.openai.com",
    api_mode: str = "responses",
    model: str = "gpt-4.1-mini",
    workers: int = 1,
    resume: bool = False,
    limit_tables: int | None = None,
    limit_rows: int | None = None,
    timeout: int = 90,
    retries: int = 2,
) -> dict[str, Any]:
    """Run a small SoF-table/row to workflow-setting alignment probe."""
    freeze_raw_snapshot(raw_root=raw_root)
    probe_dir = raw_root / "intermediate" / "alignment_probe"
    probe_dir.mkdir(parents=True, exist_ok=True)

    workflow_rows = _build_workflow_row_universe(raw_data_root=RAW_DATA_DIR / "meta_analysis")
    settings_by_review = _workflow_groups_by_review(workflow_rows)
    sof_rows = _load_sof_rows_for_alignment(raw_root=raw_root)
    gold_by_sample = _load_sof_gold_by_sample(raw_root=raw_root)
    requested_reviews = set(reviews or DEFAULT_ALIGNMENT_REVIEWS)
    setting_reviews = set(settings_by_review)
    selected_rows = [
        _alignment_input_from_sof_row(row, gold_by_sample=gold_by_sample)
        for row in sof_rows
        if row.get("review_id") in requested_reviews and row.get("review_id") in setting_reviews
    ]
    if limit_rows is not None:
        selected_rows = selected_rows[: max(0, limit_rows)]
    tables = _alignment_tables_from_rows(selected_rows)
    if limit_tables is not None:
        allowed_table_keys = {
            (table["review_id"], table["sof_table_id"])
            for table in tables[: max(0, limit_tables)]
        }
        selected_rows = [
            row for row in selected_rows if (row["review_id"], row["sof_table_id"]) in allowed_table_keys
        ]
        tables = _alignment_tables_from_rows(selected_rows)

    write_jsonl(probe_dir / "workflow_candidate_rows.jsonl", workflow_rows, sort_keys=False)
    write_jsonl(probe_dir / "alignment_inputs.jsonl", selected_rows, sort_keys=False)
    write_jsonl(probe_dir / "review_candidate_families.jsonl", _candidate_family_records(settings_by_review, requested_reviews), sort_keys=False)

    table_tasks = _table_family_tasks(tables=tables, settings_by_review=settings_by_review)
    table_predictions_path = probe_dir / "table_family_predictions.jsonl"
    if not resume and table_predictions_path.exists():
        table_predictions_path.unlink()
    table_task_ids = {task["task_id"] for task in table_tasks}
    table_predictions = (
        _load_existing_predictions(
            table_predictions_path,
            key_fields=("task_id",),
            allowed_keys=table_task_ids,
            expected_task_metadata={task["task_id"]: _task_cache_metadata(task) for task in table_tasks},
            reusable_statuses={"ok"},
        )
        if resume
        else {}
    )
    pending_table_tasks = [task for task in table_tasks if task["task_id"] not in table_predictions]
    if use_llm:
        if not api_key:
            raise RuntimeError("--use-llm requires --llm-config or --api-key")
        new_table_predictions = _run_llm_tasks(
            tasks=pending_table_tasks,
            task_type="table_family",
            api_key=api_key,
            base_url=base_url,
            api_mode=api_mode,
            model=model,
            workers=workers,
            timeout=timeout,
            retries=retries,
            output_path=table_predictions_path,
        )
    else:
        new_table_predictions = [_dry_table_prediction(task) for task in pending_table_tasks]
        if not resume:
            write_jsonl(table_predictions_path, new_table_predictions, sort_keys=False)
        else:
            append_jsonl(table_predictions_path, new_table_predictions, sort_keys=False)
    table_predictions = list(table_predictions.values()) + new_table_predictions
    write_jsonl(table_predictions_path, table_predictions, sort_keys=False)

    matched_family_keys = {
        (prediction["review_id"], prediction["sof_table_id"], prediction["analysis_group"])
        for prediction in table_predictions
        if prediction.get("match") is True and prediction.get("confidence") in {"high", "medium", "low"}
    }
    row_tasks = _row_setting_tasks(
        alignment_inputs=selected_rows,
        settings_by_review=settings_by_review,
        matched_family_keys=matched_family_keys,
    )
    row_predictions_path = probe_dir / "row_setting_predictions.jsonl"
    if not resume and row_predictions_path.exists():
        row_predictions_path.unlink()
    row_task_ids = {task["task_id"] for task in row_tasks}
    row_predictions = (
        _load_existing_predictions(
            row_predictions_path,
            key_fields=("task_id",),
            allowed_keys=row_task_ids,
            expected_task_metadata={task["task_id"]: _task_cache_metadata(task) for task in row_tasks},
            reusable_statuses={"ok"},
        )
        if resume
        else {}
    )
    pending_row_tasks = [task for task in row_tasks if task["task_id"] not in row_predictions]
    if use_llm:
        new_row_predictions = _run_llm_tasks(
            tasks=pending_row_tasks,
            task_type="row_setting",
            api_key=api_key or "",
            base_url=base_url,
            api_mode=api_mode,
            model=model,
            workers=workers,
            timeout=timeout,
            retries=retries,
            output_path=row_predictions_path,
        )
    else:
        new_row_predictions = [_dry_row_prediction(task) for task in pending_row_tasks]
        if not resume:
            write_jsonl(row_predictions_path, new_row_predictions, sort_keys=False)
        else:
            append_jsonl(row_predictions_path, new_row_predictions, sort_keys=False)
    row_predictions = list(row_predictions.values()) + new_row_predictions
    write_jsonl(row_predictions_path, row_predictions, sort_keys=False)

    results, audit_rows = _resolve_alignment_results(
        alignment_inputs=selected_rows,
        workflow_rows=workflow_rows,
        row_predictions=row_predictions,
    )
    summary = _alignment_probe_summary(
        alignment_inputs=selected_rows,
        tables=tables,
        table_tasks=table_tasks,
        table_predictions=table_predictions,
        row_tasks=row_tasks,
        row_predictions=row_predictions,
        results=results,
        audit_rows=audit_rows,
        use_llm=use_llm,
        model=model,
        api_mode=api_mode if use_llm else None,
    )
    write_jsonl(probe_dir / "alignment_results.jsonl", results, sort_keys=False)
    write_jsonl(probe_dir / "alignment_audit.jsonl", audit_rows, sort_keys=False)
    write_json(probe_dir / "alignment_summary.json", summary)
    return summary


def build_dataset(
    *,
    source: str,
    dataset_name: str,
    sample_size: int | None = None,
    seed: str = DEFAULT_SEED,
    source_url: str | None = None,
) -> dict[str, Any]:
    if source != SOURCE:
        raise ValueError(f"Unsupported grade source: {source}")
    raw_root = Path(source_url) if source_url else RAW_DATA_DIR / MODULE
    if not _raw_snapshot_exists(raw_root):
        freeze_raw_snapshot(raw_root=raw_root)
    raw_result = build_raw(raw_root=raw_root)
    records, manifest, analysis = load_source(raw_root=raw_root)
    selected = select_records(records, sample_size=sample_size, seed=seed, module=MODULE)
    splits = build_splits(selected, seed=seed, legacy_split_root=raw_root / "source" / "legacy_release_splits")
    dataset_result = write_dataset(
        dataset_name=dataset_name,
        records=selected,
        splits=splits,
        source=source,
        source_manifest_data=manifest,
        seed=seed,
        sample_size=sample_size,
        source_record_count=analysis["shared_row_count"],
        dataset_analysis_data={**analysis, "raw_build": raw_result},
    )
    return {
        **dataset_result,
        "source_manifest": manifest,
    }


def freeze_raw_snapshot(*, raw_root: Path = RAW_DATA_DIR / MODULE) -> dict[str, Any]:
    source_dir = raw_root / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    legacy_root = source_dir / "legacy_grade_benchmark_v2"
    legacy_root.mkdir(parents=True, exist_ok=True)
    split_root = source_dir / "legacy_release_splits"
    split_root.mkdir(parents=True, exist_ok=True)

    copied_files: list[str] = []
    required_existing = [
        legacy_root / "intermediate" / "04_sof_rows_cleaned.jsonl",
        legacy_root / "intermediate" / "05_sof_gold_domains.jsonl",
        split_root / "review_dev.txt",
        split_root / "review_test.txt",
    ]
    if not UPSTREAM_GRADE_ROOT.exists() and all(path.exists() for path in required_existing):
        summary = {
            "source": "grade_raw_v2_sources",
            "upstream_grade_root": str(UPSTREAM_GRADE_ROOT),
            "upstream_missing": True,
            "raw_data_snapshot_reused": True,
            "legacy_release_root": str(LEGACY_RELEASE_ROOT),
            "copied_file_count": 0,
            "question_text_policy": "review.title",
            "question_pico_policy": "review.pico",
            "note": "Existing frozen raw_data/grade/source snapshot reused; ordinary benchmark builds do not require sr-cleaned.",
        }
        write_json(raw_root / "source_manifest.json", summary)
        return summary
    if not UPSTREAM_GRADE_ROOT.exists():
        raise FileNotFoundError(
            f"Missing upstream GRADE source root: {UPSTREAM_GRADE_ROOT}; "
            f"also missing required frozen raw_data files under {source_dir}"
        )

    upstream_files = [
        UPSTREAM_GRADE_ROOT / "intermediate" / "04_sof_rows_cleaned.jsonl",
        UPSTREAM_GRADE_ROOT / "intermediate" / "05_sof_gold_domains.jsonl",
        UPSTREAM_GRADE_ROOT / "summary.json",
        UPSTREAM_GRADE_ROOT / "MANIFEST.json",
        UPSTREAM_GRADE_ROOT / "README.md",
    ]
    for source_path in upstream_files:
        if not source_path.exists():
            raise FileNotFoundError(f"Missing upstream GRADE source file: {source_path}")
        target_path = legacy_root / source_path.relative_to(UPSTREAM_GRADE_ROOT)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if not target_path.exists() or sha256_file(source_path) != sha256_file(target_path):
            shutil.copy2(source_path, target_path)
        copied_files.append(str(target_path.relative_to(raw_root)))

    for split_name in ("review_dev.txt", "review_test.txt", "summary.json", "validation_summary.json"):
        source_path = LEGACY_RELEASE_ROOT / "splits" / split_name
        if not source_path.exists():
            raise FileNotFoundError(f"Missing legacy split file: {source_path}")
        target_path = split_root / split_name
        if not target_path.exists() or sha256_file(source_path) != sha256_file(target_path):
            shutil.copy2(source_path, target_path)
        copied_files.append(str(target_path.relative_to(raw_root)))

    summary = {
        "source": "grade_raw_v2_sources",
        "upstream_grade_root": str(UPSTREAM_GRADE_ROOT),
        "upstream_missing": False,
        "raw_data_snapshot_reused": False,
        "legacy_release_root": str(LEGACY_RELEASE_ROOT),
        "copied_file_count": len(copied_files),
        "question_text_policy": "review.title",
        "question_pico_policy": "review.pico",
        "note": (
            "Frozen raw source includes only SoF cleaned rows, four-domain golds, release metadata, "
            "and review split manifests. Legacy benchmark_core and legacy SoF-analysis alignment files "
            "are intentionally excluded from the GRADE v2 build path."
        ),
    }
    write_json(raw_root / "source_manifest.json", summary)
    return summary


def build_raw(*, raw_root: Path = RAW_DATA_DIR / MODULE) -> dict[str, Any]:
    source_dir = raw_root / "source" / "legacy_grade_benchmark_v2"
    intermediate_dir = raw_root / "intermediate"
    intermediate_dir.mkdir(parents=True, exist_ok=True)

    workflow_rows = _build_workflow_row_universe(raw_data_root=RAW_DATA_DIR / "meta_analysis")
    legacy_rows = _load_legacy_grade_rows(source_dir=source_dir)
    mapped_rows, audit_rows = _map_rows_to_workflow(legacy_rows=legacy_rows, workflow_rows=workflow_rows)
    analysis = _raw_quality_report(
        workflow_rows=workflow_rows,
        legacy_rows=legacy_rows,
        mapped_rows=mapped_rows,
        audit_rows=audit_rows,
    )

    write_jsonl(intermediate_dir / "workflow_row_universe.jsonl", workflow_rows, sort_keys=False)
    write_jsonl(intermediate_dir / "legacy_grade_row_records.jsonl", legacy_rows, sort_keys=False)
    write_jsonl(intermediate_dir / "row_workflow_mapped.jsonl", mapped_rows, sort_keys=False)
    write_jsonl(intermediate_dir / "row_alignment_audit.jsonl", audit_rows, sort_keys=False)
    write_json(intermediate_dir / "raw_quality_report.json", analysis)
    return analysis


def load_source(*, raw_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    mapped_path = raw_root / "intermediate" / "row_workflow_mapped.jsonl"
    if not mapped_path.exists():
        build_raw(raw_root=raw_root)
    mapped_rows = read_jsonl(mapped_path)
    records = _records_from_mapped_rows(mapped_rows)
    analysis = json.loads((raw_root / "intermediate" / "raw_quality_report.json").read_text(encoding="utf-8"))
    manifest = source_manifest(
        source=SOURCE,
        records=records,
        source_url=str(raw_root),
        raw_sha256=_raw_snapshot_sha256(raw_root),
        extra={
            "loader": "sr_cleaned_grade_v2_plus_meta_analysis_workflow_rows",
            "raw_root": str(raw_root),
            "source_manifest": str(raw_root / "source_manifest.json"),
            "shared_row_count": analysis["shared_row_count"],
            "workflow_row_universe_count": analysis["workflow_row_universe_count"],
            "matched_row_count": analysis["matched_row_count"],
            "dropped_row_count": analysis["dropped_row_count"],
            "question_text_policy": "review.title",
            "question_pico_policy": "review.pico",
        },
    )
    return records, manifest, analysis


def build_splits(
    records: list[dict[str, Any]],
    *,
    seed: str = DEFAULT_SEED,
    legacy_split_root: Path,
) -> dict[str, list[dict[str, Any]]]:
    dev_reviews = {line.strip() for line in (legacy_split_root / "review_dev.txt").read_text(encoding="utf-8").splitlines() if line.strip()}
    test_reviews = {line.strip() for line in (legacy_split_root / "review_test.txt").read_text(encoding="utf-8").splitlines() if line.strip()}
    dev = [record for record in records if record["review_id"] in dev_reviews]
    test = [record for record in records if record["review_id"] in test_reviews]
    smoke_source = stable_order(dev or test or records, seed=f"{seed}:grade:smoke", module=MODULE)
    smoke = smoke_source[: min(SMOKE_SIZE, len(smoke_source))]
    return {"smoke": smoke, "dev": dev, "test": test}


def write_dataset(
    *,
    dataset_name: str,
    records: list[dict[str, Any]],
    splits: dict[str, list[dict[str, Any]]],
    source: str,
    source_manifest_data: dict[str, Any],
    seed: str,
    sample_size: int | None,
    source_record_count: int,
    dataset_analysis_data: dict[str, Any],
) -> dict[str, Any]:
    builder_version = (
        BUILDER_VERSION_V3
        if source in {SOURCE_V3, LEGACY_SOURCE_V3}
        else "online-pipeline-builder-v2-grade"
        if source == SOURCE_V2
        else "online-pipeline-builder-v1-grade"
    )

    shared_rows = list({record["shared_row"]["sof_row_id"]: record["shared_row"] for record in records}.values())
    shared_rows = sorted(shared_rows, key=lambda row: row["sof_row_id"])

    subtask_counts: dict[str, dict[str, int]] = {}
    materialized_splits: dict[str, dict[str, dict[str, Any]]] = {
        split_name: {} for split_name in splits
    }
    dataset_dirs: dict[str, str] = {}
    for domain in DOMAIN_NAMES:
        domain_records = [record for record in records if record["domain"] == domain]
        domain_dir = ROOT / MODULE / domain / "datasets" / dataset_name
        dataset_dirs[domain] = str(domain_dir)
        if domain_dir.exists():
            shutil.rmtree(domain_dir)
        write_jsonl(domain_dir / "shared" / "row_records.jsonl", _shared_rows_for_records(domain_records), sort_keys=False)
        _write_records(domain_dir, domain_records)
        split_counts = {"all": len(domain_records)}
        for split_name, split_records in splits.items():
            split_source_ids = {record["source_id"] for record in split_records}
            sub_records = [record for record in domain_records if record["source_id"] in split_source_ids]
            if split_name == "smoke" and not sub_records and domain_records:
                sub_records = stable_order(domain_records, seed=f"{seed}:grade:{domain}:smoke", module=MODULE)[: min(SMOKE_SIZE, len(domain_records))]
            _write_records(domain_dir / "splits" / split_name, sub_records)
            materialized_splits.setdefault(split_name, {}).update({record["source_id"]: record for record in sub_records})
            split_counts[split_name] = len(sub_records)
        _write_domain_schema(domain_dir / "schema.md", domain=domain)
        _write_domain_manifests(
            domain_dir=domain_dir,
            domain=domain,
            records=domain_records,
            split_counts=split_counts,
            builder_version=builder_version,
            source=source,
            source_manifest_data=source_manifest_data,
            seed=seed,
            sample_size=sample_size,
            source_record_count=source_record_count,
            dataset_analysis_data=dataset_analysis_data,
        )
        subtask_counts[domain] = split_counts

    split_manifest = {
        "builder_version": builder_version,
        "seed": seed,
        "module": MODULE,
        "dataset_name": dataset_name,
        "source": source,
        "sample_size": sample_size,
        "source_record_count": source_record_count,
        "selected_count": len(records),
        "split_strategy": "legacy_review_dev_test_plus_seeded_smoke_from_dev",
        "shared_rows": {
            "count": len(shared_rows),
            "path_policy": "<domain>/datasets/<dataset_name>/shared/row_records.jsonl",
        },
        "domains": {
            domain: {
                "count": counts["all"],
                "split_counts": {name: count for name, count in counts.items() if name != "all"},
                "dataset_path": str(Path(domain) / "datasets" / dataset_name),
            }
            for domain, counts in subtask_counts.items()
        },
        "splits": {
            split_name: {
                "count": len(split_records),
                "instance_ids": [record["instance"]["instance_id"] for record in sorted(split_records, key=lambda item: item["source_id"])],
            }
            for split_name, split_records in {
                "all": records,
                **{
                    name: list(records_by_id.values())
                    for name, records_by_id in materialized_splits.items()
                },
            }.items()
        },
    }
    build_manifest = {
        "builder_version": builder_version,
        "module": MODULE,
        "dataset_name": dataset_name,
        "source": source,
        "sample_size": sample_size,
        "source_record_count": source_record_count,
        "selected_count": len(records),
        "seed": seed,
        "source_manifest_sha256": sha256_json(source_manifest_data),
        "split_manifest_sha256": sha256_json(split_manifest),
    }
    return {
        "dataset_dirs": dataset_dirs,
        "build_manifest": build_manifest,
        "split_manifest": split_manifest,
    }


def _build_workflow_row_universe(*, raw_data_root: Path) -> list[dict[str, Any]]:
    intermediate = raw_data_root / "intermediate"
    analysis_settings = read_jsonl(intermediate / "analysis_settings.jsonl")
    overall_estimates = read_jsonl(intermediate / "overall_estimates.jsonl")
    subgroup_results = read_jsonl(intermediate / "subgroup_results.jsonl")
    study_result_rows = read_jsonl(intermediate / "study_result_rows.jsonl")
    analysis_methods = read_jsonl(intermediate / "analysis_methods.jsonl")

    study_rows_by_setting: dict[str, list[dict[str, Any]]] = defaultdict(list)
    study_rows_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in study_result_rows:
        study_rows_by_setting[str(row["setting_id"])].append(row)
        setting_family_id = str(row.get("setting_family_id") or "")
        if not setting_family_id:
            parts = str(row.get("setting_id") or "").split("::")
            if len(parts) >= 5:
                setting_family_id = f"setting-family::{parts[2]}::{parts[3]}::{parts[4]}"
        if setting_family_id:
            study_rows_by_family[setting_family_id].append(row)
    method_by_setting = {str(row["setting_id"]): row for row in analysis_methods}
    subgroup_result_by_family = {str(row["setting_family_id"]): row for row in subgroup_results}

    rows: list[dict[str, Any]] = []
    for estimate in overall_estimates:
        setting_id = str(estimate["setting_id"])
        setting = next(row for row in analysis_settings if str(row["setting_id"]) == setting_id)
        family_id = str(setting["setting_family_id"])
        study_rows = study_rows_by_setting.get(setting_id, []) or study_rows_by_family.get(family_id, [])
        estimate = dict(estimate)
        if study_rows and not estimate.get("included_study_ids"):
            estimate["included_study_ids"] = _unique_nonempty(row.get("study_id") for row in study_rows)
        if study_rows and not estimate.get("study_count"):
            estimate["study_count"] = len({str(row.get("study_id")) for row in study_rows if row.get("study_id")})
        if study_rows and not estimate.get("participant_count"):
            participant_count = _participant_count_from_study_rows(study_rows)
            if participant_count is not None:
                estimate["participant_count"] = participant_count
        subgroup_group = subgroup_result_by_family.get(family_id, {})
        rows.append(
            {
                "source_id": f"grade-row::{setting_id}",
                "sof_row_id": f"sof-row::{setting_id}",
                "review_id": str(setting["review_id"]),
                "setting_id": setting_id,
                "setting_family_id": family_id,
                "candidate_id": str(setting["candidate_id"]),
                "row_label": ((setting.get("outcome") or {}).get("label") or None),
                "analysis_setting": setting,
                "effect_estimate_ref": {
                    "estimate_type": "overall",
                    "estimate_id": str(estimate["overall_estimate_id"]),
                },
                "effect_estimate": estimate,
                "included_study_ids": list(estimate.get("included_study_ids") or []),
                "study_result_rows": study_rows,
                "analysis_method": method_by_setting.get(setting_id),
                "subgroup_estimates": list(subgroup_group.get("subgroup_estimates") or []),
                "subgroup_difference_tests": list(subgroup_group.get("subgroup_difference_tests") or []),
                "analysis_identity": {
                    "official_analysis_key": ((setting.get("source") or {}).get("official_analysis_key")),
                    "analysis_key": _legacy_analysis_key(((setting.get("source") or {}).get("official_analysis_key"))),
                    "analysis_name": setting.get("analysis_name"),
                    "analysis_group_name": setting.get("analysis_group_name"),
                    "data_type": setting.get("data_type"),
                    "effect_measure": setting.get("effect_measure"),
                    "model": (method_by_setting.get(setting_id) or {}).get("analysis_model"),
                    "study_count": estimate.get("study_count"),
                    "participant_count": estimate.get("participant_count"),
                },
                "provenance": {
                    "meta_analysis_dataset": "cochrane_meta_v2",
                    "meta_analysis_workflow_root": str(raw_data_root),
                    "estimate_type": "overall",
                },
            }
        )

    for subgroup_group in subgroup_results:
        for estimate in subgroup_group.get("subgroup_estimates") or []:
            setting_id = str(estimate["setting_id"])
            setting = next(row for row in analysis_settings if str(row["setting_id"]) == setting_id)
            rows.append(
                {
                    "source_id": f"grade-row::{setting_id}",
                    "sof_row_id": f"sof-row::{setting_id}",
                    "review_id": str(setting["review_id"]),
                    "setting_id": setting_id,
                    "setting_family_id": str(setting["setting_family_id"]),
                    "candidate_id": str(setting["candidate_id"]),
                    "row_label": ((setting.get("outcome") or {}).get("label") or None),
                    "analysis_setting": setting,
                    "effect_estimate_ref": {
                        "estimate_type": "subgroup",
                        "estimate_id": str(estimate["subgroup_estimate_id"]),
                    },
                    "effect_estimate": estimate,
                    "included_study_ids": list(estimate.get("included_study_ids") or []),
                    "study_result_rows": study_rows_by_setting.get(setting_id, []),
                    "analysis_method": method_by_setting.get(setting_id),
                    "subgroup_estimates": [estimate],
                    "subgroup_difference_tests": list(subgroup_group.get("subgroup_difference_tests") or []),
                    "analysis_identity": {
                        "official_analysis_key": ((setting.get("source") or {}).get("official_analysis_key")),
                        "analysis_key": _legacy_analysis_key(((setting.get("source") or {}).get("official_analysis_key"))),
                        "analysis_name": setting.get("analysis_name"),
                        "analysis_group_name": setting.get("analysis_group_name"),
                        "data_type": setting.get("data_type"),
                        "effect_measure": setting.get("effect_measure"),
                        "model": (method_by_setting.get(setting_id) or {}).get("analysis_model"),
                        "study_count": estimate.get("study_count"),
                        "participant_count": estimate.get("participant_count"),
                    },
                    "provenance": {
                        "meta_analysis_dataset": "cochrane_meta_v2",
                        "meta_analysis_workflow_root": str(raw_data_root),
                        "estimate_type": "subgroup",
                    },
                }
            )
    return sorted(rows, key=lambda row: row["sof_row_id"])


def _filter_workflow_rows_for_grade_alignment(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for row in rows:
        setting = row.get("analysis_setting") or {}
        quality = setting.get("setting_quality") or {}
        ready = bool(quality.get("ready_for_downstream_setting_build"))
        if ready:
            kept.append(row)
            continue
        reasons = quality.get("review_reasons") or ["not_ready_for_downstream_setting_build"]
        excluded.append(
            {
                "setting_id": row.get("setting_id"),
                "setting_family_id": row.get("setting_family_id"),
                "candidate_id": row.get("candidate_id"),
                "review_id": row.get("review_id"),
                "estimate_type": (row.get("effect_estimate_ref") or {}).get("estimate_type"),
                "subgroup_source": ((setting.get("subgroup") or {}).get("source")),
                "ready_for_downstream_setting_build": ready,
                "review_reasons": reasons,
            }
        )
    reason_counts = Counter()
    estimate_type_counts = Counter()
    subgroup_source_counts = Counter()
    for row in excluded:
        reason_counts.update(row.get("review_reasons") or [])
        estimate_type_counts.update([row.get("estimate_type") or "unknown"])
        subgroup_source_counts.update([row.get("subgroup_source") or "unknown"])
    report = {
        "policy": "only setting_quality.ready_for_downstream_setting_build=true enters GRADE alignment candidates",
        "raw_workflow_row_count": len(rows),
        "kept_workflow_row_count": len(kept),
        "excluded_workflow_row_count": len(excluded),
        "excluded_reason_counts": dict(sorted(reason_counts.items())),
        "excluded_estimate_type_counts": dict(sorted(estimate_type_counts.items())),
        "excluded_subgroup_source_counts": dict(sorted(subgroup_source_counts.items())),
        "excluded_examples": excluded[:50],
    }
    return kept, report


def _load_legacy_grade_rows(*, source_dir: Path) -> list[dict[str, Any]]:
    benchmark_core_path = source_dir / "datasets" / "benchmark_core.jsonl"
    alignment_path = source_dir / "intermediate" / "08_sof_analysis_alignment.jsonl"
    if not benchmark_core_path.exists():
        raise FileNotFoundError(f"Missing legacy grade benchmark core: {benchmark_core_path}")
    if not alignment_path.exists():
        raise FileNotFoundError(f"Missing legacy grade alignment file: {alignment_path}")

    benchmark_rows = read_jsonl(benchmark_core_path)
    alignment_rows = read_jsonl(alignment_path)
    alignment_by_sample = {str(row["sample_id"]): row for row in alignment_rows}
    merged: list[dict[str, Any]] = []
    for row in benchmark_rows:
        sample_id = str(row["sample_id"])
        input_payload = row.get("input") or {}
        gold_domains = (row.get("gold") or {}).get("domains") or {}
        merged.append(
            {
                "source_sample_id": sample_id,
                "review_id": str((row.get("review") or {}).get("review_id") or ""),
                "review": row.get("review") or {},
                "sof_row_context": input_payload.get("sof_row_context") or {},
                "analysis_identity": _analysis_identity_from_legacy_input(input_payload),
                "domain_inputs": _domain_inputs_from_legacy_input(input_payload),
                "domain_golds": {domain: gold_domains.get(domain) for domain in DOMAIN_NAMES},
                "overall_certainty": (row.get("gold") or {}).get("overall_certainty"),
                "input_coverage": row.get("input_coverage") or {},
                "audit": row.get("audit") or {},
                "alignment": alignment_by_sample.get(sample_id),
                "provenance": {
                    "source_dataset": "sr_cleaned_grade_benchmark_v2",
                    "source_json": ((row.get("audit") or {}).get("source_json")),
                    "source_split": ((row.get("audit") or {}).get("split")),
                    "data_package_dir": ((row.get("audit") or {}).get("data_package_dir")),
                },
            }
        )
    return merged


def _map_rows_to_workflow(
    *,
    legacy_rows: list[dict[str, Any]],
    workflow_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    workflow_by_review_and_analysis: dict[tuple[str, str | None], list[dict[str, Any]]] = defaultdict(list)
    for row in workflow_rows:
        key = (str(row["review_id"]), str((row.get("analysis_identity") or {}).get("analysis_key") or ""))
        workflow_by_review_and_analysis[key].append(row)

    mapped_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    for legacy in legacy_rows:
        review_id = str(legacy["review_id"])
        alignment = legacy.get("alignment") or {}
        final_alignment = alignment.get("final_alignment") or {}
        matched_analysis_key = str(final_alignment.get("matched_analysis_key") or "")
        candidates = workflow_by_review_and_analysis.get((review_id, matched_analysis_key), [])
        if not matched_analysis_key:
            audit_rows.append(
                {
                    "source_sample_id": legacy["source_sample_id"],
                    "review_id": review_id,
                    "status": "no_alignment_key",
                }
            )
            continue
        if not candidates:
            audit_rows.append(
                {
                    "source_sample_id": legacy["source_sample_id"],
                    "review_id": review_id,
                    "status": "no_matching_workflow_row",
                    "matched_analysis_key": matched_analysis_key,
                }
            )
            continue
        ranked = sorted(candidates, key=lambda row: _workflow_match_score(legacy=legacy, workflow_row=row), reverse=True)
        top = ranked[0]
        top_score = _workflow_match_score(legacy=legacy, workflow_row=top)
        if len(ranked) > 1:
            second_score = _workflow_match_score(legacy=legacy, workflow_row=ranked[1])
            if abs(top_score - second_score) < 0.5:
                audit_rows.append(
                    {
                        "source_sample_id": legacy["source_sample_id"],
                        "review_id": review_id,
                        "status": "ambiguous_workflow_row_match",
                        "matched_analysis_key": matched_analysis_key,
                        "candidate_setting_ids": [row["setting_id"] for row in ranked[:3]],
                    }
                )
                continue
        mapped_rows.append(
            {
                "source_id": f"{legacy['source_sample_id']}::{top['effect_estimate_ref']['estimate_type']}",
                "source_sample_id": legacy["source_sample_id"],
                "sof_row_id": top["sof_row_id"],
                "review_id": review_id,
                "question_text": str((legacy.get("review") or {}).get("title") or ""),
                "question_pico": (legacy.get("review") or {}).get("pico") or {},
                "analysis_setting": top["analysis_setting"],
                "effect_estimate_ref": top["effect_estimate_ref"],
                "effect_estimate": top["effect_estimate"],
                "included_study_ids": list(top.get("included_study_ids") or []),
                "row_label": top.get("row_label"),
                "analysis_method": top.get("analysis_method"),
                "study_result_rows": list(top.get("study_result_rows") or []),
                "subgroup_estimates": list(top.get("subgroup_estimates") or []),
                "subgroup_difference_tests": list(top.get("subgroup_difference_tests") or []),
                "domain_inputs": legacy.get("domain_inputs") or {},
                "domain_golds": legacy.get("domain_golds") or {},
                "legacy_analysis_identity": legacy.get("analysis_identity") or {},
                "legacy_sof_row_context": legacy.get("sof_row_context") or {},
                "provenance": {
                    "legacy_source_dataset": "sr_cleaned_grade_benchmark_v2",
                    "legacy_split": ((legacy.get("provenance") or {}).get("source_split")),
                    "alignment_method": ((alignment.get("final_alignment") or {}).get("status")),
                    "alignment_confidence": ((alignment.get("final_alignment") or {}).get("alignment_confidence")),
                    "matched_analysis_key": matched_analysis_key,
                    "workflow_setting_id": top["setting_id"],
                    "workflow_estimate_id": top["effect_estimate_ref"]["estimate_id"],
                },
            }
        )
    return mapped_rows, audit_rows


def _records_from_mapped_rows(mapped_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in mapped_rows:
        for domain in DOMAIN_NAMES:
            gold = (row.get("domain_golds") or {}).get(domain)
            if not gold:
                continue
            instance_id = f"{row['sof_row_id']}::{domain}"
            instance = {
                "instance_id": instance_id,
                "sof_row_id": row["sof_row_id"],
                "review_id": row["review_id"],
                "domain": domain,
                "question_text": row["question_text"],
                "question_pico": row["question_pico"],
                "analysis_setting": row["analysis_setting"],
                "effect_estimate_ref": row["effect_estimate_ref"],
                "included_study_ids": row["included_study_ids"],
                "domain_evidence": _domain_evidence(domain=domain, mapped_row=row),
                "source_context": {
                    "legacy_sof_row_context": row.get("legacy_sof_row_context") or {},
                    "legacy_analysis_identity": row.get("legacy_analysis_identity") or {},
                },
                "provenance": row["provenance"],
            }
            shared_row = {
                "sof_row_id": row["sof_row_id"],
                "source_sample_id": row["source_sample_id"],
                "review_id": row["review_id"],
                "question_text": row["question_text"],
                "question_pico": row["question_pico"],
                "row_label": row.get("row_label"),
                "analysis_setting": row["analysis_setting"],
                "effect_estimate_ref": row["effect_estimate_ref"],
                "included_study_ids": row["included_study_ids"],
                "provenance": row["provenance"],
            }
            records.append(
                {
                    "source_id": f"{row['source_id']}::{domain}",
                    "sof_row_id": row["sof_row_id"],
                    "review_id": row["review_id"],
                    "domain": domain,
                    "shared_row": shared_row,
                    "instance": instance,
                    "gold": {
                        "instance_id": instance_id,
                        "sof_row_id": row["sof_row_id"],
                        "domain": domain,
                        "judgement": {
                            "domain": domain,
                            "downgraded": gold.get("downgraded"),
                            "severity": gold.get("severity"),
                            "levels": gold.get("levels"),
                            "level_evaluable": gold.get("level_evaluable"),
                            "rationale": gold.get("rationale"),
                            "source_spans": list(gold.get("source_spans") or []),
                            "evidence_status": gold.get("evidence_status"),
                        },
                    },
                }
            )
    return sorted(records, key=lambda record: record["source_id"])


def _domain_evidence(*, domain: str, mapped_row: dict[str, Any]) -> dict[str, Any]:
    inputs = mapped_row.get("domain_inputs") or {}
    if domain == "risk_of_bias":
        return inputs.get("risk_of_bias") or {}
    if domain == "inconsistency":
        evidence = dict(inputs.get("inconsistency") or {})
        evidence.setdefault("effect_estimate", mapped_row.get("effect_estimate"))
        evidence.setdefault("analysis_method", mapped_row.get("analysis_method"))
        evidence.setdefault("subgroup_estimates", mapped_row.get("subgroup_estimates") or [])
        evidence.setdefault("subgroup_difference_tests", mapped_row.get("subgroup_difference_tests") or [])
        evidence.setdefault("study_result_rows", mapped_row.get("study_result_rows") or [])
        return evidence
    if domain == "indirectness":
        evidence = dict(inputs.get("indirectness") or {})
        evidence.setdefault("question_pico", mapped_row.get("question_pico") or {})
        return evidence
    if domain == "imprecision":
        evidence = dict(inputs.get("imprecision") or {})
        evidence.setdefault("effect_estimate", mapped_row.get("effect_estimate"))
        evidence.setdefault("analysis_method", mapped_row.get("analysis_method"))
        evidence.setdefault("study_result_rows", mapped_row.get("study_result_rows") or [])
        evidence.setdefault("study_count", (mapped_row.get("effect_estimate") or {}).get("study_count"))
        evidence.setdefault("participant_count", (mapped_row.get("effect_estimate") or {}).get("participant_count"))
        return evidence
    raise ValueError(f"Unsupported domain: {domain}")


def _analysis_identity_from_legacy_input(input_payload: dict[str, Any]) -> dict[str, Any]:
    meta_analysis = input_payload.get("meta_analysis") or {}
    return {
        "analysis_key": meta_analysis.get("analysis_key"),
        "analysis_name": meta_analysis.get("analysis_name"),
        "analysis_group_name": meta_analysis.get("analysis_group_name"),
        "data_type": meta_analysis.get("data_type"),
        "effect_measure": meta_analysis.get("effect_measure"),
        "model": meta_analysis.get("model"),
        "study_count": meta_analysis.get("study_count_from_rows"),
        "participant_count": meta_analysis.get("participant_count_from_rows"),
    }


def _domain_inputs_from_legacy_input(input_payload: dict[str, Any]) -> dict[str, Any]:
    sof_context = input_payload.get("sof_row_context") or {}
    meta_analysis = input_payload.get("meta_analysis") or {}
    shared_membership = input_payload.get("analysis_study_membership") or []
    return {
        "risk_of_bias": {
            "analysis_study_membership": shared_membership,
            "risk_of_bias_all": input_payload.get("risk_of_bias") or [],
            "risk_of_bias_aligned": input_payload.get("risk_of_bias") or [],
        },
        "inconsistency": {
            "effect_estimate": {
                "effect": meta_analysis.get("pooled_effect"),
                "ci_lower": meta_analysis.get("ci_lower"),
                "ci_upper": meta_analysis.get("ci_upper"),
            },
            "heterogeneity": {
                "i2": meta_analysis.get("heterogeneity_i2"),
                "p": meta_analysis.get("heterogeneity_p"),
            },
            "model": meta_analysis.get("model"),
            "study_effect_rows": input_payload.get("study_effect_rows") or [],
            "subgroup_summaries": meta_analysis.get("subgroup_summaries") or [],
        },
        "indirectness": {
            "target_pico": {
                "review_population": ((input_payload.get("review") or {}).get("pico") or {}).get("population"),
                "review_intervention": ((input_payload.get("review") or {}).get("pico") or {}).get("intervention"),
                "review_comparison": ((input_payload.get("review") or {}).get("pico") or {}).get("comparison"),
                "review_outcome": ((input_payload.get("review") or {}).get("pico") or {}).get("outcome"),
                "sof_population": sof_context.get("population"),
                "sof_intervention": sof_context.get("intervention"),
                "sof_comparison": sof_context.get("comparison"),
                "sof_outcome": sof_context.get("outcome_name"),
                "sof_follow_up": sof_context.get("follow_up"),
                "sof_setting": sof_context.get("setting"),
            },
            "analysis_study_membership": shared_membership,
            "study_characteristics_all": input_payload.get("included_studies") or [],
            "study_characteristics_aligned": input_payload.get("included_studies") or [],
        },
        "imprecision": {
            "data_type": meta_analysis.get("data_type"),
            "effect_measure": meta_analysis.get("effect_measure"),
            "effect_estimate": {
                "effect": meta_analysis.get("pooled_effect"),
                "ci_lower": meta_analysis.get("ci_lower"),
                "ci_upper": meta_analysis.get("ci_upper"),
            },
            "events_and_n": {
                "experimental_cases": meta_analysis.get("experimental_cases"),
                "experimental_n": meta_analysis.get("experimental_n"),
                "control_cases": meta_analysis.get("control_cases"),
                "control_n": meta_analysis.get("control_n"),
            },
            "study_count": meta_analysis.get("study_count_from_rows"),
            "participant_count": meta_analysis.get("participant_count_from_rows"),
            "study_effect_rows": input_payload.get("study_effect_rows") or [],
            "statistical_method": meta_analysis.get("statistical_method"),
            "model": meta_analysis.get("model"),
            "log_scale_data": meta_analysis.get("log_scale_data"),
            "unit_of_effect_measure": meta_analysis.get("unit_of_effect_measure"),
        },
    }


def _workflow_match_score(*, legacy: dict[str, Any], workflow_row: dict[str, Any]) -> float:
    score = 0.0
    legacy_ai = legacy.get("analysis_identity") or {}
    workflow_ai = workflow_row.get("analysis_identity") or {}
    if _norm(legacy_ai.get("analysis_name")) == _norm(workflow_ai.get("analysis_name")):
        score += 4.0
    if _norm(legacy_ai.get("analysis_group_name")) == _norm(workflow_ai.get("analysis_group_name")):
        score += 4.0
    if _norm(legacy_ai.get("data_type")) == _norm(workflow_ai.get("data_type")):
        score += 1.5
    if _norm(legacy_ai.get("effect_measure")) == _norm(workflow_ai.get("effect_measure")):
        score += 1.5
    if _norm(legacy_ai.get("analysis_key")) == _norm(workflow_ai.get("analysis_key")):
        score += 6.0
    legacy_study_count = legacy_ai.get("study_count")
    workflow_study_count = workflow_ai.get("study_count")
    if legacy_study_count is not None and workflow_study_count is not None:
        score -= abs(float(legacy_study_count) - float(workflow_study_count)) * 0.2
    legacy_participants = legacy_ai.get("participant_count")
    workflow_participants = workflow_ai.get("participant_count")
    if legacy_participants is not None and workflow_participants is not None:
        score -= abs(float(legacy_participants) - float(workflow_participants)) / 200.0
    legacy_follow_up = _norm((legacy.get("sof_row_context") or {}).get("follow_up"))
    workflow_timepoint = _norm((((workflow_row.get("analysis_setting") or {}).get("timepoint") or {}).get("label")))
    if legacy_follow_up and workflow_timepoint and legacy_follow_up == workflow_timepoint:
        score += 1.0
    subgroup_level = _norm(((((workflow_row.get("analysis_setting") or {}).get("subgroup") or {}).get("level"))))
    if not subgroup_level:
        score += 0.25
    return score


def _legacy_analysis_key(official_analysis_key: str | None) -> str | None:
    if not official_analysis_key:
        return None
    parts = str(official_analysis_key).split("::")
    if len(parts) != 3:
        return None
    return f"{parts[1]}.{parts[2]}"


def _raw_quality_report(
    *,
    workflow_rows: list[dict[str, Any]],
    legacy_rows: list[dict[str, Any]],
    mapped_rows: list[dict[str, Any]],
    audit_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    dropped_by_reason = Counter(str(row.get("status") or "unknown") for row in audit_rows)
    domain_counts = Counter()
    for row in mapped_rows:
        for domain, gold in (row.get("domain_golds") or {}).items():
            if gold:
                domain_counts[domain] += 1
    return {
        "workflow_row_universe_count": len(workflow_rows),
        "legacy_row_count": len(legacy_rows),
        "matched_row_count": len(mapped_rows),
        "dropped_row_count": len(audit_rows),
        "shared_row_count": len(mapped_rows),
        "dropped_row_count_by_reason": dict(dropped_by_reason),
        "domain_counts": dict(domain_counts),
    }


def _load_sof_rows_for_alignment(*, raw_root: Path) -> list[dict[str, Any]]:
    path = raw_root / "source" / "legacy_grade_benchmark_v2" / "intermediate" / "04_sof_rows_cleaned.jsonl"
    if not path.exists():
        source_path = UPSTREAM_GRADE_ROOT / "intermediate" / "04_sof_rows_cleaned.jsonl"
        if not source_path.exists():
            raise FileNotFoundError(f"Missing SoF cleaned row source: {source_path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, path)
    return read_jsonl(path)


def _load_sof_gold_by_sample(*, raw_root: Path) -> dict[str, dict[str, Any]]:
    path = raw_root / "source" / "legacy_grade_benchmark_v2" / "intermediate" / "05_sof_gold_domains.jsonl"
    if not path.exists():
        source_path = UPSTREAM_GRADE_ROOT / "intermediate" / "05_sof_gold_domains.jsonl"
        if not source_path.exists():
            raise FileNotFoundError(f"Missing SoF gold source: {source_path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, path)
    rows = read_jsonl(path)
    return {str(row["sample_id"]): row for row in rows}


def _all_gold_review_ids_for_alignment(*, raw_root: Path) -> list[str]:
    gold_by_sample = _load_sof_gold_by_sample(raw_root=raw_root)
    return sorted(
        {
            str(row.get("review_id"))
            for row in gold_by_sample.values()
            if row.get("review_id") and any(((row.get("gold") or {}).get("domains") or {}).get(domain) for domain in DOMAIN_NAMES)
        }
    )


def _alignment_input_from_sof_row(row: dict[str, Any], *, gold_by_sample: dict[str, dict[str, Any]]) -> dict[str, Any]:
    sample_id = str(row["sample_id"])
    gold_row = gold_by_sample.get(sample_id) or {}
    gold_domains = ((gold_row.get("gold") or {}).get("domains") or {})
    return {
        "sample_id": sample_id,
        "review_id": str(row["review_id"]),
        "review_title": row.get("review_title"),
        "question_pico": row.get("pico") or {},
        "sof_table_id": str(row.get("sof_table_id") or ""),
        "table_title": row.get("table_title") or "",
        "row_order": row.get("row_order"),
        "outcome_name": row.get("outcome_name") or "",
        "timepoint_text": row.get("timepoint_text") or "",
        "relative_effect_text": row.get("relative_effect_text") or "",
        "participants_text": row.get("participants_text") or "",
        "studies_text": row.get("studies_text") or "",
        "population_text": row.get("population_text") or "",
        "setting_text": row.get("setting_text") or "",
        "intervention_text": row.get("intervention_text") or "",
        "comparison_text": row.get("comparison_text") or "",
        "comment_text": row.get("comment_text") or "",
        "footnote_texts": list(row.get("footnote_texts") or []),
        "source_summary_of_findings_span_text": row.get("source_summary_of_findings_span_text") or "",
        "gold_available": any(gold_domains.get(domain) for domain in DOMAIN_NAMES),
    }


def _alignment_tables_from_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["review_id"], row["sof_table_id"])].append(row)
    tables: list[dict[str, Any]] = []
    for (review_id, table_id), table_rows in grouped.items():
        first = sorted(table_rows, key=lambda row: int(row.get("row_order") or 0))[0]
        tables.append(
            {
                "review_id": review_id,
                "sof_table_id": table_id,
                "review_title": first.get("review_title") or "",
                "table_title": first.get("table_title") or "",
                "population_text": first.get("population_text") or "",
                "setting_text": first.get("setting_text") or "",
                "intervention_text": first.get("intervention_text") or "",
                "comparison_text": first.get("comparison_text") or "",
                "row_outcomes": [
                    {
                        "sample_id": row["sample_id"],
                        "row_order": row.get("row_order"),
                        "outcome_name": row.get("outcome_name") or "",
                        "timepoint_text": row.get("timepoint_text") or "",
                        "relative_effect_text": row.get("relative_effect_text") or "",
                        "participants_text": row.get("participants_text") or "",
                        "studies_text": row.get("studies_text") or "",
                    }
                    for row in sorted(table_rows, key=lambda item: int(item.get("row_order") or 0))
                ],
            }
        )
    return sorted(tables, key=lambda table: (table["review_id"], table["sof_table_id"]))


def _workflow_groups_by_review(workflow_rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    groups: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in workflow_rows:
        setting = row.get("analysis_setting") or {}
        review_id = str(row["review_id"])
        analysis_group = str(setting.get("analysis_group") or "")
        if not analysis_group:
            continue
        group = groups[review_id].setdefault(
            analysis_group,
            {
                "review_id": review_id,
                "analysis_group": analysis_group,
                "analysis_group_name": setting.get("analysis_group_name") or "",
                "analysis_names": [],
                "available_subgroups": [],
                "rows": [],
            },
        )
        analysis_name = setting.get("analysis_name")
        if analysis_name and analysis_name not in group["analysis_names"]:
            group["analysis_names"].append(analysis_name)
        subgroup = (setting.get("subgroup") or {}).get("level")
        if subgroup and subgroup not in group["available_subgroups"]:
            group["available_subgroups"].append(subgroup)
        group["rows"].append(_candidate_row_summary(row))
    for review_groups in groups.values():
        for group in review_groups.values():
            group["analysis_names"] = sorted(group["analysis_names"])
            group["available_subgroups"] = sorted(group["available_subgroups"])
            group["rows"] = sorted(group["rows"], key=lambda item: item["setting_id"])
    return groups


def _candidate_row_summary(row: dict[str, Any]) -> dict[str, Any]:
    setting = row.get("analysis_setting") or {}
    estimate = row.get("effect_estimate") or {}
    return {
        "setting_id": row["setting_id"],
        "setting_family_id": row["setting_family_id"],
        "analysis_group": setting.get("analysis_group"),
        "analysis_number": setting.get("analysis_number"),
        "analysis_group_name": setting.get("analysis_group_name"),
        "analysis_name": setting.get("analysis_name"),
        "outcome": setting.get("outcome") or {},
        "timepoint": setting.get("timepoint") or {},
        "subgroup": setting.get("subgroup") or {},
        "subgroup_scope": setting.get("subgroup_scope") or {},
        "comparison": setting.get("comparison") or {},
        "comparison_structure": setting.get("comparison_structure") or {},
        "setting_quality": setting.get("setting_quality") or {},
        "effect_estimate_ref": row.get("effect_estimate_ref") or {},
        "effect_measure": estimate.get("effect_measure") or setting.get("effect_measure"),
        "effect_value": estimate.get("effect_value"),
        "ci_lower": estimate.get("ci_lower"),
        "ci_upper": estimate.get("ci_upper"),
        "study_count": estimate.get("study_count"),
        "participant_count": estimate.get("participant_count"),
    }


def _candidate_family_records(
    settings_by_review: dict[str, dict[str, dict[str, Any]]],
    requested_reviews: set[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for review_id in sorted(requested_reviews & set(settings_by_review)):
        for group in sorted(settings_by_review[review_id].values(), key=lambda item: item["analysis_group"]):
            rows.append(
                {
                    "review_id": review_id,
                    "analysis_group": group["analysis_group"],
                    "analysis_group_name": group["analysis_group_name"],
                    "analysis_names": group["analysis_names"],
                    "available_subgroups": group["available_subgroups"],
                    "setting_count": len(group["rows"]),
                }
            )
    return rows


def _table_family_tasks(
    *,
    tables: list[dict[str, Any]],
    settings_by_review: dict[str, dict[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for table in tables:
        for family in settings_by_review.get(table["review_id"], {}).values():
            payload = {
                "sof_table": {
                    "review_title": table.get("review_title"),
                    "table_title": table.get("table_title"),
                    "population_text": table.get("population_text"),
                    "setting_text": table.get("setting_text"),
                    "intervention_text": table.get("intervention_text"),
                    "comparison_text": table.get("comparison_text"),
                    "row_outcomes": table.get("row_outcomes") or [],
                },
                "candidate_family": {
                    "analysis_group": family["analysis_group"],
                    "analysis_group_name": family["analysis_group_name"],
                    "analysis_names": family["analysis_names"],
                    "available_subgroups": family["available_subgroups"],
                },
            }
            task_id = f"table-family::{table['review_id']}::{table['sof_table_id']}::{family['analysis_group']}"
            tasks.append(
                {
                    "task_id": task_id,
                    "task_type": "table_family",
                    "review_id": table["review_id"],
                    "sof_table_id": table["sof_table_id"],
                    "analysis_group": family["analysis_group"],
                    "analysis_group_name": family["analysis_group_name"],
                    "payload": payload,
                }
            )
    return sorted(tasks, key=lambda task: task["task_id"])


def _row_setting_tasks(
    *,
    alignment_inputs: list[dict[str, Any]],
    settings_by_review: dict[str, dict[str, dict[str, Any]]],
    matched_family_keys: set[tuple[str, str, str]],
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for sof_row in alignment_inputs:
        matched_groups = [
            analysis_group
            for (review_id, table_id, analysis_group) in matched_family_keys
            if review_id == sof_row["review_id"] and table_id == sof_row["sof_table_id"]
        ]
        raw_candidates: dict[str, dict[str, Any]] = {}
        for analysis_group in sorted(set(matched_groups)):
            family = settings_by_review.get(sof_row["review_id"], {}).get(analysis_group)
            if not family:
                continue
            for candidate in family["rows"]:
                raw_candidates[str(candidate["setting_id"])] = candidate
        selected_candidates, selection = _select_row_setting_candidates_by_numeric_evidence(
            sof_row=sof_row,
            candidates=sorted(raw_candidates.values(), key=lambda item: item["setting_id"]),
        )
        for candidate in selected_candidates:
            payload = {
                "sof_row": {
                    "table_title": sof_row.get("table_title"),
                    "outcome_name": sof_row.get("outcome_name"),
                    "timepoint_text": sof_row.get("timepoint_text"),
                    "relative_effect_text": sof_row.get("relative_effect_text"),
                    "participants_text": sof_row.get("participants_text"),
                    "studies_text": sof_row.get("studies_text"),
                    "population_text": sof_row.get("population_text"),
                    "setting_text": sof_row.get("setting_text"),
                    "intervention_text": sof_row.get("intervention_text"),
                    "comparison_text": sof_row.get("comparison_text"),
                    "comment_text": sof_row.get("comment_text"),
                    "footnote_texts": sof_row.get("footnote_texts") or [],
                },
                "candidate_setting": candidate,
            }
            task_id = f"row-setting::{sof_row['sample_id']}::{candidate['setting_id']}"
            candidate_selection = {
                **selection,
                "candidate_match_flags": selection.get("match_flags_by_setting_id", {}).get(str(candidate["setting_id"]), {}),
            }
            candidate_selection.pop("match_flags_by_setting_id", None)
            tasks.append(
                {
                    "task_id": task_id,
                    "task_type": "row_setting",
                    "sample_id": sof_row["sample_id"],
                    "review_id": sof_row["review_id"],
                    "sof_table_id": sof_row["sof_table_id"],
                    "setting_id": candidate["setting_id"],
                    "analysis_group": str(candidate.get("analysis_group") or ""),
                    "candidate_selection": candidate_selection,
                    "payload": payload,
                }
            )
    return sorted(tasks, key=lambda task: task["task_id"])


def _select_row_setting_candidates_by_numeric_evidence(
    *,
    sof_row: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not candidates:
        return [], {
            "mode": "no_table_family_candidates",
            "raw_candidate_count": 0,
            "selected_candidate_count": 0,
            "numeric_fields": {},
            "numeric_tolerance": _numeric_tolerance_config(),
            "match_flags_by_setting_id": {},
        }

    participant_study_pair = (
        _parse_sof_participant_study_pair(
            f"{sof_row.get('participants_text') or ''} {sof_row.get('studies_text') or ''}"
        )
        or _parse_sof_participant_study_pair(sof_row.get("source_summary_of_findings_span_text"))
        or {}
    )
    sof_numbers = {
        "effect_ci": _parse_sof_effect_ci(sof_row.get("relative_effect_text")),
        "study_count": _parse_sof_study_count(
            f"{sof_row.get('studies_text') or ''} {sof_row.get('participants_text') or ''}"
        )
        or participant_study_pair.get("study_count"),
        "participant_count": _parse_sof_participant_count(sof_row.get("participants_text"))
        or participant_study_pair.get("participant_count"),
    }
    effect_matches: dict[str, dict[str, Any]] = {}
    study_participant_matches: dict[str, dict[str, Any]] = {}
    match_flags_by_setting_id: dict[str, dict[str, bool]] = {}
    for candidate in candidates:
        setting_id = str(candidate["setting_id"])
        estimate = candidate.get("effect_estimate") or candidate
        effect_match = _effect_ci_close(
            sof_numbers.get("effect_ci"),
            (
                estimate.get("effect_value"),
                estimate.get("ci_lower"),
                estimate.get("ci_upper"),
            ),
        )
        study_match = _study_count_equal(sof_numbers.get("study_count"), estimate.get("study_count"))
        participant_match = _participant_count_close(
            sof_numbers.get("participant_count"),
            estimate.get("participant_count"),
        )
        study_participant_match = study_match and participant_match
        match_flags_by_setting_id[setting_id] = {
            "effect_ci_match": effect_match,
            "study_count_match": study_match,
            "participant_count_match": participant_match,
            "study_participant_match": study_participant_match,
        }
        if effect_match:
            effect_matches[setting_id] = candidate
        if study_participant_match:
            study_participant_matches[setting_id] = candidate

    selected_by_id = {**study_participant_matches, **effect_matches}
    if selected_by_id:
        mode = "numeric_match"
        selected = sorted(selected_by_id.values(), key=lambda item: item["setting_id"])
    else:
        selected = candidates
        mode = (
            "numeric_no_match_fallback"
            if any(value is not None for value in sof_numbers.values())
            else "numeric_unavailable_fallback"
        )
    selection = {
        "mode": mode,
        "raw_candidate_count": len(candidates),
        "selected_candidate_count": len(selected),
        "effect_ci_match_count": len(effect_matches),
        "study_participant_match_count": len(study_participant_matches),
        "numeric_fields": sof_numbers,
        "numeric_tolerance": _numeric_tolerance_config(),
        "match_flags_by_setting_id": match_flags_by_setting_id,
    }
    return selected, selection


def _numeric_tolerance_config() -> dict[str, Any]:
    return {
        "effect_ci_relative_tolerance": 0.02,
        "effect_ci_min_absolute_tolerance": 0.01,
        "effect_ci_match_policy": "signed_pairwise_or_absolute_pairwise_or_absolute_multiset",
        "participant_relative_tolerance": 0.01,
        "participant_min_absolute_tolerance": 1,
        "study_count": "exact",
    }


def _parse_sof_effect_ci(text: Any) -> tuple[float, float, float] | None:
    normalized = _normalize_sof_numeric_text(text)
    prefix, _, suffix = normalized.partition("(")
    effect_values = _directional_numbers_from_sof_text(prefix)
    ci_segment = suffix.rsplit(")", 1)[0] if suffix else ""
    ci_values = _directional_numbers_from_sof_text(ci_segment)
    if effect_values and len(ci_values) >= 2:
        return effect_values[0], ci_values[-2], ci_values[-1]
    values = _directional_numbers_from_sof_text(normalized)
    if len(values) < 3:
        return None
    return values[0], values[1], values[2]


def _parse_sof_study_count(text: Any) -> int | None:
    normalized = _normalize_sof_numeric_text(text).lower()
    match = re.search(r"(\d+)\s*(?:rcts?|stud(?:y|ies)|trials?)", normalized)
    return int(match.group(1)) if match else None


def _parse_sof_participant_count(text: Any) -> int | None:
    normalized = _normalize_sof_numeric_text(text).lower()
    match = re.search(
        r"(\d+(?:,\d{3})*)\s*(?:participants|people|patients|women|children|adults|infants|pregnan)",
        normalized,
    )
    if match:
        return int(match.group(1).replace(",", ""))
    values = _numbers_from_sof_text(text)
    return int(values[0]) if values else None


def _parse_sof_participant_study_pair(text: Any) -> dict[str, int] | None:
    normalized = _normalize_sof_numeric_text(text)
    matches = []
    for match in re.finditer(r"(\d+(?:,\d{3})*)\s*\(\s*(\d+)\s*\)", normalized):
        participant_count = int(match.group(1).replace(",", ""))
        study_count = int(match.group(2))
        if participant_count <= 0 or study_count <= 0 or study_count > participant_count:
            continue
        matches.append({"participant_count": participant_count, "study_count": study_count})
    if not matches:
        return None
    return matches[-1]


def _directional_numbers_from_sof_text(text: Any) -> list[float]:
    normalized = _normalize_sof_numeric_text(text)
    values: list[float] = []
    pattern = re.compile(
        r"(?<![A-Za-z])(-?\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:%|\b)?\s*"
        r"(higher|lower|more|less|fewer|greater|smaller)?",
        flags=re.IGNORECASE,
    )
    for match in pattern.finditer(normalized):
        raw_value = float(match.group(1).replace(",", ""))
        direction = (match.group(2) or "").lower()
        if direction in {"lower", "less", "fewer", "smaller"}:
            values.append(-abs(raw_value))
        elif direction in {"higher", "more", "greater"}:
            values.append(abs(raw_value))
        else:
            values.append(raw_value)
    return values


def _numbers_from_sof_text(text: Any) -> list[float]:
    normalized = _normalize_sof_numeric_text(text)
    return [
        float(value.replace(",", ""))
        for value in re.findall(r"(?<![A-Za-z])-?\d+(?:,\d{3})*(?:\.\d+)?", normalized)
    ]


def _normalize_sof_numeric_text(text: Any) -> str:
    return (
        str(text or "")
        .replace("−", "-")
        .replace("–", "-")
        .replace("—", "-")
        .replace("\u2010", "-")
    )


def _effect_ci_close(
    sof_effect_ci: tuple[float, float, float] | None,
    candidate_effect_ci: tuple[Any, Any, Any],
) -> bool:
    if sof_effect_ci is None or any(value is None for value in candidate_effect_ci):
        return False
    sof_values = [float(value) for value in sof_effect_ci]
    candidate_values = [float(value) for value in candidate_effect_ci]
    if all(_numeric_close(sof, candidate) for sof, candidate in zip(sof_values, candidate_values)):
        return True
    if all(_numeric_close(abs(sof), abs(candidate)) for sof, candidate in zip(sof_values, candidate_values)):
        return True
    return _numeric_multiset_close([abs(value) for value in sof_values], [abs(value) for value in candidate_values])


def _numeric_close(a: float, b: float, *, relative_tolerance: float = 0.02, min_absolute_tolerance: float = 0.01) -> bool:
    return abs(a - b) <= max(min_absolute_tolerance, abs(a) * relative_tolerance, abs(b) * relative_tolerance)


def _numeric_multiset_close(left: list[float], right: list[float]) -> bool:
    if len(left) != len(right):
        return False
    unmatched = list(right)
    for left_value in sorted(left):
        match_index = next(
            (
                index
                for index, right_value in enumerate(unmatched)
                if _numeric_close(left_value, right_value)
            ),
            None,
        )
        if match_index is None:
            return False
        unmatched.pop(match_index)
    return True


def _study_count_equal(sof_count: int | None, candidate_count: Any) -> bool:
    if sof_count is None or candidate_count is None:
        return False
    try:
        return int(sof_count) == int(candidate_count)
    except (TypeError, ValueError):
        return False


def _participant_count_close(sof_count: int | None, candidate_count: Any) -> bool:
    if sof_count is None or candidate_count is None:
        return False
    try:
        sof_value = int(sof_count)
        candidate_value = int(candidate_count)
    except (TypeError, ValueError):
        return False
    tolerance = max(1, round(max(abs(sof_value), abs(candidate_value)) * 0.01))
    return abs(sof_value - candidate_value) <= tolerance


def _run_llm_tasks(
    *,
    tasks: list[dict[str, Any]],
    task_type: str,
    api_key: str,
    base_url: str,
    api_mode: str,
    model: str,
    workers: int,
    timeout: int,
    retries: int,
    output_path: Path,
) -> list[dict[str, Any]]:
    if not tasks:
        return []
    results: list[dict[str, Any]] = []
    total_count = len(tasks)
    completed_count = 0
    success_count = 0
    failed_count = 0

    def print_progress(*, force_newline: bool = False) -> None:
        remaining = total_count - completed_count
        message = (
            f"[grade-alignment:{task_type}] {completed_count}/{total_count} done "
            f"success={success_count} failed={failed_count} remaining={remaining}"
        )
        end = "\n" if force_newline or completed_count == total_count else "\r"
        print(message, end=end, flush=True)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        future_map = {
            executor.submit(
                _run_one_llm_task,
                task=task,
                task_type=task_type,
                api_key=api_key,
                base_url=base_url,
                api_mode=api_mode,
                model=model,
                timeout=timeout,
                retries=retries,
            ): task
            for task in tasks
        }
        print_progress()
        for future in as_completed(future_map):
            task = future_map[future]
            try:
                result = future.result()
            except Exception as exc:  # pragma: no cover - depends on live LLM/network
                result = _normalize_llm_prediction(
                    task=task,
                    parsed={
                        "match": False,
                        "confidence": "low",
                        "reason": f"worker_failed:{type(exc).__name__}: {exc}",
                    },
                    status=f"worker_failed:{type(exc).__name__}",
                    raw_text="",
                )
            if result.get("llm_status") == "ok":
                success_count += 1
            else:
                failed_count += 1
            append_jsonl(output_path, [result], sort_keys=False)
            results.append(result)
            completed_count += 1
            print_progress(force_newline=result.get("llm_status") != "ok")
    return sorted(results, key=lambda row: row["task_id"])


def _run_one_llm_task(
    *,
    task: dict[str, Any],
    task_type: str,
    api_key: str,
    base_url: str,
    api_mode: str,
    model: str,
    timeout: int,
    retries: int,
) -> dict[str, Any]:
    if task_type == "table_family":
        system = (
            "You align Cochrane Summary of Findings tables to data-package analysis groups. "
            "Decide whether the candidate analysis group belongs to the SoF table. "
            "Return strict JSON only."
        )
        schema = {
            "match": True,
            "confidence": "high|medium|low",
            "relationship": "same_comparison|related_comparison|outcome_group_under_table|population_only|not_related|unclear",
            "reason": "short explanation",
        }
        instructions = (
            "A table-family match can be true when the comparison and table scope are the same even if wording differs. "
            "Use the table title, intervention, comparison, population, available subgroups, and row outcomes. "
            "Do not mark a different active comparator as match=true."
        )
    elif task_type == "row_setting":
        system = (
            "You align a Cochrane Summary of Findings outcome row to a current workflow meta-analysis setting row. "
            "Decide whether they represent the same evidence row. Return strict JSON only."
        )
        schema = {
            "match": True,
            "confidence": "high|medium|low",
            "basis": {
                "outcome": "same|compatible|different|unclear",
                "timepoint": "same|compatible|different|not_applicable",
                "subgroup": "same|compatible|different|not_applicable",
                "numeric": "same|compatible|different|not_reported",
            },
            "reason": "short explanation",
        }
        instructions = (
            "A row-setting match must represent the same evidence row, not just a related analysis. "
            "Require the outcome to be the same or clearly compatible, the timepoint to be the same or clearly compatible, "
            "and the numeric estimate/study count/participant count to be the same or clearly compatible when reported. "
            "If the SoF row is an overall row with no explicit subgroup, a subgroup candidate is not the same evidence row. "
            "If the candidate is a sensitivity analysis, subgroup, different follow-up, different analysis number, or different numeric evidence, set match=false. "
            "When basis.outcome, basis.timepoint, basis.subgroup, or basis.numeric is different, match must be false."
        )
    else:
        raise ValueError(f"Unsupported LLM alignment task type: {task_type}")
    prompt = (
        "Use only the supplied JSON payload. Do not invent IDs or external facts. "
        f"{instructions} "
        "If uncertain, set match=false or confidence=low. "
        f"Required output schema:\n{json.dumps(schema, ensure_ascii=False)}\n\n"
        f"Payload:\n{json.dumps(task['payload'], ensure_ascii=False, indent=2)}"
    )
    parsed, status, raw_text = _call_llm_json(
        api_key=api_key,
        base_url=base_url,
        api_mode=api_mode,
        model=model,
        system=system,
        prompt=prompt,
        timeout=timeout,
        retries=retries,
    )
    normalized = _normalize_llm_prediction(task=task, parsed=parsed, status=status, raw_text=raw_text)
    normalized["model"] = model
    return normalized


def _call_llm_json(
    *,
    api_key: str,
    base_url: str,
    api_mode: str,
    model: str,
    system: str,
    prompt: str,
    timeout: int,
    retries: int,
) -> tuple[dict[str, Any] | None, str, str]:
    normalized_mode = api_mode.strip().lower()
    if normalized_mode == "responses":
        payload = {
            "model": model,
            "instructions": system,
            "input": prompt,
            "temperature": 0,
        }
        endpoint = "/responses"
    elif normalized_mode == "chat":
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "temperature": 0,
        }
        endpoint = "/chat/completions"
    else:
        raise ValueError(f"Unsupported api_mode: {api_mode}")
    request = urllib.request.Request(
        base_url.rstrip("/") + endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    last_error = ""
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=ssl_context()) as response:
                data = json.loads(response.read().decode("utf-8"))
            content = _llm_response_text(data, api_mode=normalized_mode)
            parsed = _extract_json_object(content)
            if parsed is None:
                return None, "invalid_json", content
            return parsed, "ok", content
        except (TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            if attempt < retries:
                time.sleep(min(2**attempt, 8))
    return None, f"request_failed:{last_error}", ""


def _llm_response_text(data: dict[str, Any], *, api_mode: str) -> str:
    if api_mode == "chat":
        return str(data.get("choices", [{}])[0].get("message", {}).get("content", ""))
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text:
        return output_text
    chunks: list[str] = []
    for item in data.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if isinstance(content, dict):
                text = content.get("text")
                if isinstance(text, str):
                    chunks.append(text)
    return "\n".join(chunks)


def _extract_json_object(text: str) -> dict[str, Any] | None:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        value = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _normalize_llm_prediction(
    *,
    task: dict[str, Any],
    parsed: dict[str, Any] | None,
    status: str,
    raw_text: str,
) -> dict[str, Any]:
    parsed = parsed if isinstance(parsed, dict) else {}
    confidence = str(parsed.get("confidence") or "low").lower()
    if confidence not in {"high", "medium", "low"}:
        confidence = "low"
    result = {
        "task_id": task["task_id"],
        "task_type": task["task_type"],
        **_task_cache_metadata(task),
        "review_id": task["review_id"],
        "sof_table_id": task.get("sof_table_id"),
        "match": _coerce_bool(parsed.get("match")) if status == "ok" else False,
        "confidence": confidence,
        "reason": str(parsed.get("reason") or ""),
        "llm_status": status,
        "llm_raw": parsed,
    }
    if raw_text:
        result["raw_text"] = raw_text
    if task["task_type"] == "table_family":
        result.update(
            {
                "analysis_group": task["analysis_group"],
                "analysis_group_name": task["analysis_group_name"],
                "relationship": str(parsed.get("relationship") or "unclear"),
            }
        )
    if task["task_type"] == "row_setting":
        basis = parsed.get("basis") if isinstance(parsed.get("basis"), dict) else {}
        if any(str(basis.get(key) or "").lower() == "different" for key in ("outcome", "timepoint", "subgroup", "numeric")):
            result["match"] = False
            result["postprocess_status"] = "rejected_different_basis"
        result.update(
            {
                "sample_id": task["sample_id"],
                "setting_id": task["setting_id"],
                "analysis_group": task["analysis_group"],
                "basis": basis,
            }
        )
    return result


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1", "match", "matched"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def _dry_table_prediction(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": task["task_id"],
        "task_type": "table_family",
        **_task_cache_metadata(task),
        "review_id": task["review_id"],
        "sof_table_id": task["sof_table_id"],
        "analysis_group": task["analysis_group"],
        "analysis_group_name": task["analysis_group_name"],
        "match": False,
        "confidence": "low",
        "relationship": "unclear",
        "reason": "dry_run_no_llm",
        "llm_status": "dry_run",
        "llm_raw": {},
    }


def _dry_row_prediction(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": task["task_id"],
        "task_type": "row_setting",
        **_task_cache_metadata(task),
        "sample_id": task["sample_id"],
        "review_id": task["review_id"],
        "sof_table_id": task["sof_table_id"],
        "setting_id": task["setting_id"],
        "analysis_group": task["analysis_group"],
        "match": False,
        "confidence": "low",
        "basis": {},
        "reason": "dry_run_no_llm",
        "llm_status": "dry_run",
        "llm_raw": {},
    }


def _load_existing_predictions(
    path: Path,
    *,
    key_fields: tuple[str, ...],
    allowed_keys: set[str] | None = None,
    expected_task_metadata: dict[str, dict[str, str]] | None = None,
    reusable_statuses: set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    rows = read_jsonl(path)
    if reusable_statuses is not None:
        rows = [row for row in rows if str(row.get("llm_status") or "") in reusable_statuses]
    indexed = {"::".join(str(row.get(field) or "") for field in key_fields): row for row in rows}
    if allowed_keys is None:
        allowed = indexed
    else:
        allowed = {key: row for key, row in indexed.items() if key in allowed_keys}
    if not expected_task_metadata:
        return allowed
    return {
        key: row
        for key, row in allowed.items()
        if all(row.get(field) == expected_value for field, expected_value in expected_task_metadata.get(key, {}).items())
    }


def _resolve_alignment_results(
    *,
    alignment_inputs: list[dict[str, Any]],
    workflow_rows: list[dict[str, Any]],
    row_predictions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    workflow_by_setting = {str(row["setting_id"]): row for row in workflow_rows}
    predictions_by_sample: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for prediction in row_predictions:
        if prediction.get("match") is True and prediction.get("confidence") in {"high", "medium"}:
            predictions_by_sample[str(prediction["sample_id"])].append(prediction)
    results: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    for row in alignment_inputs:
        sample_id = row["sample_id"]
        matches = predictions_by_sample.get(sample_id, [])
        if not matches:
            result = {
                "sample_id": sample_id,
                "review_id": row["review_id"],
                "status": "no_match",
                "matched_candidates": [],
            }
            results.append(result)
            audit_rows.append(result)
            continue
        strict_matches = [match for match in matches if _is_strict_row_match(match)]
        if len(strict_matches) == 1:
            matches = strict_matches
        if len(matches) > 1:
            result = {
                "sample_id": sample_id,
                "review_id": row["review_id"],
                "status": "ambiguous",
                "matched_candidates": [
                    {
                        "setting_id": match["setting_id"],
                        "confidence": match["confidence"],
                        "reason": match.get("reason"),
                    }
                    for match in matches
                ],
            }
            results.append(result)
            audit_rows.append(result)
            continue
        match = matches[0]
        workflow_row = workflow_by_setting.get(str(match["setting_id"]))
        verifier = _verify_alignment(sof_row=row, workflow_row=workflow_row)
        status = "matched" if verifier["accepted"] else "verifier_rejected"
        result = {
            "sample_id": sample_id,
            "review_id": row["review_id"],
            "status": status,
            "selected_setting_id": match["setting_id"] if workflow_row else None,
            "selected_estimate_ref": (workflow_row or {}).get("effect_estimate_ref"),
            "selected_included_study_ids": (workflow_row or {}).get("included_study_ids") or [],
            "confidence": match["confidence"],
            "matched_candidates": [
                {
                    "setting_id": match["setting_id"],
                    "confidence": match["confidence"],
                    "reason": match.get("reason"),
                    "basis": match.get("basis") or {},
                }
            ],
            "verifier": verifier,
        }
        results.append(result)
        if status != "matched":
            audit_rows.append(result)
    return results, audit_rows


def _resolve_alignment_results_v2(
    *,
    alignment_inputs: list[dict[str, Any]],
    workflow_rows: list[dict[str, Any]],
    table_predictions: list[dict[str, Any]],
    row_predictions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    workflow_by_setting = {str(row["setting_id"]): row for row in workflow_rows}
    table_prediction_by_key = {
        (str(row.get("review_id") or ""), str(row.get("sof_table_id") or ""), str(row.get("analysis_group") or "")): row
        for row in table_predictions
    }
    predictions_by_sample: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for prediction in row_predictions:
        if prediction.get("match") is True:
            predictions_by_sample[str(prediction["sample_id"])].append(prediction)

    results: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    for sof_row in alignment_inputs:
        sample_id = str(sof_row["sample_id"])
        raw_matches = predictions_by_sample.get(sample_id, [])
        high_matches = [row for row in raw_matches if row.get("confidence") == "high"]
        strict_matches = [row for row in high_matches if _is_strict_row_match(row)]
        if not raw_matches:
            result = _alignment_reject_result(sof_row=sof_row, status="no_match", matched_candidates=[])
            results.append(result)
            audit_rows.append(result)
            continue
        if not strict_matches:
            status = "low_confidence" if high_matches != raw_matches else "verifier_rejected"
            result = _alignment_reject_result(
                sof_row=sof_row,
                status=status,
                matched_candidates=[_alignment_candidate_summary(row) for row in raw_matches],
            )
            results.append(result)
            audit_rows.append(result)
            continue
        if len(strict_matches) > 1:
            result = _alignment_reject_result(
                sof_row=sof_row,
                status="multiple_match",
                matched_candidates=[_alignment_candidate_summary(row) for row in strict_matches],
            )
            results.append(result)
            audit_rows.append(result)
            continue

        match = strict_matches[0]
        workflow_row = workflow_by_setting.get(str(match["setting_id"]))
        table_key = (str(match["review_id"]), str(match["sof_table_id"]), str(match["analysis_group"]))
        table_prediction = table_prediction_by_key.get(table_key) or {}
        verifier = _verify_alignment_v2(sof_row=sof_row, workflow_row=workflow_row, row_prediction=match)
        if not verifier["accepted"]:
            result = _alignment_reject_result(
                sof_row=sof_row,
                status=verifier["reason"],
                matched_candidates=[_alignment_candidate_summary(match)],
                verifier=verifier,
            )
            results.append(result)
            audit_rows.append(result)
            continue

        result = {
            "sample_id": sample_id,
            "sof_row_id": f"sof-row::{sample_id}",
            "review_id": sof_row["review_id"],
            "sof_table_id": sof_row["sof_table_id"],
            "status": "matched",
            "selected_setting_id": match["setting_id"],
            "selected_estimate_ref": (workflow_row or {}).get("effect_estimate_ref"),
            "selected_included_study_ids": (workflow_row or {}).get("included_study_ids") or [],
            "table_family": {
                "analysis_group": match["analysis_group"],
                "confidence": table_prediction.get("confidence"),
                "relationship": table_prediction.get("relationship"),
                "reason": table_prediction.get("reason"),
            },
            "row_setting": {
                "confidence": match["confidence"],
                "basis": match.get("basis") or {},
                "reason": match.get("reason"),
            },
            "matched_candidates": [_alignment_candidate_summary(match)],
            "verifier": verifier,
        }
        results.append(result)
    return results, audit_rows


def _alignment_reject_result(
    *,
    sof_row: dict[str, Any],
    status: str,
    matched_candidates: list[dict[str, Any]],
    verifier: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = {
        "sample_id": sof_row["sample_id"],
        "sof_row_id": f"sof-row::{sof_row['sample_id']}",
        "review_id": sof_row["review_id"],
        "sof_table_id": sof_row["sof_table_id"],
        "status": status,
        "matched_candidates": matched_candidates,
    }
    if verifier is not None:
        result["verifier"] = verifier
    return result


def _alignment_candidate_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "setting_id": row.get("setting_id"),
        "analysis_group": row.get("analysis_group"),
        "confidence": row.get("confidence"),
        "basis": row.get("basis") or {},
        "reason": row.get("reason"),
    }


def _verify_alignment_v2(
    *,
    sof_row: dict[str, Any],
    workflow_row: dict[str, Any] | None,
    row_prediction: dict[str, Any],
) -> dict[str, Any]:
    if workflow_row is None:
        return {"accepted": False, "reason": "selected_setting_missing"}
    if str(workflow_row["review_id"]) != str(sof_row["review_id"]):
        return {"accepted": False, "reason": "review_id_mismatch"}
    basis = row_prediction.get("basis") if isinstance(row_prediction.get("basis"), dict) else {}
    for field in ("outcome", "timepoint", "subgroup", "numeric"):
        if str(basis.get(field) or "").lower() == "different":
            return {"accepted": False, "reason": f"{field}_conflict"}
    if row_prediction.get("confidence") != "high":
        return {"accepted": False, "reason": "low_confidence"}
    return {"accepted": True, "reason": "unique_high_confidence_match"}


def _is_strict_row_match(prediction: dict[str, Any]) -> bool:
    basis = prediction.get("basis") if isinstance(prediction.get("basis"), dict) else {}
    return (
        prediction.get("confidence") == "high"
        and str(basis.get("numeric") or "").lower() == "same"
        and str(basis.get("subgroup") or "").lower() in {"same", "not_applicable"}
        and str(basis.get("outcome") or "").lower() in {"same", "compatible"}
        and str(basis.get("timepoint") or "").lower() in {"same", "compatible", "not_applicable"}
    )


def _verify_alignment(sof_row: dict[str, Any], workflow_row: dict[str, Any] | None) -> dict[str, Any]:
    if workflow_row is None:
        return {"accepted": False, "reason": "selected_setting_missing"}
    if str(workflow_row["review_id"]) != str(sof_row["review_id"]):
        return {"accepted": False, "reason": "review_id_mismatch"}
    # Keep numeric checks conservative in the probe; flag only obvious exact textual contradictions later.
    return {"accepted": True, "reason": "basic_identity_checks_passed"}


def _alignment_probe_summary(
    *,
    alignment_inputs: list[dict[str, Any]],
    tables: list[dict[str, Any]],
    table_tasks: list[dict[str, Any]],
    table_predictions: list[dict[str, Any]],
    row_tasks: list[dict[str, Any]],
    row_predictions: list[dict[str, Any]],
    results: list[dict[str, Any]],
    audit_rows: list[dict[str, Any]],
    use_llm: bool,
    model: str,
    api_mode: str | None = None,
) -> dict[str, Any]:
    result_status = Counter(str(row.get("status") or "unknown") for row in results)
    table_match_count = sum(1 for row in table_predictions if row.get("match") is True)
    row_match_count = sum(1 for row in row_predictions if row.get("match") is True)
    candidate_selection_counts = Counter(
        str((task.get("candidate_selection") or {}).get("mode") or "unknown")
        for task in row_tasks
    )
    row_task_count_by_sample: dict[str, int] = Counter(str(task.get("sample_id") or "") for task in row_tasks)
    return {
        "mode": "llm" if use_llm else "dry_run",
        "model": model if use_llm else None,
        "api_mode": api_mode,
        "input_row_count": len(alignment_inputs),
        "table_count": len(tables),
        "table_family_task_count": len(table_tasks),
        "table_family_match_count": table_match_count,
        "row_setting_task_count": len(row_tasks),
        "row_setting_task_count_by_candidate_selection": dict(sorted(candidate_selection_counts.items())),
        "row_setting_candidate_count_by_sample": {
            "rows_with_tasks": len(row_task_count_by_sample),
            "max": max(row_task_count_by_sample.values()) if row_task_count_by_sample else 0,
            "single_candidate_rows": sum(1 for count in row_task_count_by_sample.values() if count == 1),
            "le5_candidate_rows": sum(1 for count in row_task_count_by_sample.values() if count <= 5),
            "le10_candidate_rows": sum(1 for count in row_task_count_by_sample.values() if count <= 10),
        },
        "row_setting_match_count": row_match_count,
        "result_status_counts": dict(result_status),
        "audit_count": len(audit_rows),
        "reviews": sorted({row["review_id"] for row in alignment_inputs}),
    }


def _alignment_v2_summary(
    *,
    alignment_name: str,
    alignment_inputs: list[dict[str, Any]],
    tables: list[dict[str, Any]],
    workflow_rows: list[dict[str, Any]],
    table_tasks: list[dict[str, Any]],
    table_predictions: list[dict[str, Any]],
    row_tasks: list[dict[str, Any]],
    row_predictions: list[dict[str, Any]],
    results: list[dict[str, Any]],
    audit_rows: list[dict[str, Any]],
    workflow_filter_report: dict[str, Any] | None = None,
    use_llm: bool,
    model: str,
    api_mode: str | None = None,
) -> dict[str, Any]:
    result_status = Counter(str(row.get("status") or "unknown") for row in results)
    matched_rows = [row for row in results if row.get("status") == "matched"]
    table_match_count = sum(1 for row in table_predictions if row.get("match") is True)
    row_match_count = sum(1 for row in row_predictions if row.get("match") is True)
    candidate_selection_counts = Counter(
        str((task.get("candidate_selection") or {}).get("mode") or "unknown")
        for task in row_tasks
    )
    row_task_count_by_sample: dict[str, int] = Counter(str(task.get("sample_id") or "") for task in row_tasks)
    return {
        "builder_version": (
            ALIGNMENT_BUILDER_VERSION_V3
            if alignment_name.startswith("alignment_v3")
            else "online-pipeline-builder-v2-grade-alignment"
        ),
        "alignment_name": alignment_name,
        "mode": "llm" if use_llm else "dry_run",
        "model": model if use_llm else None,
        "api_mode": api_mode,
        "input_row_count": len(alignment_inputs),
        "table_count": len(tables),
        "workflow_row_universe_count": len(workflow_rows),
        "workflow_filter": workflow_filter_report or {},
        "table_family_task_count": len(table_tasks),
        "table_family_match_count": table_match_count,
        "row_setting_task_count": len(row_tasks),
        "row_setting_task_count_by_candidate_selection": dict(sorted(candidate_selection_counts.items())),
        "row_setting_candidate_count_by_sample": {
            "rows_with_tasks": len(row_task_count_by_sample),
            "max": max(row_task_count_by_sample.values()) if row_task_count_by_sample else 0,
            "single_candidate_rows": sum(1 for count in row_task_count_by_sample.values() if count == 1),
            "le5_candidate_rows": sum(1 for count in row_task_count_by_sample.values() if count <= 5),
            "le10_candidate_rows": sum(1 for count in row_task_count_by_sample.values() if count <= 10),
        },
        "row_setting_match_count": row_match_count,
        "matched_row_count": len(matched_rows),
        "audit_count": len(audit_rows),
        "result_status_counts": dict(result_status),
        "reviews": sorted({row["review_id"] for row in alignment_inputs}),
        "matched_review_count": len({row["review_id"] for row in matched_rows}),
        "matched_table_count": len({(row["review_id"], row["sof_table_id"]) for row in matched_rows}),
    }


def _records_from_alignment_v2(*, raw_root: Path) -> list[dict[str, Any]]:
    return _records_from_alignment(raw_root=raw_root, alignment_name="alignment_v2")


def _grade_dataset_input_coverage(records: list[dict[str, Any]]) -> dict[str, Any]:
    shared_by_sof = {record["sof_row_id"]: record["shared_row"] for record in records}
    rob_instances = [record["instance"] for record in records if record["domain"] == "risk_of_bias"]
    indirect_instances = [record["instance"] for record in records if record["domain"] == "indirectness"]
    binding_sources = Counter()
    zero_included = 0
    zero_study_rows = 0
    for shared in shared_by_sof.values():
        evidence_body = shared.get("evidence_body") or {}
        coverage = evidence_body.get("coverage") or {}
        binding_sources.update([coverage.get("study_binding_source") or "unknown"])
        if not evidence_body.get("included_study_ids"):
            zero_included += 1
        if not evidence_body.get("study_result_rows"):
            zero_study_rows += 1
    rob_method_counts = Counter()
    indirect_method_counts = Counter()
    for instance in rob_instances:
        coverage = ((instance.get("domain_evidence") or {}).get("study_join_coverage") or {})
        for method, count in (coverage.get("match_method_counts") or {}).items():
            rob_method_counts[method] += int(count)
    for instance in indirect_instances:
        coverage = ((instance.get("domain_evidence") or {}).get("study_join_coverage") or {})
        for method, count in (coverage.get("match_method_counts") or {}).items():
            indirect_method_counts[method] += int(count)
    return {
        "shared_row_count": len(shared_by_sof),
        "domain_instance_count": len(records),
        "evidence_body": {
            "study_binding_source_counts": dict(sorted(binding_sources.items())),
            "rows_with_zero_included_study_ids": zero_included,
            "rows_with_zero_study_result_rows": zero_study_rows,
        },
        "risk_of_bias": {
            "instances": len(rob_instances),
            "instances_with_any_risk_of_bias_assessment": sum(
                1 for instance in rob_instances if ((instance.get("domain_evidence") or {}).get("risk_of_bias_assessments") or [])
            ),
            "instances_with_missing_risk_of_bias_for_any_study": sum(
                1 for instance in rob_instances if ((instance.get("domain_evidence") or {}).get("risk_of_bias_missing_study_ids") or [])
            ),
            "study_id_match_method_counts": dict(sorted(rob_method_counts.items())),
        },
        "indirectness": {
            "instances": len(indirect_instances),
            "instances_with_any_study_characteristics": sum(
                1 for instance in indirect_instances if ((instance.get("domain_evidence") or {}).get("study_characteristics") or [])
            ),
            "instances_with_missing_characteristics_for_any_study": sum(
                1 for instance in indirect_instances if ((instance.get("domain_evidence") or {}).get("study_characteristics_missing_study_ids") or [])
            ),
            "study_id_match_method_counts": dict(sorted(indirect_method_counts.items())),
        },
    }


def _records_from_alignment(*, raw_root: Path, alignment_name: str) -> list[dict[str, Any]]:
    alignment_dir = raw_root / "intermediate" / alignment_name
    results = read_jsonl(alignment_dir / "alignment_results.jsonl")
    sof_inputs = read_jsonl(alignment_dir / "sof_alignment_inputs.jsonl")
    source_sof_rows = _load_sof_rows_for_alignment(raw_root=raw_root)
    workflow_rows = read_jsonl(alignment_dir / "workflow_setting_universe.jsonl")
    gold_by_sample = _load_sof_gold_by_sample(raw_root=raw_root)
    sof_by_sample = {str(row["sample_id"]): row for row in sof_inputs}
    source_sof_by_sample = {str(row["sample_id"]): row for row in source_sof_rows}
    workflow_by_setting = {str(row["setting_id"]): row for row in workflow_rows}
    sr_cache: dict[str, dict[str, Any]] = {}

    records: list[dict[str, Any]] = []
    for result in results:
        if result.get("status") != "matched":
            continue
        sample_id = str(result["sample_id"])
        sof_row = sof_by_sample.get(sample_id)
        source_sof_row = source_sof_by_sample.get(sample_id) or sof_row or {}
        workflow_row = workflow_by_setting.get(str(result.get("selected_setting_id") or ""))
        gold_domains = (((gold_by_sample.get(sample_id) or {}).get("gold") or {}).get("domains") or {})
        if not sof_row or not workflow_row:
            continue
        evidence_body = _evidence_body_for_grade_row(
            workflow_row=workflow_row,
            source_sof_row=source_sof_row,
        )
        upstream = _study_upstream_evidence_for_sof_row(
            sof_row=source_sof_row,
            included_study_ids=evidence_body["included_study_ids"],
            sr_cache=sr_cache,
        )
        source_prefix = "grade-v4" if alignment_name.startswith("alignment_v3") else "grade-v2"
        for domain in DOMAIN_NAMES:
            gold = gold_domains.get(domain)
            if not gold:
                continue
            instance_id = f"{source_prefix}::{sample_id}::{domain}"
            instance = _grade_v2_instance(
                instance_id=instance_id,
                domain=domain,
                sof_row=sof_row,
                workflow_row=workflow_row,
                evidence_body=evidence_body,
                upstream=upstream,
                alignment_result=result,
            )
            if domain == "risk_of_bias" and not ((instance.get("domain_evidence") or {}).get("risk_of_bias_assessments") or []):
                continue
            if domain == "imprecision" and _has_missing_imprecision_ci(instance):
                continue
            records.append(
                {
                    "source_id": instance_id,
                    "sof_row_id": instance["sof_row_id"],
                    "review_id": instance["review_id"],
                    "domain": domain,
                    "shared_row": _grade_v2_shared_row(instance=instance, sof_row=sof_row, alignment_result=result),
                    "instance": instance,
                    "gold": {
                        "instance_id": instance_id,
                        "sof_row_id": instance["sof_row_id"],
                        "domain": domain,
                        "judgement": _normalized_gold_judgement(domain=domain, gold=gold),
                    },
                }
            )
    return sorted(records, key=lambda record: record["source_id"])


def _has_missing_imprecision_ci(instance: dict[str, Any]) -> bool:
    estimate = ((instance.get("domain_evidence") or {}).get("effect_estimate") or {})
    return estimate.get("ci_lower") is None or estimate.get("ci_upper") is None


def _grade_v2_instance(
    *,
    instance_id: str,
    domain: str,
    sof_row: dict[str, Any],
    workflow_row: dict[str, Any],
    evidence_body: dict[str, Any],
    upstream: dict[str, Any],
    alignment_result: dict[str, Any],
) -> dict[str, Any]:
    setting = workflow_row["analysis_setting"]
    alignment = {
        "selected_setting_id": workflow_row["setting_id"],
        "table_family_confidence": (alignment_result.get("table_family") or {}).get("confidence"),
        "row_setting_confidence": (alignment_result.get("row_setting") or {}).get("confidence"),
        "row_setting_basis": (alignment_result.get("row_setting") or {}).get("basis") or {},
        "table_family": alignment_result.get("table_family") or {},
        "row_setting": alignment_result.get("row_setting") or {},
        "verifier": alignment_result.get("verifier") or {},
    }
    full_evidence_body = {
        **evidence_body,
        "sof_row_id": alignment_result["sof_row_id"],
        "sof_context": _sof_context(sof_row),
        "analysis_setting": setting,
        "study_characteristics": upstream.get("study_characteristics") or [],
        "study_characteristics_missing_study_ids": upstream.get("missing_study_characteristics_study_ids") or [],
        "alignment": alignment,
    }
    return {
        "instance_id": instance_id,
        "sample_id": sof_row["sample_id"],
        "sof_row_id": alignment_result["sof_row_id"],
        "review_id": sof_row["review_id"],
        "domain": domain,
        "question_text": sof_row.get("review_title") or "",
        "question_pico": sof_row.get("question_pico") or {},
        "sof_context": _sof_context(sof_row),
        "evidence_body": full_evidence_body,
        "analysis_setting": setting,
        "effect_estimate_ref": full_evidence_body.get("effect_estimate_ref") or {},
        "effect_estimate": full_evidence_body.get("effect_estimate") or {},
        "included_study_ids": full_evidence_body.get("included_study_ids") or [],
        "study_result_rows": full_evidence_body.get("study_result_rows") or [],
        "analysis_method": workflow_row.get("analysis_method"),
        "domain_evidence": _domain_evidence_v2(
            domain=domain,
            workflow_row=workflow_row,
            sof_row=sof_row,
            evidence_body=full_evidence_body,
            upstream=upstream,
        ),
        "alignment": alignment,
    }


def _grade_v2_shared_row(*, instance: dict[str, Any], sof_row: dict[str, Any], alignment_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "sof_row_id": instance["sof_row_id"],
        "sample_id": instance["sample_id"],
        "review_id": instance["review_id"],
        "question_text": instance["question_text"],
        "question_pico": instance["question_pico"],
        "sof_context": instance["sof_context"],
        "evidence_body": instance["evidence_body"],
        "analysis_setting": instance["analysis_setting"],
        "effect_estimate_ref": instance["effect_estimate_ref"],
        "included_study_ids": instance["included_study_ids"],
        "alignment": instance["alignment"],
        "source": {
            "sof_table_id": sof_row.get("sof_table_id"),
            "alignment_status": alignment_result.get("status"),
        },
    }


def _sof_context(sof_row: dict[str, Any]) -> dict[str, Any]:
    return {
        "sof_table_id": sof_row.get("sof_table_id"),
        "table_title": sof_row.get("table_title"),
        "row_order": sof_row.get("row_order"),
        "outcome_name": sof_row.get("outcome_name"),
        "timepoint_text": sof_row.get("timepoint_text"),
        "relative_effect_text": sof_row.get("relative_effect_text"),
        "participants_text": sof_row.get("participants_text"),
        "studies_text": sof_row.get("studies_text"),
        "population_text": sof_row.get("population_text"),
        "setting_text": sof_row.get("setting_text"),
        "intervention_text": sof_row.get("intervention_text"),
        "comparison_text": sof_row.get("comparison_text"),
        "comment_text": sof_row.get("comment_text"),
        "footnote_texts": sof_row.get("footnote_texts") or [],
        "source_summary_of_findings_span_text": sof_row.get("source_summary_of_findings_span_text"),
    }


def _evidence_body_for_grade_row(*, workflow_row: dict[str, Any], source_sof_row: dict[str, Any]) -> dict[str, Any]:
    estimate = dict(workflow_row.get("effect_estimate") or {})
    setting = workflow_row.get("analysis_setting") or {}
    fallback_rows = _fallback_study_result_rows_from_sof_alignment(source_sof_row=source_sof_row, setting=setting)
    workflow_study_rows = list(workflow_row.get("study_result_rows") or [])
    study_rows = workflow_study_rows or fallback_rows
    included_study_ids = (
        list(workflow_row.get("included_study_ids") or [])
        or list(estimate.get("included_study_ids") or [])
        or _unique_nonempty(row.get("study_id") for row in study_rows)
    )
    if included_study_ids and not estimate.get("included_study_ids"):
        estimate["included_study_ids"] = included_study_ids
    if study_rows and not estimate.get("study_count"):
        estimate["study_count"] = len({str(row.get("study_id")) for row in study_rows if row.get("study_id")})
    if study_rows and not estimate.get("participant_count"):
        participant_count = _participant_count_from_study_rows(study_rows)
        if participant_count is not None:
            estimate["participant_count"] = participant_count
    return {
        "setting_id": workflow_row.get("setting_id"),
        "setting_family_id": workflow_row.get("setting_family_id"),
        "candidate_id": workflow_row.get("candidate_id"),
        "effect_estimate_ref": workflow_row.get("effect_estimate_ref") or {},
        "effect_estimate": estimate,
        "included_study_ids": included_study_ids,
        "study_result_rows": study_rows,
        "analysis_method": workflow_row.get("analysis_method"),
        "subgroup_estimates": workflow_row.get("subgroup_estimates") or [],
        "subgroup_difference_tests": workflow_row.get("subgroup_difference_tests") or [],
        "coverage": {
            "workflow_included_study_id_count": len(workflow_row.get("included_study_ids") or []),
            "fallback_study_result_row_count": len(fallback_rows),
            "study_result_row_count": len(study_rows),
            "included_study_id_count": len(included_study_ids),
            "study_binding_source": (
                "workflow"
                if workflow_row.get("included_study_ids")
                else "sof_alignment_candidate"
                if included_study_ids
                else "missing"
            ),
        },
    }


def _fallback_study_result_rows_from_sof_alignment(*, source_sof_row: dict[str, Any], setting: dict[str, Any]) -> list[dict[str, Any]]:
    analysis_group = str(setting.get("analysis_group") or "")
    analysis_number = str(setting.get("analysis_number") or "")
    if not analysis_group or not analysis_number:
        return []
    for candidate in source_sof_row.get("alignment_candidates") or []:
        analysis = candidate.get("analysis") or {}
        if str(analysis.get("analysis_group") or "") != analysis_group:
            continue
        if str(analysis.get("analysis_number") or "") != analysis_number:
            continue
        rows = []
        for index, row in enumerate(analysis.get("study_rows") or []):
            study_id = str(row.get("study") or "").strip()
            if not study_id:
                continue
            rows.append(
                {
                    "row_id": f"sof-alignment-row::{source_sof_row.get('sample_id')}::{index}",
                    "setting_id": setting.get("setting_id"),
                    "study_id": study_id,
                    "study_year": row.get("year"),
                    "extraction_status": "extracted",
                    "data_type": setting.get("data_type") or analysis.get("data_type"),
                    "comparison": {
                        "experimental_arm": ((setting.get("comparison") or {}).get("experimental")),
                        "control_arm": ((setting.get("comparison") or {}).get("comparator")),
                    },
                    "outcome": {
                        "label": ((setting.get("outcome") or {}).get("label")) or analysis.get("analysis_name"),
                        "timepoint": ((setting.get("timepoint") or {}).get("label")),
                    },
                    "subgroup": setting.get("subgroup") or {},
                    "result_data": _result_data_from_alignment_study_row(row=row, data_type=setting.get("data_type") or analysis.get("data_type")),
                    "effect": {
                        "value": row.get("effect"),
                        "ci_lower": row.get("ci_lower"),
                        "ci_upper": row.get("ci_upper"),
                        "weight": row.get("weight"),
                    },
                    "source": {
                        "source": "sof_alignment_candidates",
                        "sample_id": source_sof_row.get("sample_id"),
                        "analysis_key": analysis.get("analysis_key"),
                    },
                }
            )
        if rows:
            return rows
    return []


def _result_data_from_alignment_study_row(*, row: dict[str, Any], data_type: Any) -> dict[str, Any] | None:
    normalized_type = str(data_type or "").lower()
    if normalized_type == "dichotomous":
        values = {
            "experimental_events": row.get("experimental_cases"),
            "experimental_total": row.get("experimental_n"),
            "control_events": row.get("control_cases"),
            "control_total": row.get("control_n"),
        }
        return values if any(value is not None for value in values.values()) else None
    if normalized_type == "continuous":
        values = {
            "experimental_mean": row.get("experimental_mean"),
            "experimental_sd": row.get("experimental_sd"),
            "experimental_total": row.get("experimental_n"),
            "control_mean": row.get("control_mean"),
            "control_sd": row.get("control_sd"),
            "control_total": row.get("control_n"),
        }
        return values if any(value is not None for value in values.values()) else None
    return None


def _participant_count_from_study_rows(rows: list[dict[str, Any]]) -> int | None:
    total = 0
    found = False
    for row in rows:
        result_data = row.get("result_data") or {}
        experimental_total = _safe_int(result_data.get("experimental_total"))
        control_total = _safe_int(result_data.get("control_total"))
        if experimental_total is None and control_total is None:
            continue
        total += int(experimental_total or 0) + int(control_total or 0)
        found = True
    return total if found else None


def _study_upstream_evidence_for_sof_row(
    *,
    sof_row: dict[str, Any],
    included_study_ids: list[str],
    sr_cache: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    source_review_path = str(sof_row.get("source_review_path") or sof_row.get("source_json") or "")
    source_data = _load_source_review_study_index(source_review_path, sr_cache=sr_cache)
    characteristics_by_id = source_data.get("characteristics_by_id") or {}
    alias_to_id = source_data.get("alias_to_id") or {}
    study_characteristics = []
    risk_of_bias_assessments = []
    join_rows = []
    missing_characteristics = []
    missing_rob = []
    for requested_id in included_study_ids:
        matched_id, match_method = _match_study_id(requested_id, characteristics_by_id=characteristics_by_id, alias_to_id=alias_to_id)
        source_item = characteristics_by_id.get(matched_id or "")
        if source_item:
            study_characteristics.append(_study_characteristics_from_source_item(requested_id=requested_id, matched_id=matched_id or requested_id, item=source_item))
            rob = _risk_of_bias_from_source_item(requested_id=requested_id, matched_id=matched_id or requested_id, item=source_item)
            if rob.get("domains"):
                risk_of_bias_assessments.append(rob)
            else:
                missing_rob.append(requested_id)
        else:
            missing_characteristics.append(requested_id)
            missing_rob.append(requested_id)
        join_rows.append(
            {
                "study_id": requested_id,
                "matched_study_id": matched_id,
                "match_method": match_method,
                "has_study_characteristics": bool(source_item),
                "has_risk_of_bias": bool(source_item and (source_item.get("risk_of_bias") or [])),
            }
        )
    method_counts = Counter(row["match_method"] for row in join_rows)
    return {
        "study_characteristics": study_characteristics,
        "risk_of_bias_assessments": risk_of_bias_assessments,
        "missing_study_characteristics_study_ids": missing_characteristics,
        "missing_risk_of_bias_study_ids": missing_rob,
        "study_join_rows": join_rows,
        "study_join_coverage": {
            "source_review_path": source_review_path,
            "requested_study_count": len(included_study_ids),
            "matched_study_characteristics_count": len(study_characteristics),
            "matched_risk_of_bias_count": len(risk_of_bias_assessments),
            "missing_study_characteristics_count": len(missing_characteristics),
            "missing_risk_of_bias_count": len(missing_rob),
            "match_method_counts": dict(sorted(method_counts.items())),
        },
    }


def _load_source_review_study_index(path: str, *, sr_cache: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not path:
        return {"characteristics_by_id": {}, "alias_to_id": {}}
    if path in sr_cache:
        return sr_cache[path]
    resolved = Path(path)
    if not resolved.exists():
        data = {"characteristics_by_id": {}, "alias_to_id": {}}
        sr_cache[path] = data
        return data
    source = json.loads(resolved.read_text(encoding="utf-8"))
    included = ((source.get("characteristics_of_studies") or {}).get("included") or [])
    characteristics_by_id = {
        str(item.get("study_id") or ""): item
        for item in included
        if item.get("study_id")
    }
    alias_to_id: dict[str, str] = {}
    for study_id in characteristics_by_id:
        for alias in _study_id_aliases(study_id):
            alias_to_id.setdefault(alias, study_id)
    data = {"characteristics_by_id": characteristics_by_id, "alias_to_id": alias_to_id}
    sr_cache[path] = data
    return data


def _match_study_id(
    requested_id: str,
    *,
    characteristics_by_id: dict[str, dict[str, Any]],
    alias_to_id: dict[str, str],
) -> tuple[str | None, str]:
    if requested_id in characteristics_by_id:
        return requested_id, "exact"
    aliases = _study_id_aliases(requested_id)
    for alias in aliases:
        if alias in alias_to_id:
            return alias_to_id[alias], "normalized"
    requested_core = _study_id_core_alias(requested_id)
    candidates = [
        study_id
        for alias, study_id in alias_to_id.items()
        if requested_core and (requested_core == alias or requested_core in alias or alias in requested_core)
    ]
    unique_candidates = sorted(set(candidates))
    if len(unique_candidates) == 1:
        return unique_candidates[0], "substring"
    return None, "missing"


def _study_id_aliases(value: Any) -> list[str]:
    raw = str(value or "").strip()
    normalized = _normalize_study_id(raw)
    aliases = {normalized}
    core = _study_id_core_alias(raw)
    if core:
        aliases.add(core)
    if normalized.startswith("von "):
        aliases.add(normalized.removeprefix("von ").strip())
    for prefix in ("none detected", "not detected", "notes", "n/a", "na", "available"):
        if normalized.startswith(prefix):
            aliases.add(normalized.removeprefix(prefix).strip(" .:-"))
    aliases = {alias for alias in aliases if alias}
    return sorted(aliases, key=lambda item: (len(item), item))


def _study_id_core_alias(value: Any) -> str:
    normalized = _normalize_study_id(value)
    year_match = re.search(r"(19|20)\d{2}[a-z]?", normalized)
    if not year_match:
        return normalized
    year = year_match.group(0)
    before_year = normalized[: year_match.start()]
    tokens = re.findall(r"[a-z]+", before_year)
    if not tokens:
        return year
    surname = tokens[-1]
    particles = {"van", "von", "de", "da", "di", "del", "der", "den", "la", "le"}
    if len(tokens) >= 2 and tokens[-2] in particles:
        surname = f"{tokens[-2]} {surname}"
    return f"{surname} {year}".strip()


def _normalize_study_id(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower()
    text = text.replace("‐", "-").replace("–", "-").replace("—", "-").replace("‑", "-")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _study_characteristics_from_source_item(*, requested_id: str, matched_id: str, item: dict[str, Any]) -> dict[str, Any]:
    return {
        "study_id": requested_id,
        "matched_study_id": matched_id,
        "population": item.get("participants") or "",
        "intervention_comparator": item.get("interventions") or "",
        "outcomes": item.get("outcomes") or "",
        "methods": item.get("methods") or "",
        "notes": item.get("notes") or "",
        "source": "characteristics_of_studies.included",
    }


def _risk_of_bias_from_source_item(*, requested_id: str, matched_id: str, item: dict[str, Any]) -> dict[str, Any]:
    domains = []
    for rob in item.get("risk_of_bias") or []:
        domains.append(
            {
                "domain_id": _normalize_rob_domain_id(rob.get("bias")),
                "domain": rob.get("bias") or "",
                "judgement": _normalize_rob_judgement(rob.get("judgement")),
                "support_text": rob.get("support") or "",
            }
        )
    return {
        "study_id": requested_id,
        "matched_study_id": matched_id,
        "domains": domains,
        "overall": _overall_rob_from_domains(domains),
        "source": "characteristics_of_studies.included.risk_of_bias",
    }


def _normalize_rob_domain_id(value: Any) -> str:
    text = _normalize_study_id(value)
    if "random" in text and "sequence" in text:
        return "random_sequence_generation"
    if "allocation" in text and "conceal" in text:
        return "allocation_concealment"
    if "participant" in text or "personnel" in text or "performance" in text:
        return "blinding_participants_personnel"
    if "outcome assessment" in text or "detection" in text or "assessor" in text:
        return "blinding_outcome_assessment"
    if "incomplete" in text or "attrition" in text:
        return "incomplete_outcome_data"
    if "selective" in text or "reporting" in text:
        return "selective_reporting"
    if "other" in text:
        return "other_bias"
    return text.replace(" ", "_")


def _normalize_rob_judgement(value: Any) -> str:
    text = _normalize_study_id(value)
    if "low" in text:
        return "low_risk"
    if "high" in text:
        return "high_risk"
    if "unclear" in text:
        return "unclear_risk"
    return text.replace(" ", "_") or "unclear_risk"


def _overall_rob_from_domains(domains: list[dict[str, Any]]) -> str:
    judgements = {domain.get("judgement") for domain in domains}
    if "high_risk" in judgements:
        return "high_risk"
    if "unclear_risk" in judgements:
        return "unclear_risk"
    if "low_risk" in judgements:
        return "low_risk"
    return "unclear_risk"


def _unique_nonempty(values: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _safe_int(value: Any) -> int | None:
    if value in {None, ""}:
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return None


def _domain_evidence_v2(
    *,
    domain: str,
    workflow_row: dict[str, Any],
    sof_row: dict[str, Any],
    evidence_body: dict[str, Any],
    upstream: dict[str, Any],
) -> dict[str, Any]:
    estimate = evidence_body.get("effect_estimate") or {}
    base = {
        "sof_context": _sof_context(sof_row),
        "effect_estimate": estimate,
        "study_count": estimate.get("study_count"),
        "participant_count": estimate.get("participant_count"),
        "analysis_method": workflow_row.get("analysis_method"),
        "included_study_ids": evidence_body.get("included_study_ids") or [],
        "study_join_coverage": upstream.get("study_join_coverage") or {},
    }
    if domain == "risk_of_bias":
        return {
            **base,
            "risk_of_bias_assessments": upstream.get("risk_of_bias_assessments") or [],
            "risk_of_bias_missing_study_ids": upstream.get("missing_risk_of_bias_study_ids") or [],
        }
    if domain == "inconsistency":
        return {
            **base,
            "heterogeneity": estimate.get("heterogeneity") or {
                "i2": estimate.get("heterogeneity_i2"),
                "tau2": estimate.get("tau2"),
                "chi2": estimate.get("chi2"),
                "p_value": estimate.get("p_value"),
            },
            "subgroup_estimates": evidence_body.get("subgroup_estimates") or [],
            "subgroup_difference_tests": evidence_body.get("subgroup_difference_tests") or [],
            "study_result_rows": evidence_body.get("study_result_rows") or [],
            "study_characteristics": upstream.get("study_characteristics") or [],
            "study_characteristics_missing_study_ids": upstream.get("missing_study_characteristics_study_ids") or [],
        }
    if domain == "indirectness":
        return {
            **base,
            "target_pico": {
                "review_pico": sof_row.get("question_pico") or {},
                "sof_population": sof_row.get("population_text"),
                "sof_setting": sof_row.get("setting_text"),
                "sof_intervention": sof_row.get("intervention_text"),
                "sof_comparison": sof_row.get("comparison_text"),
                "sof_outcome": sof_row.get("outcome_name"),
                "sof_timepoint": sof_row.get("timepoint_text"),
            },
            "analysis_setting": workflow_row.get("analysis_setting") or {},
            "screening_criteria": None,
            "study_characteristics": upstream.get("study_characteristics") or [],
            "study_characteristics_missing_study_ids": upstream.get("missing_study_characteristics_study_ids") or [],
        }
    if domain == "imprecision":
        return {
            **base,
            "data_type": (workflow_row.get("analysis_setting") or {}).get("data_type"),
            "effect_measure": estimate.get("effect_measure") or (workflow_row.get("analysis_setting") or {}).get("effect_measure"),
            "study_result_rows": evidence_body.get("study_result_rows") or [],
            "sof_relative_effect_text": sof_row.get("relative_effect_text"),
            "sof_absolute_effect_control_text": sof_row.get("absolute_effect_control_text"),
            "sof_absolute_effect_intervention_text": sof_row.get("absolute_effect_intervention_text"),
        }
    raise ValueError(f"Unsupported domain: {domain}")


def _normalized_gold_judgement(*, domain: str, gold: dict[str, Any]) -> dict[str, Any]:
    return {
        "domain": domain,
        "downgraded": gold.get("downgraded"),
        "severity": gold.get("severity"),
        "levels": gold.get("levels"),
        "level_evaluable": gold.get("level_evaluable"),
        "rationale": gold.get("rationale") or "",
        "source_spans": list(gold.get("source_spans") or []),
        "evidence_status": gold.get("evidence_status"),
    }


def _alignment_examples(
    *,
    results: list[dict[str, Any]],
    alignment_inputs: list[dict[str, Any]],
    workflow_rows: list[dict[str, Any]],
    status: str | None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    sof_by_sample = {str(row["sample_id"]): row for row in alignment_inputs}
    workflow_by_setting = {str(row["setting_id"]): row for row in workflow_rows}
    examples: list[dict[str, Any]] = []
    for result in results:
        if status is not None and result.get("status") != status:
            continue
        sof_row = sof_by_sample.get(str(result.get("sample_id") or ""))
        workflow_row = workflow_by_setting.get(str(result.get("selected_setting_id") or ""))
        candidate = None
        if workflow_row is None and result.get("matched_candidates"):
            candidate_id = str((result.get("matched_candidates") or [{}])[0].get("setting_id") or "")
            workflow_row = workflow_by_setting.get(candidate_id)
        if workflow_row is not None:
            candidate = _candidate_row_summary(workflow_row)
        examples.append(
            {
                "sample_id": result.get("sample_id"),
                "review_id": result.get("review_id"),
                "status": result.get("status"),
                "sof_row": _sof_context(sof_row or {}),
                "candidate_setting": candidate,
                "alignment": {
                    "table_family": result.get("table_family"),
                    "row_setting": result.get("row_setting"),
                    "matched_candidates": result.get("matched_candidates") or [],
                    "verifier": result.get("verifier"),
                },
            }
        )
        if len(examples) >= limit:
            break
    return examples


def _raw_snapshot_exists(raw_root: Path) -> bool:
    return (raw_root / "intermediate" / "row_workflow_mapped.jsonl").exists()


def _raw_snapshot_sha256(raw_root: Path) -> str:
    digest = {
        "source_manifest": json.loads((raw_root / "source_manifest.json").read_text(encoding="utf-8")),
        "raw_quality_report": json.loads((raw_root / "intermediate" / "raw_quality_report.json").read_text(encoding="utf-8")),
    }
    return sha256_json(digest)


def _raw_snapshot_sha256_v2(raw_root: Path) -> str:
    return _raw_snapshot_sha256_alignment(raw_root, alignment_name="alignment_v2")


def _raw_snapshot_sha256_alignment(raw_root: Path, *, alignment_name: str) -> str:
    alignment_summary_path = raw_root / "intermediate" / alignment_name / "alignment_summary.json"
    digest = {
        "source_manifest": json.loads((raw_root / "source_manifest.json").read_text(encoding="utf-8")),
        "alignment_summary": json.loads(alignment_summary_path.read_text(encoding="utf-8")),
    }
    return sha256_json(digest)


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _write_records(path: Path, records: list[dict[str, Any]]) -> None:
    write_jsonl(path / "instances.jsonl", [record["instance"] for record in records], sort_keys=False)
    write_jsonl(path / "gold.jsonl", [record["gold"] for record in records], sort_keys=False)


def _write_domain_schema(path: Path, *, domain: str) -> None:
    path.write_text(
        f"# {domain} dataset\n\n"
        "- `instances.jsonl`: one aligned SoF row / one domain input record\n"
        "- `gold.jsonl`: normalized domain downgrade judgement\n"
        "- `shared/row_records.jsonl`: canonical SoF-row records used by this domain dataset\n"
        "- Required prediction fields for evaluation: `instance_id`, `domain`, `judgement.downgraded`, `judgement.severity`, `judgement.levels`, `judgement.level_evaluable`\n",
        encoding="utf-8",
    )


def _shared_rows_for_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    shared_rows = list({record["shared_row"]["sof_row_id"]: record["shared_row"] for record in records}.values())
    return sorted(shared_rows, key=lambda row: row["sof_row_id"])


def _write_domain_manifests(
    *,
    domain_dir: Path,
    domain: str,
    records: list[dict[str, Any]],
    split_counts: dict[str, int],
    builder_version: str,
    source: str,
    source_manifest_data: dict[str, Any],
    seed: str,
    sample_size: int | None,
    source_record_count: int,
    dataset_analysis_data: dict[str, Any],
) -> None:
    split_manifest = {
        "builder_version": builder_version,
        "seed": seed,
        "module": MODULE,
        "domain": domain,
        "dataset_name": domain_dir.name,
        "source": source,
        "sample_size": sample_size,
        "source_record_count": source_record_count,
        "selected_count": len(records),
        "split_strategy": "legacy_review_dev_test_plus_seeded_smoke_from_dev",
        "split_counts": split_counts,
        "splits": {
            split_name: {
                "count": split_counts.get(split_name, 0),
            }
            for split_name in ("all", "smoke", "dev", "test")
        },
    }
    build_manifest = {
        "builder_version": builder_version,
        "module": MODULE,
        "domain": domain,
        "dataset_name": domain_dir.name,
        "source": source,
        "sample_size": sample_size,
        "source_record_count": source_record_count,
        "selected_count": len(records),
        "seed": seed,
        "source_manifest_sha256": sha256_json(source_manifest_data),
        "split_manifest_sha256": sha256_json(split_manifest),
    }
    write_json(domain_dir / "source_manifest.json", source_manifest_data)
    write_json(domain_dir / "split_manifest.json", split_manifest)
    write_json(domain_dir / "build_manifest.json", build_manifest)
    write_json(domain_dir / "dataset_analysis.json", dataset_analysis_data)
