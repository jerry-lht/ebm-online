from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .canonicalization import CANONICALIZATION_VERSION, canonicalize_predictions_with_provenance
from .constants import DEFAULT_MATCH_THRESHOLD, PROMPT_VERSION, SPLIT_VERSION
from .io_utils import dump_json, load_json, load_jsonl
from .parsing import parse_prediction
from .prompting import build_prompt


_LOCAL_API_CONFIG_FILENAMES = (
    "analysis_setting.local.json",
    "analysis_setting.local.example.json",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RunConfig:
    model_name: str
    model_version: str
    split: str
    output_dir: Path
    api_key: str = ""
    base_url: str = ""
    max_retries: int = 0
    timeout_seconds: int = 120
    concurrency: int = 4
    max_output_tokens: int = 4000
    rerun_failed: bool = False
    rerun_invalid_output: bool = False
    rerun_empty_output: bool = False
    review_ids: tuple[str, ...] = ()
    parse_tolerance_mode: str = "strict"
    match_threshold: float = DEFAULT_MATCH_THRESHOLD


class ModelBackend:
    def generate(self, prompt: str, review: dict[str, Any], config: RunConfig) -> str:  # pragma: no cover - interface
        raise NotImplementedError


class MockBackend(ModelBackend):
    def generate(self, prompt: str, review: dict[str, Any], config: RunConfig) -> str:
        candidates = []
        for outcome in review.get("sr_pico", {}).get("outcome", [])[:2]:
            candidates.append(
                {
                    "outcome_concept": outcome,
                    "data_type": "",
                    "candidate_effect_measure": "",
                    "comparisons": [],
                    "arm_pairs": [],
                    "subgroup_candidates": [],
                    "timepoints": [],
                    "reported_outcome_measures": [],
                }
            )
        return json.dumps(candidates, ensure_ascii=False)


class JsonFileBackend(ModelBackend):
    def __init__(self, source_path: Path) -> None:
        self.source_path = source_path
        self._cache = load_json(source_path)

    def generate(self, prompt: str, review: dict[str, Any], config: RunConfig) -> str:
        review_id = review["review_id"]
        value = self._cache.get(review_id, [])
        return json.dumps(value, ensure_ascii=False)



def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]



def _load_local_api_config() -> dict[str, str]:
    root = _repo_root()
    for filename in _LOCAL_API_CONFIG_FILENAMES:
        path = root / filename
        if not path.exists() or filename.endswith(".example.json"):
            continue
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise RuntimeError(f"invalid_local_api_config:{path}")
        api_key = str(payload.get("api_key", "")).strip()
        base_url = str(payload.get("base_url", "")).strip()
        model = str(payload.get("model", "")).strip()
        return {
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
        }
    return {
        "api_key": "",
        "base_url": "",
        "model": "",
    }



def _resolve_openai_credentials(config: RunConfig) -> tuple[str, str]:
    local_config = _load_local_api_config()
    api_key = local_config["api_key"] or config.api_key or os.environ.get("OPENAI_API_KEY", "")
    base_url = (
        local_config["base_url"]
        or config.base_url
        or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    ).rstrip("/")
    return api_key, base_url


