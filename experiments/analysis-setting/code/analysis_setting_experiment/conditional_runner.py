from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .conditional_constants import CONDITIONAL_PROMPT_VERSION
from .conditional_experiment import (
    DEFAULT_DECISION_STRATEGY,
    DEFAULT_EVIDENCE_STRATEGY,
    conditional_result_variant,
    resolve_effect_measure_decision_strategy,
    resolve_effect_measure_evidence_strategy,
)
from .conditional_parsing import parse_conditional_prediction
from .conditional_prompting import build_conditional_prompt
from .io_utils import dump_json, load_json, load_jsonl
from .runner import (
    CANONICALIZATION_VERSION,
    ModelBackend,
    OpenAIResponsesBackend,
    RunConfig,
    _initial_state,
    _lock_for,
    _render_progress_bar,
    utc_now,
)



def _config_evidence_strategy(config: RunConfig, task_name: str) -> str:
    return resolve_effect_measure_evidence_strategy(task_name, getattr(config, "evidence_strategy", ""))



def _config_decision_strategy(config: RunConfig, task_name: str) -> str:
    return resolve_effect_measure_decision_strategy(task_name, getattr(config, "decision_strategy", ""))



def _config_few_shot_set(config: RunConfig) -> str:
    return (getattr(config, "few_shot_set", "") or "").strip()



def conditional_run_root(config: RunConfig, *, task_name: str, evidence_mode: str) -> Path:
    root = config.output_dir / "runs" / config.model_name / config.split / task_name / evidence_mode
    variant = conditional_result_variant(
        task_name,
        evidence_strategy=_config_evidence_strategy(config, task_name),
        decision_strategy=_config_decision_strategy(config, task_name),
        few_shot_set=_config_few_shot_set(config),
        prompt_version=getattr(config, "prompt_version", "") or None,
    )
    if variant:
        root = root / variant
    return root



def conditional_instance_dir(config: RunConfig, instance: dict[str, Any]) -> Path:
    return conditional_run_root(config, task_name=instance["task_name"], evidence_mode=instance["evidence_mode"]) / instance["instance_id"]



def conditional_state_path(config: RunConfig, instance: dict[str, Any]) -> Path:
    return conditional_instance_dir(config, instance) / "state.json"



def conditional_latest_prediction_path(config: RunConfig, instance: dict[str, Any]) -> Path:
    return conditional_instance_dir(config, instance) / "latest_prediction.json"



def conditional_prediction_root(
    output_dir: Path,
    model_name: str,
    split: str,
    task_name: str,
    evidence_mode: str,
    *,
    evidence_strategy: str,
    decision_strategy: str,
    few_shot_set: str | None,
    prompt_version: str | None = None,
) -> Path:
    root = output_dir / "runs" / model_name / split / task_name / evidence_mode
    variant = conditional_result_variant(
        task_name,
        evidence_strategy=evidence_strategy,
        decision_strategy=decision_strategy,
        few_shot_set=few_shot_set,
        prompt_version=prompt_version,
    )
    if variant:
        root = root / variant
    return root



def _conditional_write_attempt_artifacts(
    config: RunConfig,
    instance: dict[str, Any],
    attempt_id: str,
    payload: dict[str, Any],
) -> None:
    attempt_dir = conditional_instance_dir(config, instance) / "attempts" / attempt_id
    dump_json(attempt_dir / "prediction.json", payload)



def _latest_attempt_id(state: dict[str, Any]) -> str:
    return f"attempt_{state.get('attempt_count', 0):03d}"



def _initial_conditional_state(config: RunConfig, instance: dict[str, Any]) -> dict[str, Any]:
    base = _initial_state(config, instance["instance_id"])
    base["instance_id"] = instance["instance_id"]
    base["review_id"] = instance["review_id"]
    base["task_name"] = instance["task_name"]
    base["evidence_mode"] = instance["evidence_mode"]
    base["prompt_version"] = getattr(config, "prompt_version", "") or CONDITIONAL_PROMPT_VERSION
    base["evidence_strategy"] = _config_evidence_strategy(config, instance["task_name"])
    base["decision_strategy"] = _config_decision_strategy(config, instance["task_name"])
    base["few_shot_set"] = _config_few_shot_set(config)
    return base



