"""Predictors and task runners for benchmark2-v2 experiments."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .constants import (
    ALLOWED_SUPPORT_STATUSES,
    ALLOWED_UNCERTAIN_REASONS,
    DIRECT_FIELDS_BY_DATA_TYPE,
    ORACLE_EXTRACTION_TASK,
    PROPOSAL_TASK,
    ROUTED_EXTRACTION_TASK,
    SUPPORT_TASK,
)
from .io_utils import ensure_dir, iter_jsonl, write_json
from .llm_backend import default_model_name, make_client, repair_json_payload, response_text_to_json
from .normalize import normalize_subgroup, normalize_text, normalize_text_loose, normalize_timepoint_value, normalize_timepoints, row_key, structured_item_key
from .prompting import (
    PROMPT_VERSION,
    build_oracle_extraction_prompt_bundle,
    build_proposal_prompt_bundle,
    build_routed_extraction_prompt_bundle,
    build_support_prompt_bundle,
)
from .runtime import execute_task_run, resolve_task_paths, utc_now_iso, write_manifest

DEFAULT_PROMPT_VARIANT = "default"
PLACEHOLDER_VALUES = {"", "-", "--", "n/a", "na", "none", "null", "nil", "not reported", "unknown"}


def _filter_split(rows: list[dict], split: str | None) -> list[dict]:
    if split is None:
        return rows
    return [row for row in rows if row.get("split") == split]


def _load_rows(path: str | Path, split: str | None) -> list[dict]:
    return _filter_split(list(iter_jsonl(path) or []), split)


def _llm_text_response(messages: list[dict], *, model: str) -> str:
    client = make_client()
    response = client.chat.completions.create(model=model, messages=messages, temperature=0)
    content = response.choices[0].message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                texts.append(part.get("text", ""))
        return "".join(texts)
    raise ValueError("Unsupported LLM response content shape")


def _parse_with_repair(*, text: str, model: str) -> tuple[Any, dict]:
    try:
        return response_text_to_json(text), {"json_repair_attempted": 0, "json_repair_succeeded": 0}
    except Exception as exc:
        repaired = repair_json_payload(model=model, raw_text=text)
        return repaired, {
            "json_repair_attempted": 1,
            "json_repair_succeeded": 1,
            "initial_parse_error": repr(exc),
        }


def _prediction_metadata(*, bundle, mode: str) -> dict:
    return {
        "mode": mode,
        "model": default_model_name() if mode == "llm" else None,
        "prompt_version": PROMPT_VERSION,
        "prompt_name": bundle.prompt_name if bundle else None,
        "data_type": bundle.data_type if bundle else None,
        "context_stats": bundle.context_stats if bundle else {},
    }


def _sanitize_support_prediction(payload: Any) -> tuple[dict, dict]:
    if not isinstance(payload, dict):
        raise ValueError("Support payload must be an object")
    subgroup_status = payload.get("subgroup_support_status", "not_supported")
    timepoint_status = payload.get("timepoint_support_status", "not_supported")
    if subgroup_status not in ALLOWED_SUPPORT_STATUSES:
        subgroup_status = "not_supported"
    if timepoint_status not in ALLOWED_SUPPORT_STATUSES:
        timepoint_status = "not_supported"
    reasons = [reason for reason in payload.get("uncertain_reasons") or [] if reason in ALLOWED_UNCERTAIN_REASONS]
    if subgroup_status != "uncertain" and timepoint_status != "uncertain":
        reasons = []
    if (subgroup_status == "uncertain" or timepoint_status == "uncertain") and not reasons:
        reasons = ["insufficient_evidence"]
    return {
        "subgroup_support_status": subgroup_status,
        "timepoint_support_status": timepoint_status,
    }, {
        "uncertain_reason_count": len(reasons),
        "uncertain_reasons": reasons,
        "empty_prediction_count": 0,
    }


def _sanitize_proposed_items(items: list[dict]) -> tuple[list[dict], dict]:
    sanitized = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        subgroup = normalize_subgroup(item.get("subgroup"))
        timepoints = normalize_timepoints(item.get("timepoints") or [])
        key = (subgroup, timepoints)
        if key in seen:
            continue
        seen.add(key)
        sanitized.append({"subgroup": subgroup, "timepoints": list(timepoints)})
    return sanitized, {"empty_prediction_count": 1 if not sanitized else 0, "predicted_item_count": len(sanitized)}


def _sanitize_proposed_subgroups(values: list[object]) -> list[str | None]:
    sanitized = []
    seen = set()
    for value in values:
        subgroup = normalize_subgroup(value.get("subgroup") if isinstance(value, dict) else value)
        if subgroup in seen:
            continue
        seen.add(subgroup)
        sanitized.append(subgroup)
    return sanitized


def _sanitize_proposed_timepoints(values: list[object]) -> list[str]:
    sanitized = []
    seen = set()
    for value in values:
        timepoint = normalize_timepoint_value(value.get("timepoint") if isinstance(value, dict) else value)
        if not timepoint or timepoint in seen:
            continue
        seen.add(timepoint)
        sanitized.append(timepoint)
    return sanitized


def _merge_split_proposed_items(*, subgroups: list[str | None], timepoints: list[str]) -> tuple[list[dict], dict]:
    normalized_subgroups = [subgroup for subgroup in subgroups if subgroup is not None]
    normalized_timepoints = [timepoint for timepoint in timepoints if timepoint]
    merged = []
    if normalized_subgroups:
        if len(normalized_subgroups) == 1 and normalized_timepoints:
            merged.append({"subgroup": normalized_subgroups[0], "timepoints": normalized_timepoints})
        else:
            for subgroup in normalized_subgroups:
                merged.append({"subgroup": subgroup, "timepoints": []})
    elif normalized_timepoints:
        merged.append({"subgroup": None, "timepoints": normalized_timepoints})
    proposed_items, prediction_stats = _sanitize_proposed_items(merged)
    prediction_stats.update({
        "proposed_subgroup_count": len(normalized_subgroups),
        "proposed_timepoint_count": len(normalized_timepoints),
    })
    return proposed_items, prediction_stats


def _sanitize_rows(rows: list[dict], data_type: str | None) -> tuple[list[dict], dict]:
    allowed = DIRECT_FIELDS_BY_DATA_TYPE.get(data_type or "", [])
    allowed_map = {normalize_text_loose(name): name for name in allowed}
    sanitized_rows = []
    disallowed_field_count = 0
    placeholder_value_count = 0
    partial_row_count = 0
    complete_row_count = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        kept = []
        seen = set()
        for field in row.get("direct_extraction_fields") or []:
            if not isinstance(field, dict):
                continue
            name_key = normalize_text_loose(field.get("field"))
            if name_key not in allowed_map:
                disallowed_field_count += 1
                continue
            value = normalize_text(field.get("value"))
            if normalize_text_loose(value) in PLACEHOLDER_VALUES:
                placeholder_value_count += 1
                continue
            canonical = allowed_map[name_key]
            if canonical in seen:
                continue
            seen.add(canonical)
            kept.append({"field": canonical, "value": value})
        if kept:
            kept.sort(key=lambda field: allowed.index(field["field"]))
            sanitized_rows.append({"direct_extraction_fields": kept})
            if len(kept) == len(allowed) and allowed:
                complete_row_count += 1
            else:
                partial_row_count += 1
    return sanitized_rows, {
        "disallowed_field_count": disallowed_field_count,
        "placeholder_value_count": placeholder_value_count,
        "partial_row_count": partial_row_count,
        "complete_row_count": complete_row_count,
        "empty_prediction_count": 1 if not sanitized_rows else 0,
    }


def _sanitize_routed_items(items: list[dict], data_type: str | None) -> tuple[list[dict], dict]:
    sanitized = []
    seen = set()
    aggregate_stats = {
        "disallowed_field_count": 0,
        "placeholder_value_count": 0,
        "partial_row_count": 0,
        "complete_row_count": 0,
        "empty_prediction_count": 0,
    }
    for item in items:
        if not isinstance(item, dict):
            continue
        subgroup = normalize_subgroup(item.get("subgroup"))
        timepoints = normalize_timepoints(item.get("timepoints") or [])
        rows, row_stats = _sanitize_rows(item.get("predicted_rows") or [], data_type)
        for key in aggregate_stats:
            aggregate_stats[key] += int(row_stats.get(key, 0))
        key = (subgroup, timepoints, tuple(row_key(row) for row in rows))
        if key in seen:
            continue
        seen.add(key)
        sanitized.append({"subgroup": subgroup, "timepoints": list(timepoints), "predicted_rows": rows})
    aggregate_stats["empty_prediction_count"] = 1 if not sanitized else 0
    return sanitized, aggregate_stats


def _parse_rows_payload(payload: Any) -> list[dict]:
    return payload.get("predicted_rows") or [] if isinstance(payload, dict) else []


def _parse_items_payload(payload: Any, field_name: str) -> list[dict]:
    return payload.get(field_name) or [] if isinstance(payload, dict) else []


def _support_target_llm_predict(row: dict, *, prompt_variant: str, target: str) -> tuple[dict, dict, dict]:
    bundle = build_support_prompt_bundle(row, variant=prompt_variant, target=target)
    model = default_model_name()
    text = _llm_text_response(bundle.messages, model=model)
    payload, parse_stats = _parse_with_repair(text=text, model=model)
    if not isinstance(payload, dict):
        raise ValueError("Support payload must be an object")
    status_key = f"{target}_support_status"
    status = payload.get(status_key, "not_supported")
    if status not in ALLOWED_SUPPORT_STATUSES:
        status = "not_supported"
    reasons = [reason for reason in payload.get("uncertain_reasons") or [] if reason in ALLOWED_UNCERTAIN_REASONS]
    if status != "uncertain":
        reasons = []
    if status == "uncertain" and not reasons:
        reasons = ["insufficient_evidence"]
    stats = {
        "uncertain_reason_count": len(reasons),
        "uncertain_reasons": reasons,
        "empty_prediction_count": 0,
        **parse_stats,
    }
    return {status_key: status}, _prediction_metadata(bundle=bundle, mode="llm"), stats


def _support_llm_predict(row: dict, *, prompt_variant: str = DEFAULT_PROMPT_VARIANT) -> dict:
    subgroup_payload, subgroup_meta, subgroup_stats = _support_target_llm_predict(row, prompt_variant=prompt_variant, target="subgroup")
    timepoint_payload, timepoint_meta, timepoint_stats = _support_target_llm_predict(row, prompt_variant=prompt_variant, target="timepoint")
    prediction_stats = {
        "empty_prediction_count": 0,
        "subgroup_uncertain_reason_count": subgroup_stats.get("uncertain_reason_count", 0),
        "timepoint_uncertain_reason_count": timepoint_stats.get("uncertain_reason_count", 0),
        "subgroup_uncertain_reasons": subgroup_stats.get("uncertain_reasons", []),
        "timepoint_uncertain_reasons": timepoint_stats.get("uncertain_reasons", []),
        "json_repair_attempted": subgroup_stats.get("json_repair_attempted", 0) + timepoint_stats.get("json_repair_attempted", 0),
        "json_repair_succeeded": subgroup_stats.get("json_repair_succeeded", 0) + timepoint_stats.get("json_repair_succeeded", 0),
    }
    if subgroup_stats.get("initial_parse_error"):
        prediction_stats["subgroup_initial_parse_error"] = subgroup_stats["initial_parse_error"]
    if timepoint_stats.get("initial_parse_error"):
        prediction_stats["timepoint_initial_parse_error"] = timepoint_stats["initial_parse_error"]
    return {
        **subgroup_payload,
        **timepoint_payload,
        "prediction_metadata": {
            "mode": "llm",
            "model": default_model_name(),
            "prompt_version": PROMPT_VERSION,
            "prompt_name": "support-split:{variant}".format(variant=prompt_variant),
            "subgroup_prompt_name": subgroup_meta.get("prompt_name"),
            "timepoint_prompt_name": timepoint_meta.get("prompt_name"),
            "data_type": subgroup_meta.get("data_type"),
            "context_stats": subgroup_meta.get("context_stats") or {},
            "support_call_mode": "split",
        },
        "prediction_stats": prediction_stats,
    }


def _proposal_target_llm_predict(row: dict, *, prompt_variant: str, target: str) -> tuple[dict, dict, dict]:
    bundle = build_proposal_prompt_bundle(row, variant=prompt_variant, target=target)
    model = default_model_name()
    text = _llm_text_response(bundle.messages, model=model)
    payload, parse_stats = _parse_with_repair(text=text, model=model)
    if not isinstance(payload, dict):
        raise ValueError("Proposal payload must be an object")
    if target == "subgroup":
        proposed_subgroups = _sanitize_proposed_subgroups(payload.get("proposed_subgroups") or [])
        stats = {
            "proposed_subgroup_count": len([subgroup for subgroup in proposed_subgroups if subgroup is not None]),
            "empty_prediction_count": 1 if not proposed_subgroups else 0,
            **parse_stats,
        }
        return {"proposed_subgroups": proposed_subgroups}, _prediction_metadata(bundle=bundle, mode="llm"), stats
    proposed_timepoints = _sanitize_proposed_timepoints(payload.get("proposed_timepoints") or [])
    stats = {
        "proposed_timepoint_count": len(proposed_timepoints),
        "empty_prediction_count": 1 if not proposed_timepoints else 0,
        **parse_stats,
    }
    return {"proposed_timepoints": proposed_timepoints}, _prediction_metadata(bundle=bundle, mode="llm"), stats


def _proposal_llm_predict(row: dict, *, prompt_variant: str = DEFAULT_PROMPT_VARIANT) -> dict:
    if prompt_variant == "negative_examples_split":
        subgroup_payload, subgroup_meta, subgroup_stats = _proposal_target_llm_predict(row, prompt_variant=prompt_variant, target="subgroup")
        timepoint_payload, timepoint_meta, timepoint_stats = _proposal_target_llm_predict(row, prompt_variant=prompt_variant, target="timepoint")
        proposed_items, prediction_stats = _merge_split_proposed_items(
            subgroups=subgroup_payload.get("proposed_subgroups") or [],
            timepoints=timepoint_payload.get("proposed_timepoints") or [],
        )
        prediction_stats.update({
            "json_repair_attempted": subgroup_stats.get("json_repair_attempted", 0) + timepoint_stats.get("json_repair_attempted", 0),
            "json_repair_succeeded": subgroup_stats.get("json_repair_succeeded", 0) + timepoint_stats.get("json_repair_succeeded", 0),
        })
        if subgroup_stats.get("initial_parse_error"):
            prediction_stats["subgroup_initial_parse_error"] = subgroup_stats["initial_parse_error"]
        if timepoint_stats.get("initial_parse_error"):
            prediction_stats["timepoint_initial_parse_error"] = timepoint_stats["initial_parse_error"]
        return {
            "proposed_items": proposed_items,
            "prediction_metadata": {
                "mode": "llm",
                "model": default_model_name(),
                "prompt_version": PROMPT_VERSION,
                "prompt_name": "proposal-split:{variant}".format(variant=prompt_variant),
                "subgroup_prompt_name": subgroup_meta.get("prompt_name"),
                "timepoint_prompt_name": timepoint_meta.get("prompt_name"),
                "data_type": subgroup_meta.get("data_type"),
                "context_stats": subgroup_meta.get("context_stats") or {},
                "proposal_call_mode": "split",
            },
            "prediction_stats": prediction_stats,
        }
    bundle = build_proposal_prompt_bundle(row, variant=prompt_variant)
    model = default_model_name()
    text = _llm_text_response(bundle.messages, model=model)
    payload, parse_stats = _parse_with_repair(text=text, model=model)
    proposed_items, prediction_stats = _sanitize_proposed_items(_parse_items_payload(payload, "proposed_items"))
    prediction_stats.update(parse_stats)
    return {"proposed_items": proposed_items, "prediction_metadata": _prediction_metadata(bundle=bundle, mode="llm"), "prediction_stats": prediction_stats}


def _oracle_extraction_llm_predict(row: dict, *, prompt_variant: str = DEFAULT_PROMPT_VARIANT) -> dict:
    bundle = build_oracle_extraction_prompt_bundle(row, variant=prompt_variant)
    model = default_model_name()
    text = _llm_text_response(bundle.messages, model=model)
    payload, parse_stats = _parse_with_repair(text=text, model=model)
    predicted_rows, prediction_stats = _sanitize_rows(_parse_rows_payload(payload), bundle.data_type)
    prediction_stats.update(parse_stats)
    return {"predicted_rows": predicted_rows, "prediction_metadata": _prediction_metadata(bundle=bundle, mode="llm"), "prediction_stats": prediction_stats}


def _routed_extraction_llm_predict(row: dict, *, prompt_variant: str = DEFAULT_PROMPT_VARIANT) -> dict:
    bundle = build_routed_extraction_prompt_bundle(row, variant=prompt_variant)
    model = default_model_name()
    text = _llm_text_response(bundle.messages, model=model)
    payload, parse_stats = _parse_with_repair(text=text, model=model)
    predicted_items, prediction_stats = _sanitize_routed_items(_parse_items_payload(payload, "predicted_items"), bundle.data_type)
    prediction_stats.update(parse_stats)
    return {"predicted_items": predicted_items, "prediction_metadata": _prediction_metadata(bundle=bundle, mode="llm"), "prediction_stats": prediction_stats}


def _safe_llm_call(fn, row: dict, *, empty_payload: dict, prompt_variant: str) -> dict:
    try:
        return fn(row, prompt_variant=prompt_variant)
    except Exception as exc:
        return {
            **empty_payload,
            "prediction_metadata": {"mode": "llm", "model": default_model_name(), "prompt_version": PROMPT_VERSION},
            "prediction_stats": {"parse_error": repr(exc), "empty_prediction_count": 1},
        }


def _support_predict_row(row: dict, mode: str, *, prompt_variant: str) -> dict:
    if mode == "oracle":
        payload = {
            "subgroup_support_status": row["gold_support"]["subgroup_support_status"],
            "timepoint_support_status": row["gold_support"]["timepoint_support_status"],
            "prediction_metadata": {"mode": mode, "model": None, "prompt_version": PROMPT_VERSION},
            "prediction_stats": {"empty_prediction_count": 0},
        }
    elif mode == "empty":
        payload = {
            "subgroup_support_status": "not_supported",
            "timepoint_support_status": "not_supported",
            "prediction_metadata": {"mode": mode, "model": None, "prompt_version": PROMPT_VERSION},
            "prediction_stats": {"empty_prediction_count": 1},
        }
    elif mode == "llm":
        payload = _safe_llm_call(
            _support_llm_predict,
            row,
            empty_payload={"subgroup_support_status": "not_supported", "timepoint_support_status": "not_supported"},
            prompt_variant=prompt_variant,
        )
    else:
        raise ValueError(f"Unsupported support mode: {mode}")
    return {
        "instance_id": row["instance_id"],
        "split": row["split"],
        "task_name": SUPPORT_TASK,
        **payload,
    }


def _proposal_predict_row(row: dict, mode: str, *, prompt_variant: str) -> dict:
    if mode == "oracle":
        proposed_items, prediction_stats = _sanitize_proposed_items(row.get("gold_items") or [])
        payload = {"proposed_items": proposed_items, "prediction_metadata": {"mode": mode, "model": None, "prompt_version": PROMPT_VERSION}, "prediction_stats": prediction_stats}
    elif mode == "empty":
        payload = {"proposed_items": [], "prediction_metadata": {"mode": mode, "model": None, "prompt_version": PROMPT_VERSION}, "prediction_stats": {"empty_prediction_count": 1}}
    elif mode == "llm":
        payload = _safe_llm_call(_proposal_llm_predict, row, empty_payload={"proposed_items": []}, prompt_variant=prompt_variant)
    else:
        raise ValueError(f"Unsupported proposal mode: {mode}")
    return {"instance_id": row["instance_id"], "split": row["split"], "task_name": PROPOSAL_TASK, **payload}


def _oracle_extraction_predict_row(row: dict, mode: str, *, prompt_variant: str) -> dict:
    if mode == "oracle":
        predicted_rows, prediction_stats = _sanitize_rows(row.get("gold_extraction_rows") or [], row.get("setting_context", {}).get("data_type"))
        payload = {"predicted_rows": predicted_rows, "prediction_metadata": {"mode": mode, "model": None, "prompt_version": PROMPT_VERSION}, "prediction_stats": prediction_stats}
    elif mode == "empty":
        payload = {"predicted_rows": [], "prediction_metadata": {"mode": mode, "model": None, "prompt_version": PROMPT_VERSION}, "prediction_stats": {"empty_prediction_count": 1}}
    elif mode == "llm":
        payload = _safe_llm_call(_oracle_extraction_llm_predict, row, empty_payload={"predicted_rows": []}, prompt_variant=prompt_variant)
    else:
        raise ValueError(f"Unsupported oracle extraction mode: {mode}")
    return {
        "instance_id": row["instance_id"],
        "parent_setting_instance_id": row.get("parent_setting_instance_id"),
        "split": row["split"],
        "task_name": ORACLE_EXTRACTION_TASK,
        **payload,
    }


def _routed_extraction_predict_row(row: dict, mode: str, *, prompt_variant: str) -> dict:
    if mode == "oracle":
        predicted_items = []
        for item in row.get("gold_items") or []:
            predicted_rows, _ = _sanitize_rows(item.get("gold_extraction_rows") or [], row.get("setting_context", {}).get("data_type"))
            predicted_items.append({"subgroup": normalize_subgroup(item.get("subgroup")), "timepoints": list(normalize_timepoints(item.get("timepoints") or [])), "predicted_rows": predicted_rows})
        payload = {"predicted_items": predicted_items, "prediction_metadata": {"mode": mode, "model": None, "prompt_version": PROMPT_VERSION}, "prediction_stats": {"empty_prediction_count": 1 if not predicted_items else 0}}
    elif mode == "empty":
        payload = {"predicted_items": [], "prediction_metadata": {"mode": mode, "model": None, "prompt_version": PROMPT_VERSION}, "prediction_stats": {"empty_prediction_count": 1}}
    elif mode == "llm":
        payload = _safe_llm_call(_routed_extraction_llm_predict, row, empty_payload={"predicted_items": []}, prompt_variant=prompt_variant)
    else:
        raise ValueError(f"Unsupported routed extraction mode: {mode}")
    return {"instance_id": row["instance_id"], "split": row["split"], "task_name": ROUTED_EXTRACTION_TASK, **payload}


def _write_run_manifest(*, task_name: str, run_dir: str | Path, metadata: dict) -> None:
    manifest_path = Path(run_dir) / "manifests" / f"{task_name}_run_manifest.json"
    write_manifest(manifest_path, {"task_name": task_name, **metadata})


def _run_task(*, task_name: str, instances_path: str | Path, run_dir: str | Path, split: str | None, mode: str, prompt_variant: str, num_workers: int, resume: bool, flush_every: int, continue_on_error: bool, max_attempts: int, show_progress: bool, predict_row_fn) -> dict:
    rows = _load_rows(instances_path, split)
    task_paths = resolve_task_paths(task_name=task_name, run_dir=run_dir)
    run_metadata = {
        "mode": mode,
        "prompt_variant": prompt_variant,
        "split": split,
        "started_at": utc_now_iso(),
        "task_label": task_name,
        "instance_count": len(rows),
    }
    _write_run_manifest(task_name=task_name, run_dir=run_dir, metadata={**run_metadata, "instances_path": str(instances_path)})
    summary = execute_task_run(
        task_name=task_name,
        rows=rows,
        run_dir=run_dir,
        predict_fn=lambda row: predict_row_fn(row, mode, prompt_variant=prompt_variant),
        run_metadata=run_metadata,
        num_workers=num_workers,
        resume=resume,
        flush_every=flush_every,
        continue_on_error=continue_on_error,
        max_attempts=max_attempts,
        show_progress=show_progress,
        instance_source_path=instances_path,
    )
    write_json(Path(run_dir) / "manifests" / f"{task_name}_task_config.json", {"task_name": task_name, "mode": mode, "prompt_variant": prompt_variant, "split": split})
    return summary


def run_support(*, instances_path: str | Path, run_dir: str | Path, split: str | None = None, mode: str = "oracle", prompt_variant: str = DEFAULT_PROMPT_VARIANT, num_workers: int = 1, resume: bool = False, flush_every: int = 1, continue_on_error: bool = True, max_attempts: int = 1, show_progress: bool = True) -> dict:
    return _run_task(task_name=SUPPORT_TASK, instances_path=instances_path, run_dir=run_dir, split=split, mode=mode, prompt_variant=prompt_variant, num_workers=num_workers, resume=resume, flush_every=flush_every, continue_on_error=continue_on_error, max_attempts=max_attempts, show_progress=show_progress, predict_row_fn=_support_predict_row)


def run_proposal(*, instances_path: str | Path, run_dir: str | Path, split: str | None = None, mode: str = "oracle", prompt_variant: str = DEFAULT_PROMPT_VARIANT, num_workers: int = 1, resume: bool = False, flush_every: int = 1, continue_on_error: bool = True, max_attempts: int = 1, show_progress: bool = True) -> dict:
    return _run_task(task_name=PROPOSAL_TASK, instances_path=instances_path, run_dir=run_dir, split=split, mode=mode, prompt_variant=prompt_variant, num_workers=num_workers, resume=resume, flush_every=flush_every, continue_on_error=continue_on_error, max_attempts=max_attempts, show_progress=show_progress, predict_row_fn=_proposal_predict_row)


def run_oracle_extraction(*, instances_path: str | Path, run_dir: str | Path, split: str | None = None, mode: str = "oracle", prompt_variant: str = DEFAULT_PROMPT_VARIANT, num_workers: int = 1, resume: bool = False, flush_every: int = 1, continue_on_error: bool = True, max_attempts: int = 1, show_progress: bool = True) -> dict:
    return _run_task(task_name=ORACLE_EXTRACTION_TASK, instances_path=instances_path, run_dir=run_dir, split=split, mode=mode, prompt_variant=prompt_variant, num_workers=num_workers, resume=resume, flush_every=flush_every, continue_on_error=continue_on_error, max_attempts=max_attempts, show_progress=show_progress, predict_row_fn=_oracle_extraction_predict_row)


def run_routed_extraction(*, instances_path: str | Path, run_dir: str | Path, split: str | None = None, mode: str = "oracle", prompt_variant: str = DEFAULT_PROMPT_VARIANT, num_workers: int = 1, resume: bool = False, flush_every: int = 1, continue_on_error: bool = True, max_attempts: int = 1, show_progress: bool = True) -> dict:
    return _run_task(task_name=ROUTED_EXTRACTION_TASK, instances_path=instances_path, run_dir=run_dir, split=split, mode=mode, prompt_variant=prompt_variant, num_workers=num_workers, resume=resume, flush_every=flush_every, continue_on_error=continue_on_error, max_attempts=max_attempts, show_progress=show_progress, predict_row_fn=_routed_extraction_predict_row)


def rerun_failures(*, task_name: str, run_dir: str | Path, mode: str = "oracle", prompt_variant: str = DEFAULT_PROMPT_VARIANT, num_workers: int = 1, flush_every: int = 1, continue_on_error: bool = True, max_attempts: int = 1, show_progress: bool = True) -> dict:
    task_paths = resolve_task_paths(task_name=task_name, run_dir=run_dir)
    failed_rows = list(iter_jsonl(task_paths.failed_instances_path) or [])
    failed_ids = {row.get("instance_id") for row in failed_rows if row.get("instance_id")}
    source_rows = [row for row in iter_jsonl(task_paths.instances_path) or [] if row.get("instance_id") in failed_ids]
    task_paths.failed_instances_path.write_text("", encoding="utf-8")
    predict_fn_map = {
        SUPPORT_TASK: _support_predict_row,
        PROPOSAL_TASK: _proposal_predict_row,
        ORACLE_EXTRACTION_TASK: _oracle_extraction_predict_row,
        ROUTED_EXTRACTION_TASK: _routed_extraction_predict_row,
    }
    return execute_task_run(
        task_name=task_name,
        rows=source_rows,
        run_dir=run_dir,
        predict_fn=lambda row: predict_fn_map[task_name](row, mode, prompt_variant=prompt_variant),
        run_metadata={"mode": mode, "prompt_variant": prompt_variant, "rerun_failures": True, "started_at": utc_now_iso()},
        num_workers=num_workers,
        resume=True,
        flush_every=flush_every,
        continue_on_error=continue_on_error,
        max_attempts=max_attempts,
        show_progress=show_progress,
        instance_source_path=task_paths.instances_path,
    )