class OpenAIResponsesBackend(ModelBackend):
    def _post_json(self, url: str, payload: dict[str, Any], api_key: str, timeout_seconds: int) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "curl/8.5.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def _extract_responses_text(self, body: dict[str, Any]) -> str:
        text_parts: list[str] = []
        for item in body.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    text_parts.append(content.get("text", ""))
        return "".join(text_parts).strip()

    def _extract_chat_text(self, body: dict[str, Any]) -> str:
        choices = body.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
            return "".join(parts).strip()
        return ""

    def generate(self, prompt: str, review: dict[str, Any], config: RunConfig) -> str:
        api_key, base_url = _resolve_openai_credentials(config)
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        responses_payload = {
            "model": config.model_name,
            "input": prompt,
            "temperature": 0,
            "top_p": 1,
            "max_output_tokens": config.max_output_tokens,
        }
        try:
            body = self._post_json(f"{base_url}/responses", responses_payload, api_key, config.timeout_seconds)
            text = self._extract_responses_text(body)
            if text:
                return text
        except urllib.error.HTTPError as exc:  # noqa: PERF203
            details = exc.read().decode("utf-8", errors="ignore")
            if exc.code not in {400, 404, 405, 422, 501}:
                raise RuntimeError(f"http_error:{exc.code}:{details}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"network_error:{exc.reason}") from exc

        chat_payload = {
            "model": config.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "top_p": 1,
            "max_tokens": config.max_output_tokens,
        }
        try:
            body = self._post_json(f"{base_url}/chat/completions", chat_payload, api_key, config.timeout_seconds)
        except urllib.error.HTTPError as exc:  # noqa: PERF203
            details = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"http_error:{exc.code}:{details}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"network_error:{exc.reason}") from exc
        text = self._extract_chat_text(body)
        if not text:
            raise RuntimeError("empty_openai_response_text")
        return text


def build_backend(kind: str, *, json_source: Path | None = None) -> ModelBackend:
    if kind == "mock":
        return MockBackend()
    if kind == "json_file":
        if json_source is None:
            raise ValueError("json_source is required for json_file backend")
        return JsonFileBackend(json_source)
    if kind == "openai":
        return OpenAIResponsesBackend()
    raise ValueError(f"unknown_backend:{kind}")


def run_root(config: RunConfig) -> Path:
    return config.output_dir / "runs" / config.model_name / config.split


def review_dir(config: RunConfig, review_id: str) -> Path:
    return run_root(config) / review_id


def state_path(config: RunConfig, review_id: str) -> Path:
    return review_dir(config, review_id) / "state.json"


def latest_prediction_path(config: RunConfig, review_id: str) -> Path:
    return review_dir(config, review_id) / "latest_prediction.json"


def latest_attempt_id(state: dict[str, Any]) -> str:
    return f"attempt_{state.get('attempt_count', 0):03d}"


_STATE_LOCKS: dict[str, threading.Lock] = {}


def _lock_for(path: Path) -> threading.Lock:
    key = str(path)
    if key not in _STATE_LOCKS:
        _STATE_LOCKS[key] = threading.Lock()
    return _STATE_LOCKS[key]


def should_run_review(config: RunConfig, review: dict[str, Any], existing_state: dict[str, Any] | None) -> bool:
    review_id = review["review_id"]
    if config.review_ids and review_id not in config.review_ids:
        return False
    if existing_state is None:
        return True
    status = existing_state.get("status", "")
    if status == "success":
        if config.rerun_empty_output and existing_state.get("last_non_empty_output") is False:
            return True
        return review_id in config.review_ids
    if status == "failed":
        return config.rerun_failed or review_id in config.review_ids
    if status == "invalid_output":
        return config.rerun_invalid_output or review_id in config.review_ids
    return True


def _initial_state(config: RunConfig, review_id: str) -> dict[str, Any]:
    return {
        "review_id": review_id,
        "model_name": config.model_name,
        "model_version": config.model_version,
        "split": config.split,
        "status": "pending",
        "attempt_count": 0,
        "last_error": "",
        "started_at": "",
        "finished_at": "",
        "prompt_version": PROMPT_VERSION,
        "split_version": SPLIT_VERSION,
        "last_non_empty_output": None,
    }


def load_state(config: RunConfig, review_id: str) -> dict[str, Any] | None:
    path = state_path(config, review_id)
    if not path.exists():
        return None
    return load_json(path)


def save_state(config: RunConfig, review_id: str, state: dict[str, Any]) -> None:
    dump_json(state_path(config, review_id), state)


def _write_attempt_artifacts(config: RunConfig, review_id: str, attempt_id: str, payload: dict[str, Any]) -> None:
    attempt_dir = review_dir(config, review_id) / "attempts" / attempt_id
    dump_json(attempt_dir / "prediction.json", payload)


def run_single_review(config: RunConfig, review: dict[str, Any], backend: ModelBackend) -> dict[str, Any]:
    review_id = review["review_id"]
    lock = _lock_for(state_path(config, review_id))
    with lock:
        state = load_state(config, review_id) or _initial_state(config, review_id)
        state["attempt_count"] = int(state.get("attempt_count", 0)) + 1
        state["status"] = "running"
        state["started_at"] = utc_now()
        state["finished_at"] = ""
        save_state(config, review_id, state)
    attempt_id = latest_attempt_id(state)
    prompt = build_prompt(review)
    raw_output = ""
    parsed: dict[str, Any] = {}
    last_error = ""
    for attempt_index in range(config.max_retries + 1):
        try:
            raw_output = backend.generate(prompt, review, config)
            parsed = parse_prediction(raw_output)
            break
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            if attempt_index >= config.max_retries:
                parsed = {
                    "parse_status": "failed",
                    "schema_valid": False,
                    "parsed_prediction_json": [],
                    "raw_parsed_prediction_json": [],
                    "error": last_error,
                }
    payload = {
        "review_id": review_id,
        "raw_model_output": raw_output,
        "raw_parsed_prediction_json": parsed.get("raw_parsed_prediction_json", []),
        "parsed_prediction_json": parsed.get("parsed_prediction_json", []),
        "parse_status": parsed.get("parse_status", "failed"),
        "schema_valid": parsed.get("schema_valid", False),
        "attempt_id": attempt_id,
        "canonicalization_version": CANONICALIZATION_VERSION,
        "model_name": config.model_name,
        "model_version": config.model_version,
        "split": config.split,
        "created_at": utc_now(),
        "error": parsed.get("error", last_error),
    }
    _write_attempt_artifacts(config, review_id, attempt_id, payload)
    dump_json(latest_prediction_path(config, review_id), payload)
    with lock:
        state = load_state(config, review_id) or _initial_state(config, review_id)
        state["finished_at"] = utc_now()
        state["last_error"] = payload["error"]
        state["last_non_empty_output"] = bool(payload["parsed_prediction_json"])
        if payload["parse_status"] == "success":
            state["status"] = "success"
        elif payload["parse_status"] == "invalid_output":
            state["status"] = "invalid_output"
        else:
            state["status"] = "failed"
        save_state(config, review_id, state)
    return state


def _collect_status_counts(config: RunConfig, reviews: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "pending": 0,
        "running": 0,
        "success": 0,
        "failed": 0,
        "invalid_output": 0,
    }
    for review in reviews:
        state = load_state(config, review["review_id"])
        status = (state or {}).get("status", "pending")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _render_progress_bar(completed: int, total: int, *, width: int = 28) -> str:
    if total <= 0:
        total = 1
    ratio = completed / total
    filled = min(width, int(ratio * width))
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def _write_progress(
    config: RunConfig,
    *,
    dataset_review_count: int,
    scheduled_review_count: int,
    completed_review_count: int,
    status_counts: dict[str, int],
    started_at: str,
    finished_at: str = "",
) -> dict[str, Any]:
    payload = {
        "model_name": config.model_name,
        "model_version": config.model_version,
        "split": config.split,
        "dataset_review_count": dataset_review_count,
        "scheduled_review_count": scheduled_review_count,
        "completed_review_count": completed_review_count,
        "remaining_review_count": max(scheduled_review_count - completed_review_count, 0),
        "status_counts": status_counts,
        "concurrency": config.concurrency,
        "started_at": started_at,
        "updated_at": utc_now(),
        "finished_at": finished_at,
    }
    dump_json(run_root(config) / "progress.json", payload)
    return payload


def run_split(dataset_path: Path, config: RunConfig, backend: ModelBackend) -> dict[str, Any]:
    reviews = load_jsonl(dataset_path)
    selected: list[dict[str, Any]] = []
    for review in reviews:
        state = load_state(config, review["review_id"])
        if should_run_review(config, review, state):
            selected.append(review)
    started_at = utc_now()
    status_counts = _collect_status_counts(config, reviews)
    _write_progress(
        config,
        dataset_review_count=len(reviews),
        scheduled_review_count=len(selected),
        completed_review_count=0,
        status_counts=status_counts,
        started_at=started_at,
    )
    if not selected:
        summary = {
            "model_name": config.model_name,
            "model_version": config.model_version,
            "split": config.split,
            "scheduled_review_count": 0,
            "completed_at": utc_now(),
            "concurrency": config.concurrency,
        }
        dump_json(run_root(config) / "run_summary.json", summary)
        return summary

    completed = 0
    total = len(selected)
    with ThreadPoolExecutor(max_workers=config.concurrency) as executor:
        futures = [executor.submit(run_single_review, config, review, backend) for review in selected]
        for future in as_completed(futures):
            future.result()
            completed += 1
            status_counts = _collect_status_counts(config, reviews)
            progress_payload = _write_progress(
                config,
                dataset_review_count=len(reviews),
                scheduled_review_count=total,
                completed_review_count=completed,
                status_counts=status_counts,
                started_at=started_at,
            )
            bar = _render_progress_bar(completed, total)
            print(
                f"{bar} {completed}/{total} | success={progress_payload['status_counts'].get('success', 0)} "
                f"failed={progress_payload['status_counts'].get('failed', 0)} "
                f"invalid={progress_payload['status_counts'].get('invalid_output', 0)}",
                flush=True,
            )
            time.sleep(0)
    summary = {
        "model_name": config.model_name,
        "model_version": config.model_version,
        "split": config.split,
        "scheduled_review_count": total,
        "completed_at": utc_now(),
        "concurrency": config.concurrency,
    }
    status_counts = _collect_status_counts(config, reviews)
    _write_progress(
        config,
        dataset_review_count=len(reviews),
        scheduled_review_count=total,
        completed_review_count=total,
        status_counts=status_counts,
        started_at=started_at,
        finished_at=summary["completed_at"],
    )
    dump_json(run_root(config) / "run_summary.json", summary)
    return summary