def _load_instance_state(config: RunConfig, instance: dict[str, Any]) -> dict[str, Any] | None:
    path = conditional_state_path(config, instance)
    if not path.exists():
        return None
    return load_json(path)



def _save_instance_state(config: RunConfig, instance: dict[str, Any], state: dict[str, Any]) -> None:
    dump_json(conditional_state_path(config, instance), state)



def should_run_instance(config: RunConfig, instance: dict[str, Any], existing_state: dict[str, Any] | None) -> bool:
    if config.review_ids and instance["review_id"] not in config.review_ids:
        return False
    if existing_state is None:
        return True
    status = existing_state.get("status", "")
    if status == "success":
        if config.rerun_empty_output and existing_state.get("last_non_empty_output") is False:
            return True
        return instance["review_id"] in config.review_ids
    if status == "failed":
        return config.rerun_failed or instance["review_id"] in config.review_ids
    if status == "invalid_output":
        return config.rerun_invalid_output or instance["review_id"] in config.review_ids
    return True



def run_single_instance(config: RunConfig, instance: dict[str, Any], backend: ModelBackend) -> dict[str, Any]:
    lock = _lock_for(conditional_state_path(config, instance))
    with lock:
        state = _load_instance_state(config, instance) or _initial_conditional_state(config, instance)
        state["attempt_count"] = int(state.get("attempt_count", 0)) + 1
        state["status"] = "running"
        state["started_at"] = utc_now()
        state["finished_at"] = ""
        _save_instance_state(config, instance, state)
    attempt_id = _latest_attempt_id(state)
    prompt_version = getattr(config, "prompt_version", "") or None
    evidence_strategy = _config_evidence_strategy(config, instance["task_name"])
    decision_strategy = _config_decision_strategy(config, instance["task_name"])
    few_shot_set = _config_few_shot_set(config)
    prompt = build_conditional_prompt(
        instance,
        prompt_version=prompt_version,
        evidence_strategy=evidence_strategy,
        decision_strategy=decision_strategy,
        few_shot_set=few_shot_set,
    )
    raw_output = ""
    parsed: dict[str, Any] = {}
    last_error = ""
    for attempt_index in range(config.max_retries + 1):
        try:
            raw_output = backend.generate(prompt, instance, config)
            parsed = parse_conditional_prediction(instance["task_name"], raw_output)
            break
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            if attempt_index >= config.max_retries:
                parsed = {
                    "parse_status": "failed",
                    "schema_valid": False,
                    "parsed_prediction_json": {},
                    "error": last_error,
                }
    payload = {
        "instance_id": instance["instance_id"],
        "review_id": instance["review_id"],
        "task_name": instance["task_name"],
        "evidence_mode": instance["evidence_mode"],
        "evidence_strategy": evidence_strategy,
        "decision_strategy": decision_strategy,
        "few_shot_set": few_shot_set,
        "raw_model_output": raw_output,
        "parsed_prediction_json": parsed.get("parsed_prediction_json", {}),
        "parse_status": parsed.get("parse_status", "failed"),
        "schema_valid": parsed.get("schema_valid", False),
        "attempt_id": attempt_id,
        "prompt_version": getattr(config, "prompt_version", "") or CONDITIONAL_PROMPT_VERSION,
        "canonicalization_version": CANONICALIZATION_VERSION,
        "model_name": config.model_name,
        "model_version": config.model_version,
        "split": config.split,
        "created_at": utc_now(),
        "error": parsed.get("error", last_error),
    }
    _conditional_write_attempt_artifacts(config, instance, attempt_id, payload)
    dump_json(conditional_latest_prediction_path(config, instance), payload)
    with lock:
        state = _load_instance_state(config, instance) or _initial_conditional_state(config, instance)
        state["finished_at"] = utc_now()
        state["last_error"] = payload["error"]
        state["last_non_empty_output"] = bool(payload["parsed_prediction_json"])
        if payload["parse_status"] == "success":
            state["status"] = "success"
        elif payload["parse_status"] == "invalid_output":
            state["status"] = "invalid_output"
        else:
            state["status"] = "failed"
        _save_instance_state(config, instance, state)
    return state



