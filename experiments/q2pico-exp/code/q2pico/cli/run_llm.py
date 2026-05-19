"""Run OpenAI-compatible Question-to-PICO slot extraction."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import random
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from q2pico.config import get_provider_config, load_config
from q2pico.io_utils import append_jsonl, read_jsonl, read_question_examples, write_json, write_jsonl
from q2pico.prompt_registry import read_prompt_template
from q2pico.schemas import LABEL_TO_OUTPUT_KEY, PICO_LABELS, QuestionPICOExample, parse_label_scope

PROMPT_MODE = "question-slot-split-v1"
PROMPT_VERSION = "question_slot_split_v1"
LABEL_PROMPT_VERSIONS = {
    "P": "question_slot_split_v1_p_only",
    "I": "question_slot_split_v1_i_only",
    "C": "question_slot_split_v1_c_only",
    "O": "question_slot_split_v1_o_only",
}
PI_P_PROMPT_VERSION = "question_slot_split_v1_p_pi_enhanced"
PI_I_PROMPT_VARIANTS = {
    "baseline": "question_slot_split_v1_i_only",
    "official_only": "question_slot_split_v1_i_official_only",
    "official_plus_order_heuristic": "question_slot_split_v1_i_official_plus_order_heuristic",
}
DEFAULT_FEW_SHOT_PATH = "results/data/questions.fewshot20.examples.jsonl"
SCHEMA_VERSION = "q2_question_slots_v1"
API_DATE = "2026-05-16"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_TEMPERATURE = 0
DEFAULT_FEW_SHOT_COUNT = 3
DEFAULT_WORKERS = 16
DEFAULT_MAX_RETRIES = 2
DEFAULT_OPENAI_CLIENT_MAX_RETRIES = 0
DEFAULT_RETRY_MAX_BACKOFF_SECONDS = 30.0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Question-to-PICO slot extraction.")
    parser.add_argument("--provider", default="openai", choices=("openai",))
    parser.add_argument("--model-id", help="OpenAI model id. Overrides provider config model_id.")
    parser.add_argument("--model-version", help="Optional model version or release date.")
    parser.add_argument("--provider-config", help="Optional JSON/YAML provider config path.")
    parser.add_argument("--examples", required=True, help="Prepared question examples JSONL.")
    parser.add_argument("--split-manifest", required=True, help="Prepared split manifest JSON.")
    parser.add_argument("--output-dir", required=True, help="Directory for prompts, raw output, and run config.")
    parser.add_argument("--prompt-mode", choices=(PROMPT_MODE,), default=PROMPT_MODE)
    parser.add_argument(
        "--pi-prompt-variant",
        choices=tuple(PI_I_PROMPT_VARIANTS),
        help=(
            "Use the PI ablation prompt profile: enhanced P prompt for P plus the selected I prompt variant. "
            "Omit to use the original label prompt mapping."
        ),
    )
    parser.add_argument("--labels", default="P,I,C,O", help="Comma-separated label scope, e.g. P,I")
    parser.add_argument("--few-shot-examples", default=DEFAULT_FEW_SHOT_PATH)
    parser.add_argument("--few-shot-count", type=int, default=DEFAULT_FEW_SHOT_COUNT)
    parser.add_argument("--limit", type=int, help="Maximum number of questions to process.")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    parser.add_argument("--temperature", type=float, help="Override provider/default temperature.")
    parser.add_argument("--timeout-seconds", type=float, help="Override provider/default request timeout.")
    parser.add_argument("--resume", action="store_true", help="Resume from existing per-label outputs.")
    parser.add_argument("--show-progress", action="store_true", help="Print simple progress updates to stderr.")
    parser.add_argument("--dry-run", action="store_true", help="Render prompts and run_config without calling the API.")
    parser.add_argument("--force", action="store_true", help="Replace existing output directory files.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    output_dir = Path(args.output_dir)
    prompts_path = output_dir / "prompts.jsonl"
    raw_path = output_dir / "raw.jsonl"
    error_path = output_dir / "errors.jsonl"
    config_path = output_dir / "run_config.json"
    labels = parse_label_scope(args.labels)
    label_prompt_versions = _resolve_label_prompt_versions(args.pi_prompt_variant)
    _check_outputs([prompts_path, raw_path, error_path, config_path], args.force, args.dry_run, args.resume)
    for label in labels:
        label_dir = output_dir / "labels" / label
        _check_outputs(
            [
                label_dir / "prompts.jsonl",
                label_dir / "raw.jsonl",
                label_dir / "errors.jsonl",
                label_dir / "run_config.json",
            ],
            args.force,
            args.dry_run,
            args.resume,
        )

    examples = read_question_examples(args.examples)
    if args.limit is not None:
        if args.limit < 0:
            raise ValueError("--limit must be non-negative")
        examples = examples[: args.limit]
    if args.few_shot_count < 0:
        raise ValueError("--few-shot-count must be non-negative")
    if args.workers <= 0:
        raise ValueError("--workers must be positive")
    if args.max_retries < 0:
        raise ValueError("--max-retries must be non-negative")

    provider_settings = _load_provider_settings(args.provider_config, args.provider)
    model_id = args.model_id or provider_settings.get("model_id")
    if not isinstance(model_id, str) or not model_id:
        raise RuntimeError("OpenAI model id is required. Pass --model-id or set providers.openai.model_id.")
    model_version = args.model_version
    if model_version is None:
        configured_model_version = provider_settings.get("model_version")
        if configured_model_version is not None:
            model_version = str(configured_model_version)
    base_url = str(provider_settings.get("base_url") or DEFAULT_BASE_URL)
    temperature = _coalesce_float(args.temperature, provider_settings.get("temperature"), DEFAULT_TEMPERATURE)
    timeout_seconds = _coalesce_float(
        args.timeout_seconds,
        provider_settings.get("timeout_seconds"),
        DEFAULT_TIMEOUT_SECONDS,
    )
    api_key = _resolve_api_key(provider_settings)
    api_mode = _resolve_api_mode(provider_settings, base_url)
    few_shot_examples = read_question_examples(args.few_shot_examples)[: args.few_shot_count]

    return _run_split_mode(
        args=args,
        examples=examples,
        few_shot_examples=few_shot_examples,
        output_dir=output_dir,
        prompts_path=prompts_path,
        raw_path=raw_path,
        error_path=error_path,
        config_path=config_path,
        model_id=model_id,
        model_version=model_version,
        base_url=base_url,
        temperature=temperature,
        timeout_seconds=timeout_seconds,
        api_key=api_key,
        api_mode=api_mode,
        labels=labels,
        label_prompt_versions=label_prompt_versions,
    )


def _run_split_mode(
    *,
    args: argparse.Namespace,
    examples: list[QuestionPICOExample],
    few_shot_examples: list[QuestionPICOExample],
    output_dir: Path,
    prompts_path: Path,
    raw_path: Path,
    error_path: Path,
    config_path: Path,
    model_id: str,
    model_version: str | None,
    base_url: str,
    temperature: float,
    timeout_seconds: float,
    api_key: str | None,
    api_mode: str,
    labels: tuple[str, ...],
    label_prompt_versions: dict[str, str],
) -> int:
    prompt_rows_by_label: dict[str, list[dict[str, Any]]] = {}
    existing_raw_rows_by_label: dict[str, list[dict[str, Any]]] = {}
    existing_error_rows_by_label: dict[str, list[dict[str, Any]]] = {}
    completed_subrequests: set[tuple[str, str]] = set()

    for label in labels:
        label_dir = output_dir / "labels" / label
        raw_label_path = label_dir / "raw.jsonl"
        error_label_path = label_dir / "errors.jsonl"
        existing_raw_rows = list(read_jsonl(raw_label_path)) if args.resume and raw_label_path.exists() else []
        existing_error_rows = list(read_jsonl(error_label_path)) if args.resume and error_label_path.exists() else []
        existing_raw_rows_by_label[label] = existing_raw_rows
        existing_error_rows_by_label[label] = existing_error_rows
        for row in existing_raw_rows:
            question_id = row.get("question_id")
            if isinstance(question_id, str):
                completed_subrequests.add((question_id, label))

    top_prompt_rows = [
        {
            "question_id": example.question_id,
            "split_extraction": True,
            "subrequests": [{"label": label} for label in labels],
        }
        for example in examples
    ]
    write_jsonl(prompts_path, top_prompt_rows)

    for label in labels:
        prompt_version = label_prompt_versions[label]
        prompt_template = _read_prompt_template(prompt_version)
        prompt_rows = [
            _build_prompt_row(
                example=example,
                prompt_template=prompt_template,
                prompt_version=prompt_version,
                model_id=model_id,
                model_version=model_version,
                provider=args.provider,
                base_url=base_url,
                temperature=temperature,
                few_shot_examples=few_shot_examples,
                label=label,
            )
            for example in examples
            if (example.question_id, label) not in completed_subrequests
        ]
        for row in prompt_rows:
            row["label"] = label
            row["subrequest_id"] = f"{row['question_id']}::{label}"
        prompt_rows_by_label[label] = prompt_rows
        label_dir = output_dir / "labels" / label
        label_prompts_path = label_dir / "prompts.jsonl"
        label_raw_path = label_dir / "raw.jsonl"
        label_error_path = label_dir / "errors.jsonl"
        label_config_path = label_dir / "run_config.json"
        write_jsonl(label_prompts_path, prompt_rows)
        write_json(
            label_config_path,
            {
                "task": "question_pico",
                "task_version": "q2crbench_question_v1",
                "input_type": "clinical_question",
                "provider": args.provider,
                "model_id": model_id,
                "model_version": model_version,
                "base_url": base_url,
                "api_mode": api_mode,
                "temperature": temperature,
                "timeout_seconds": timeout_seconds,
                "workers": args.workers,
                "max_retries": args.max_retries,
                "openai_client_max_retries": DEFAULT_OPENAI_CLIENT_MAX_RETRIES,
                "prompt_mode": args.prompt_mode,
                "prompt_version": PROMPT_VERSION,
                "pi_prompt_variant": args.pi_prompt_variant,
                "label": label,
                "prompt_schema": "keyed_json",
                "schema_version": SCHEMA_VERSION,
                "api_date": API_DATE,
                "dry_run": args.dry_run,
                "resume": args.resume,
                "show_progress": args.show_progress,
                "labels": list(labels),
                "label_prompt_versions": {label: label_prompt_versions[label]},
                "label_few_shot_paths": {label: args.few_shot_examples},
                "few_shot_doc_ids": [example.question_id for example in few_shot_examples],
                "split_manifest_path": args.split_manifest,
                "examples_path": args.examples,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "output_paths": {
                    "prompts": str(label_prompts_path),
                    "raw": str(label_raw_path),
                    "errors": str(label_error_path),
                    "run_config": str(label_config_path),
                },
                "pending_prompt_rows": len(prompt_rows),
                "existing_raw_rows": len(existing_raw_rows_by_label[label]),
                "existing_error_rows": len(existing_error_rows_by_label[label]),
            },
        )

    top_run_config = {
        "task": "question_pico",
        "task_version": "q2crbench_question_v1",
        "input_type": "clinical_question",
        "provider": args.provider,
        "model_id": model_id,
        "model_version": model_version,
        "base_url": base_url,
        "api_mode": api_mode,
        "temperature": temperature,
        "timeout_seconds": timeout_seconds,
        "workers": args.workers,
        "max_retries": args.max_retries,
        "openai_client_max_retries": DEFAULT_OPENAI_CLIENT_MAX_RETRIES,
        "prompt_mode": args.prompt_mode,
        "prompt_version": PROMPT_VERSION,
        "pi_prompt_variant": args.pi_prompt_variant,
        "label_prompt_versions": {label: label_prompt_versions[label] for label in labels},
        "label_few_shot_paths": {label: args.few_shot_examples for label in labels},
        "few_shot_doc_ids": {label: [example.question_id for example in few_shot_examples] for label in labels},
        "split_manifest_path": args.split_manifest,
        "examples_path": args.examples,
        "prompt_schema": "keyed_json",
        "schema_version": SCHEMA_VERSION,
        "api_date": API_DATE,
        "dry_run": args.dry_run,
        "resume": args.resume,
        "show_progress": args.show_progress,
        "labels": list(labels),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "output_paths": {
            "prompts": str(prompts_path),
            "raw": str(raw_path),
            "errors": str(error_path),
            "run_config": str(config_path),
        },
        "pending_prompt_rows": sum(len(rows) for rows in prompt_rows_by_label.values()),
        "existing_raw_rows": sum(len(rows) for rows in existing_raw_rows_by_label.values()),
        "existing_error_rows": sum(len(rows) for rows in existing_error_rows_by_label.values()),
    }
    write_json(config_path, top_run_config)

    if args.dry_run:
        return 0
    if not api_key:
        raise RuntimeError(
            "OpenAI API key is required for non-dry-run execution. "
            "Set OPENAI_API_KEY or configure providers.openai.api_key/api_key_env."
        )

    for label in labels:
        label_dir = output_dir / "labels" / label
        run_result = _call_openai(
            prompt_rows=prompt_rows_by_label[label],
            raw_path=label_dir / "raw.jsonl",
            error_path=label_dir / "errors.jsonl",
            api_key=api_key,
            base_url=base_url,
            model_id=model_id,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            api_mode=api_mode,
            workers=args.workers,
            show_progress=args.show_progress,
            max_retries=args.max_retries,
        )
        completed_question_ids: set[str] = set()
        if (label_dir / "raw.jsonl").exists():
            completed_question_ids = {
                row["question_id"]
                for row in read_jsonl(label_dir / "raw.jsonl")
                if isinstance(row.get("question_id"), str)
            }
        unresolved_error_rows = [
            row
            for row in existing_error_rows_by_label[label]
            if isinstance(row.get("question_id"), str) and row["question_id"] not in completed_question_ids
        ]
        if args.resume and (label_dir / "errors.jsonl").exists():
            write_jsonl(label_dir / "errors.jsonl", unresolved_error_rows)
        label_config_path = label_dir / "run_config.json"
        label_config = json.loads(label_config_path.read_text(encoding="utf-8"))
        label_config["completed_raw_rows"] = len(existing_raw_rows_by_label[label]) + run_result["written_rows"]
        label_config["failed_rows"] = len(unresolved_error_rows) + run_result["failed_rows"]
        write_json(label_config_path, label_config)

    aggregate = _aggregate_split_outputs(output_dir, labels=labels)
    write_jsonl(raw_path, aggregate["raw_rows"])
    write_jsonl(error_path, aggregate["error_rows"])
    top_run_config["completed_subrequests"] = aggregate["completed_subrequests"]
    top_run_config["failed_subrequests"] = aggregate["failed_subrequests"]
    top_run_config["completed_questions"] = aggregate["completed_questions"]
    top_run_config["completed_raw_rows"] = len(aggregate["raw_rows"])
    top_run_config["failed_rows"] = len(aggregate["error_rows"])
    write_json(config_path, top_run_config)
    if aggregate["failed_subrequests"]:
        raise RuntimeError(
            f"LLM split run finished with {len(aggregate['failed_subrequests'])} failed subrequests. "
            f"See {error_path} and rerun with --resume to fill only missing subrequests."
        )
    return 0


def _check_outputs(paths: list[Path], force: bool, dry_run: bool, resume: bool) -> None:
    raw_path = paths[1]
    error_path = paths[2]
    config_path = paths[3]
    if raw_path.exists() and not config_path.exists():
        raise FileExistsError(f"raw output exists without run_config: {raw_path}; remove it or restore {config_path}")
    if error_path.exists() and not config_path.exists():
        raise FileExistsError(
            f"error output exists without run_config: {error_path}; remove it or restore {config_path}"
        )
    if resume:
        return
    paths_to_check = paths if not dry_run else [paths[0], paths[3]]
    existing = [path for path in paths_to_check if path.exists()]
    if existing and not force:
        existing_text = ", ".join(str(path) for path in existing)
        raise FileExistsError(f"Output path already exists: {existing_text}; pass --force to replace")


def _resolve_label_prompt_versions(pi_prompt_variant: str | None) -> dict[str, str]:
    label_prompt_versions = dict(LABEL_PROMPT_VERSIONS)
    if pi_prompt_variant is None:
        return label_prompt_versions
    label_prompt_versions["P"] = PI_P_PROMPT_VERSION
    label_prompt_versions["I"] = PI_I_PROMPT_VARIANTS[pi_prompt_variant]
    return label_prompt_versions


def _load_provider_settings(provider_config: str | None, provider: str) -> dict[str, Any]:
    if provider_config is None:
        return {}
    config = load_config(provider_config)
    provider_settings = get_provider_config(config, provider)
    defaults = config.get("defaults", {})
    if defaults is None:
        defaults = {}
    if not isinstance(defaults, dict):
        raise ValueError("Config field 'defaults' must be an object")
    return {**defaults, **provider_settings}


def _coalesce_float(*values: Any) -> float:
    for value in values:
        if value is not None:
            return float(value)
    raise ValueError("Expected at least one non-null value")


def _resolve_api_key(provider_settings: dict[str, Any]) -> str | None:
    api_key = provider_settings.get("api_key")
    if isinstance(api_key, str) and api_key and not api_key.startswith("FILL_ME"):
        return api_key
    env_name = provider_settings.get("api_key_env", "OPENAI_API_KEY")
    if isinstance(env_name, str) and env_name:
        env_value = os.environ.get(env_name)
        if env_value:
            return env_value
    return None


def _resolve_api_mode(provider_settings: dict[str, Any], base_url: str) -> str:
    configured = provider_settings.get("api_mode")
    if configured is not None:
        value = str(configured)
        if value not in {"responses", "chat_completions"}:
            raise ValueError("providers.openai.api_mode must be 'responses' or 'chat_completions'")
        return value
    if "api.openai.com" in base_url:
        return "responses"
    return "chat_completions"


def _read_prompt_template(prompt_version: str) -> str:
    return read_prompt_template(prompt_version)


def _build_prompt_row(
    *,
    example: QuestionPICOExample,
    prompt_template: str,
    prompt_version: str,
    model_id: str,
    model_version: str | None,
    provider: str,
    base_url: str,
    temperature: float,
    few_shot_examples: list[QuestionPICOExample],
    label: str,
) -> dict[str, Any]:
    keyed_output_key = LABEL_TO_OUTPUT_KEY[label]
    few_shot_block = _render_few_shot_block(few_shot_examples, label=label)
    user_prompt = prompt_template.format(
        question_id=example.question_id,
        question_text=example.question_text,
        few_shot_examples=few_shot_block,
    )
    return {
        "question_id": example.question_id,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You extract structured PICO slots from clinical questions. "
                    "Use only information inferable from the question text and return JSON only."
                ),
            },
            {"role": "user", "content": user_prompt},
        ],
        "metadata": {
            "provider": provider,
            "model_id": model_id,
            "model_version": model_version,
            "base_url": base_url,
            "temperature": temperature,
            "prompt_mode": PROMPT_MODE,
            "prompt_version": prompt_version,
            "schema_version": SCHEMA_VERSION,
            "prompt_schema": "keyed_json",
            "api_date": API_DATE,
            "few_shot_doc_ids": [shot.question_id for shot in few_shot_examples],
            "label_filter": label,
            "keyed_output_key": keyed_output_key,
        },
    }


def _render_few_shot_block(examples: list[QuestionPICOExample], *, label: str) -> str:
    if not examples:
        return ""
    keyed_output_key = LABEL_TO_OUTPUT_KEY[label]
    rendered: list[str] = []
    for example in examples:
        rendered.append(
            "Example question_id: {question_id}\nClinical question:\n{question_text}\nExpected JSON:\n{payload}".format(
                question_id=example.question_id,
                question_text=example.question_text,
                payload=json.dumps(
                    {keyed_output_key: example.gold_slots[label]},
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            )
        )
    return "\n\n".join(rendered)


def _call_openai(
    *,
    prompt_rows: list[dict[str, Any]],
    raw_path: Path,
    error_path: Path,
    api_key: str,
    base_url: str,
    model_id: str,
    temperature: float,
    timeout_seconds: float,
    api_mode: str,
    workers: int,
    show_progress: bool,
    max_retries: int,
) -> dict[str, int]:
    progress = _ProgressPrinter(total=len(prompt_rows), enabled=show_progress)
    max_workers = min(workers, max(1, len(prompt_rows)))
    written_rows = 0
    failed_rows = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _call_single_prompt,
                prompt_row=prompt_row,
                api_key=api_key,
                base_url=base_url,
                model_id=model_id,
                temperature=temperature,
                timeout_seconds=timeout_seconds,
                api_mode=api_mode,
                max_retries=max_retries,
            ): index
            for index, prompt_row in enumerate(prompt_rows)
        }
        for future in concurrent.futures.as_completed(futures):
            index = futures[future]
            try:
                row = future.result()
            except Exception as exc:
                failed_rows += 1
                question_id = prompt_rows[index]["question_id"]
                append_jsonl(
                    error_path,
                    [
                        {
                            "question_id": question_id,
                            "error_type": type(exc).__name__,
                            "message": str(exc),
                        }
                    ],
                )
                progress.failed(question_id=question_id, message=str(exc))
                continue
            append_jsonl(raw_path, [row])
            written_rows += 1
            progress.done(question_id=row["question_id"])
    progress.finish()
    return {"written_rows": written_rows, "failed_rows": failed_rows}


def _call_single_prompt(
    *,
    prompt_row: dict[str, Any],
    api_key: str,
    base_url: str,
    model_id: str,
    temperature: float,
    timeout_seconds: float,
    api_mode: str,
    max_retries: int,
) -> dict[str, Any]:
    attempt = 0
    while True:
        try:
            return _call_single_prompt_once(
                prompt_row=prompt_row,
                api_key=api_key,
                base_url=base_url,
                model_id=model_id,
                temperature=temperature,
                timeout_seconds=timeout_seconds,
                api_mode=api_mode,
            )
        except Exception as exc:
            if not _is_retryable_error(exc) or attempt >= max_retries:
                raise
            attempt += 1
            time.sleep(_retry_delay_seconds(exc, attempt))


def _is_retryable_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int) and status_code in {408, 409, 429, 500, 502, 503, 504}:
        return True
    retryable_error_names = {
        "APITimeoutError",
        "APIConnectionError",
        "RateLimitError",
        "InternalServerError",
    }
    if type(exc).__name__ in retryable_error_names:
        return True
    message = str(exc).lower()
    return (
        "temporarily unavailable" in message
        or "request timed out" in message
        or "connection reset" in message
        or "rate limit" in message
        or "too many requests" in message
        or "gateway timeout" in message
    )


def _retry_delay_seconds(exc: Exception, attempt: int) -> float:
    retry_after = _extract_retry_after_seconds(exc)
    if retry_after is not None:
        return retry_after
    exp_backoff = min(float(2**attempt), DEFAULT_RETRY_MAX_BACKOFF_SECONDS)
    jitter = random.uniform(0.0, 1.0)
    return exp_backoff + jitter


def _extract_retry_after_seconds(exc: Exception) -> float | None:
    response = getattr(exc, "response", None)
    if response is None:
        return None
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    value = headers.get("retry-after")
    if value is None:
        return None
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None
    if seconds <= 0:
        return None
    return min(seconds, DEFAULT_RETRY_MAX_BACKOFF_SECONDS)


def _call_single_prompt_once(
    *,
    prompt_row: dict[str, Any],
    api_key: str,
    base_url: str,
    model_id: str,
    temperature: float,
    timeout_seconds: float,
    api_mode: str,
) -> dict[str, Any]:
    try:
        from openai import BadRequestError, NotFoundError, OpenAI
    except ImportError as exc:
        raise RuntimeError("The openai package is required for q2pico LLM runs") from exc

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout_seconds,
        max_retries=DEFAULT_OPENAI_CLIENT_MAX_RETRIES,
    )
    request_mode = api_mode
    keyed_output_key = prompt_row["metadata"]["keyed_output_key"]
    try:
        if request_mode == "responses":
            response = client.responses.create(
                model=model_id,
                input=prompt_row["messages"],
                temperature=temperature,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "question_pico_slots",
                        "schema": _response_schema(keyed_output_key),
                        "strict": True,
                    }
                },
            )
            parsed = _parse_response_text(response.output_text, keyed_output_key)
            response_id = getattr(response, "id", None)
        else:
            parsed, response_id, request_mode = _call_chat_completions(
                client=client,
                prompt_row=prompt_row,
                model_id=model_id,
                temperature=temperature,
            )
    except NotFoundError:
        if request_mode != "responses":
            raise
        parsed, response_id, request_mode = _call_chat_completions(
            client=client,
            prompt_row=prompt_row,
            model_id=model_id,
            temperature=temperature,
        )
    except BadRequestError:
        if request_mode != "responses":
            raise
        parsed, response_id, request_mode = _call_chat_completions(
            client=client,
            prompt_row=prompt_row,
            model_id=model_id,
            temperature=temperature,
        )
    return {
        "question_id": prompt_row["question_id"],
        "response": json.dumps(parsed, ensure_ascii=False, sort_keys=True),
        "metadata": {
            **prompt_row["metadata"],
            "api_mode": request_mode,
            "openai_response_id": response_id,
        },
    }


def _call_chat_completions(
    *,
    client: Any,
    prompt_row: dict[str, Any],
    model_id: str,
    temperature: float,
) -> tuple[dict[str, Any], Any, str]:
    try:
        from openai import BadRequestError
    except ImportError as exc:
        raise RuntimeError("The openai package is required for q2pico LLM runs") from exc

    keyed_output_key = prompt_row["metadata"]["keyed_output_key"]
    attempts: list[tuple[str, dict[str, Any] | None]] = [
        (
            "chat_completions_json_schema",
            {
                "type": "json_schema",
                "json_schema": {
                    "name": "question_pico_slots",
                    "schema": _response_schema(keyed_output_key),
                    "strict": True,
                },
            },
        ),
        ("chat_completions_json_object", {"type": "json_object"}),
        ("chat_completions_plain", None),
    ]
    last_error: Exception | None = None
    for mode_name, response_format in attempts:
        kwargs: dict[str, Any] = {
            "model": model_id,
            "messages": prompt_row["messages"],
            "temperature": temperature,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format
        try:
            response = client.chat.completions.create(**kwargs)
        except BadRequestError as exc:
            last_error = exc
            if not _is_response_format_error(exc):
                raise
            continue
        content = response.choices[0].message.content
        if not isinstance(content, str):
            raise ValueError("Chat completions response did not contain string content")
        return _parse_response_text(content, keyed_output_key), getattr(response, "id", None), mode_name
    if last_error is not None:
        raise last_error
    raise RuntimeError("chat.completions fallback exhausted without a response")


def _is_response_format_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "response_format" in message
        or "json_schema" in message
        or "json_object" in message
        or "text.format" in message
        or "missing required parameter" in message
    )


class _ProgressPrinter:
    def __init__(self, total: int, enabled: bool) -> None:
        self.total = total
        self.enabled = enabled and total > 0
        self.completed = 0
        self._lock = threading.Lock()
        if self.enabled:
            print(f"[run_llm] queued {self.total} requests", file=sys.stderr, flush=True)

    def done(self, question_id: str) -> None:
        if not self.enabled:
            return
        with self._lock:
            self.completed += 1
            print(
                f"[run_llm] completed {self.completed}/{self.total} question_id={question_id}",
                file=sys.stderr,
                flush=True,
            )

    def failed(self, question_id: str, message: str) -> None:
        if not self.enabled:
            return
        with self._lock:
            self.completed += 1
            print(
                f"[run_llm] failed {self.completed}/{self.total} question_id={question_id} error={message}",
                file=sys.stderr,
                flush=True,
            )

    def finish(self) -> None:
        if not self.enabled:
            return
        print(f"[run_llm] finished {self.completed}/{self.total}", file=sys.stderr, flush=True)


def _response_schema(keyed_output_key: str) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            keyed_output_key: {
                "type": "array",
                "items": {"type": "string"},
            }
        },
        "required": [keyed_output_key],
    }


def _parse_response_text(output_text: str, keyed_output_key: str) -> dict[str, list[str]]:
    candidates = [output_text, _strip_markdown_code_fence(output_text)]
    parsed: Any | None = None
    for candidate in candidates:
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
            break
        except json.JSONDecodeError:
            extracted = _extract_first_json_value(candidate)
            if extracted is not None:
                parsed = extracted
                break
    if parsed is None:
        raise ValueError("OpenAI response output_text was not valid JSON")
    if not isinstance(parsed, dict) or not isinstance(parsed.get(keyed_output_key), list):
        raise ValueError(f"OpenAI response must be an object with a {keyed_output_key!r} array")
    for invalid_key in LABEL_TO_OUTPUT_KEY.values():
        if invalid_key == keyed_output_key:
            continue
        if invalid_key in parsed:
            raise ValueError(f"OpenAI response must use the {keyed_output_key!r} key, not {invalid_key!r}")
    normalized_items: list[str] = []
    for item in parsed[keyed_output_key]:
        if not isinstance(item, str):
            raise ValueError(f"{keyed_output_key} items must be strings")
        normalized_items.append(item)
    return {keyed_output_key: normalized_items}


def _strip_markdown_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _extract_first_json_value(text: str) -> Any | None:
    decoder = json.JSONDecoder()
    for idx, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            value, _end = decoder.raw_decode(text[idx:])
        except json.JSONDecodeError:
            continue
        return value
    return None


def _aggregate_split_outputs(output_dir: Path, *, labels: tuple[str, ...]) -> dict[str, Any]:
    rows_by_question: dict[str, dict[str, dict[str, Any]]] = {}
    errors_by_question: dict[str, dict[str, dict[str, Any]]] = {}
    completed_subrequests: list[str] = []
    failed_subrequests: list[str] = []

    for label in labels:
        label_dir = output_dir / "labels" / label
        raw_path = label_dir / "raw.jsonl"
        error_path = label_dir / "errors.jsonl"
        if raw_path.exists():
            for row in read_jsonl(raw_path):
                question_id = row.get("question_id")
                if isinstance(question_id, str):
                    rows_by_question.setdefault(question_id, {})[label] = row
                    completed_subrequests.append(f"{question_id}::{label}")
        if error_path.exists():
            for row in read_jsonl(error_path):
                question_id = row.get("question_id")
                if isinstance(question_id, str):
                    errors_by_question.setdefault(question_id, {})[label] = row
                    failed_subrequests.append(f"{question_id}::{label}")

    raw_rows: list[dict[str, Any]] = []
    error_rows: list[dict[str, Any]] = []
    completed_questions: list[str] = []
    all_question_ids = sorted(set(rows_by_question) | set(errors_by_question))
    for question_id in all_question_ids:
        label_rows = rows_by_question.get(question_id, {})
        if all(label in label_rows for label in labels):
            merged = {label: [] for label in labels}
            label_metadata: dict[str, Any] = {}
            parse_failed = False
            for label in labels:
                row = label_rows[label]
                label_metadata[label] = row.get("metadata", {})
                parsed = json.loads(row["response"])
                keyed_output_key = LABEL_TO_OUTPUT_KEY[label]
                if not isinstance(parsed, dict) or not isinstance(parsed.get(keyed_output_key), list):
                    parse_failed = True
                    break
                merged[label] = parsed[keyed_output_key]
            if not parse_failed:
                raw_rows.append(
                    {
                        "question_id": question_id,
                        "response": json.dumps(merged, ensure_ascii=False, sort_keys=True),
                        "metadata": {
                            "split_extraction": True,
                            "label_metadata": label_metadata,
                            "labels": list(labels),
                        },
                    }
                )
                completed_questions.append(question_id)
                continue
        missing_labels = [label for label in labels if label not in label_rows]
        error_rows.append(
            {
                "question_id": question_id,
                "error_type": "SplitQuestionIncomplete",
                "message": "Not all label subrequests completed successfully",
                "failed_labels": missing_labels,
                "label_errors": errors_by_question.get(question_id, {}),
            }
        )
    return {
        "raw_rows": raw_rows,
        "error_rows": error_rows,
        "completed_subrequests": sorted(set(completed_subrequests)),
        "failed_subrequests": sorted(set(failed_subrequests)),
        "completed_questions": sorted(completed_questions),
    }


if __name__ == "__main__":
    raise SystemExit(main())