def _collect_instance_status_counts(config: RunConfig, instances: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "pending": 0,
        "running": 0,
        "success": 0,
        "failed": 0,
        "invalid_output": 0,
    }
    for instance in instances:
        state = _load_instance_state(config, instance)
        status = (state or {}).get("status", "pending")
        counts[status] = counts.get(status, 0) + 1
    return counts



def _write_conditional_progress(
    config: RunConfig,
    *,
    task_name: str,
    evidence_mode: str,
    dataset_instance_count: int,
    scheduled_instance_count: int,
    completed_instance_count: int,
    status_counts: dict[str, int],
    started_at: str,
    finished_at: str = "",
) -> dict[str, Any]:
    payload = {
        "model_name": config.model_name,
        "model_version": config.model_version,
        "split": config.split,
        "task_name": task_name,
        "evidence_mode": evidence_mode,
        "evidence_strategy": _config_evidence_strategy(config, task_name),
        "decision_strategy": _config_decision_strategy(config, task_name),
        "few_shot_set": _config_few_shot_set(config),
        "dataset_instance_count": dataset_instance_count,
        "scheduled_instance_count": scheduled_instance_count,
        "completed_instance_count": completed_instance_count,
        "remaining_instance_count": max(scheduled_instance_count - completed_instance_count, 0),
        "status_counts": status_counts,
        "concurrency": config.concurrency,
        "started_at": started_at,
        "updated_at": utc_now(),
        "finished_at": finished_at,
    }
    dump_json(conditional_run_root(config, task_name=task_name, evidence_mode=evidence_mode) / "progress.json", payload)
    return payload


class ConditionalMockBackend(ModelBackend):
    def generate(self, prompt: str, review: dict[str, Any], config: RunConfig) -> str:
        return json.dumps(review.get("gold_target", {}), ensure_ascii=False)


class ConditionalJsonFileBackend(ModelBackend):
    def __init__(self, source_path: Path) -> None:
        self._cache = load_json(source_path)

    def generate(self, prompt: str, review: dict[str, Any], config: RunConfig) -> str:
        instance_id = review.get("instance_id", "")
        review_id = review.get("review_id", "")
        value = self._cache.get(instance_id)
        if value is None:
            value = self._cache.get(review_id, {})
        return json.dumps(value, ensure_ascii=False)



def build_conditional_backend(kind: str, *, json_source: Path | None = None) -> ModelBackend:
    if kind == "mock":
        return ConditionalMockBackend()
    if kind == "json_file":
        if json_source is None:
            raise ValueError("json_source is required for json_file backend")
        return ConditionalJsonFileBackend(json_source)
    if kind == "openai":
        return OpenAIResponsesBackend()
    raise ValueError(f"unknown_backend:{kind}")



def run_conditional_split(
    dataset_path: Path,
    config: RunConfig,
    backend: ModelBackend,
    *,
    task_name: str,
    evidence_mode: str,
) -> dict[str, Any]:
    instances = [row for row in load_jsonl(dataset_path) if row["task_name"] == task_name and row["evidence_mode"] == evidence_mode]
    selected: list[dict[str, Any]] = []
    for instance in instances:
        state = _load_instance_state(config, instance)
        if should_run_instance(config, instance, state):
            selected.append(instance)
    started_at = utc_now()
    status_counts = _collect_instance_status_counts(config, instances)
    _write_conditional_progress(
        config,
        task_name=task_name,
        evidence_mode=evidence_mode,
        dataset_instance_count=len(instances),
        scheduled_instance_count=len(selected),
        completed_instance_count=0,
        status_counts=status_counts,
        started_at=started_at,
    )
    if not selected:
        summary = {
            "model_name": config.model_name,
            "model_version": config.model_version,
            "split": config.split,
            "task_name": task_name,
            "evidence_mode": evidence_mode,
            "evidence_strategy": _config_evidence_strategy(config, task_name),
            "decision_strategy": _config_decision_strategy(config, task_name),
            "few_shot_set": _config_few_shot_set(config),
            "prompt_version": getattr(config, "prompt_version", "") or CONDITIONAL_PROMPT_VERSION,
            "scheduled_instance_count": 0,
            "completed_at": utc_now(),
            "concurrency": config.concurrency,
        }
        dump_json(conditional_run_root(config, task_name=task_name, evidence_mode=evidence_mode) / "run_summary.json", summary)
        return summary

    from concurrent.futures import ThreadPoolExecutor, as_completed

    completed = 0
    with ThreadPoolExecutor(max_workers=config.concurrency) as executor:
        futures = [executor.submit(run_single_instance, config, instance, backend) for instance in selected]
        for future in as_completed(futures):
            state = future.result()
            completed += 1
            status = state.get("status", "pending")
            status_counts[status] = status_counts.get(status, 0) + 1
            progress = _write_conditional_progress(
                config,
                task_name=task_name,
                evidence_mode=evidence_mode,
                dataset_instance_count=len(instances),
                scheduled_instance_count=len(selected),
                completed_instance_count=completed,
                status_counts=status_counts,
                started_at=started_at,
            )
            bar = _render_progress_bar(completed, len(selected))
            print(
                f"{bar} {completed}/{len(selected)} | success={progress['status_counts'].get('success', 0)} "
                f"failed={progress['status_counts'].get('failed', 0)} "
                f"invalid={progress['status_counts'].get('invalid_output', 0)}",
                flush=True,
            )
    summary = {
        "model_name": config.model_name,
        "model_version": config.model_version,
        "split": config.split,
        "task_name": task_name,
        "evidence_mode": evidence_mode,
        "evidence_strategy": _config_evidence_strategy(config, task_name),
        "decision_strategy": _config_decision_strategy(config, task_name),
        "few_shot_set": _config_few_shot_set(config),
        "prompt_version": getattr(config, "prompt_version", "") or CONDITIONAL_PROMPT_VERSION,
        "scheduled_instance_count": len(selected),
        "completed_at": utc_now(),
        "concurrency": config.concurrency,
    }
    dump_json(conditional_run_root(config, task_name=task_name, evidence_mode=evidence_mode) / "run_summary.json", summary)
    _write_conditional_progress(
        config,
        task_name=task_name,
        evidence_mode=evidence_mode,
        dataset_instance_count=len(instances),
        scheduled_instance_count=len(selected),
        completed_instance_count=len(selected),
        status_counts=_collect_instance_status_counts(config, instances),
        started_at=started_at,
        finished_at=summary["completed_at"],
    )
    return summary



def load_conditional_prediction_or_empty(
    output_dir: Path,
    model_name: str,
    split: str,
    task_name: str,
    evidence_mode: str,
    instance_id: str,
    *,
    evidence_strategy: str = DEFAULT_EVIDENCE_STRATEGY,
    decision_strategy: str = DEFAULT_DECISION_STRATEGY,
    few_shot_set: str | None = None,
    prompt_version: str | None = None,
) -> dict[str, Any]:
    candidate_paths = [
        conditional_prediction_root(
            output_dir,
            model_name,
            split,
            task_name,
            evidence_mode,
            evidence_strategy=evidence_strategy,
            decision_strategy=decision_strategy,
            few_shot_set=few_shot_set,
            prompt_version=prompt_version,
        )
        / instance_id
        / "latest_prediction.json"
    ]
    legacy_path = output_dir / "runs" / model_name / split / task_name / evidence_mode / instance_id / "latest_prediction.json"
    if legacy_path not in candidate_paths:
        candidate_paths.append(legacy_path)
    for path in candidate_paths:
        if path.exists():
            return load_json(path)
    return {
        "parsed_prediction_json": {},
        "schema_valid": False,
        "parse_status": "missing_prediction",
        "error": "missing_prediction",
    }
