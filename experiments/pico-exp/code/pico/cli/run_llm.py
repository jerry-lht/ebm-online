"""Run OpenAI LLM extraction for PICO spans."""

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

from pico.config import get_provider_config, load_config
from pico.io_utils import append_jsonl, read_document_examples, read_jsonl, write_json, write_jsonl
from pico.prompt_registry import read_prompt_template
from pico.schemas import DocumentExample, PICO_LABELS

PROMPT_VERSION_BY_MODE = {
    "zero-shot-text": "zero_shot_text_v1",
    "few-shot-text": "few_shot_text_v1",
    "zero-shot-text-v2": "zero_shot_text_v2",
    "few-shot-text-v2": "few_shot_text_v2",
    "zero-shot-text-v3": "zero_shot_text_v3",
    "few-shot-text-v3": "few_shot_text_v3",
    "zero-shot-text-v3-i-only": "zero_shot_text_v3_i_only",
    "few-shot-text-v3-i-only": "few_shot_text_v3_i_only",
    "zero-shot-text-v4": "zero_shot_text_v4",
    "few-shot-text-v4": "few_shot_text_v4",
    "zero-shot-text-v4-i-only": "zero_shot_text_v4_i_only",
    "few-shot-text-v4-i-only": "few_shot_text_v4_i_only",
    "zero-shot-text-v5": "zero_shot_text_v5",
    "few-shot-text-v5": "few_shot_text_v5",
    "few-shot-text-bestof-split-v1": "few_shot_text_bestof_split_v1",
    "few-shot-text-bestof-split-v2": "few_shot_text_bestof_split_v2",
    "zero-shot-offsets": "zero_shot_v1",
    "few-shot-offsets": "few_shot_v1",
    "zero-shot": "zero_shot_text_v1",
    "few-shot": "few_shot_text_v1",
}
PROMPT_SCHEMA_BY_MODE = {
    "zero-shot-text": "text",
    "few-shot-text": "text",
    "zero-shot-text-v2": "text",
    "few-shot-text-v2": "text",
    "zero-shot-text-v3": "text",
    "few-shot-text-v3": "text",
    "zero-shot-text-v3-i-only": "text",
    "few-shot-text-v3-i-only": "text",
    "zero-shot-text-v4": "text",
    "few-shot-text-v4": "text",
    "zero-shot-text-v4-i-only": "text",
    "few-shot-text-v4-i-only": "text",
    "zero-shot-text-v5": "text",
    "few-shot-text-v5": "text",
    "few-shot-text-bestof-split-v1": "text",
    "few-shot-text-bestof-split-v2": "text",
    "zero-shot-offsets": "offsets",
    "few-shot-offsets": "offsets",
    "zero-shot": "text",
    "few-shot": "text",
}
BESTOF_SPLIT_LABEL_OUTPUT_KEYS = {
    "P": "participants",
    "I": "interventions",
    "O": "outcomes",
}
BESTOF_SPLIT_DEFAULT_FEW_SHOT_PATHS = {
    "P": "results/data/few_shot_text_bestof_split_p.examples.jsonl",
    "I": "results/data/few_shot_text_bestof_split_i.examples.jsonl",
    "O": "results/data/few_shot_text_bestof_split_o.examples.jsonl",
}
HIDE_FEWSHOT_EXAMPLE_DOC_ID_PROMPT_VERSIONS = {
    "few_shot_text_bestof_split_v1_i_only",
    "few_shot_text_bestof_split_v2_i_only",
}
BESTOF_SPLIT_CONFIG_BY_MODE = {
    "few-shot-text-bestof-split-v1": {
        "prompt_version": "few_shot_text_bestof_split_v1",
        "label_prompt_versions": {
            "P": "few_shot_text_bestof_split_v1_p_only",
            "I": "few_shot_text_bestof_split_v1_i_only",
            "O": "few_shot_text_bestof_split_v1_o_only",
        },
        "label_few_shot_paths": dict(BESTOF_SPLIT_DEFAULT_FEW_SHOT_PATHS),
    },
    "few-shot-text-bestof-split-v2": {
        "prompt_version": "few_shot_text_bestof_split_v2",
        "label_prompt_versions": {
            "P": "few_shot_text_bestof_split_v1_p_only",
            "I": "few_shot_text_bestof_split_v2_i_only",
            "O": "few_shot_text_bestof_split_v1_o_only",
        },
        "label_few_shot_paths": dict(BESTOF_SPLIT_DEFAULT_FEW_SHOT_PATHS),
    },
}
KEYED_OUTPUT_KEY_BY_PROMPT_VERSION = {
    prompt_version: BESTOF_SPLIT_LABEL_OUTPUT_KEYS[label]
    for split_config in BESTOF_SPLIT_CONFIG_BY_MODE.values()
    for label, prompt_version in split_config["label_prompt_versions"].items()
}
SCHEMA_VERSION = "llm_pico_spans_text_v1"
OFFSET_SCHEMA_VERSION = "llm_pico_spans_offsets_v1"
API_DATE = "2026-05-14"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_TEMPERATURE = 0
DEFAULT_FEW_SHOT_EXAMPLES = 3
DEFAULT_WORKERS = 16
DEFAULT_MAX_RETRIES = 2
DEFAULT_OPENAI_CLIENT_MAX_RETRIES = 0
DEFAULT_RETRY_MAX_BACKOFF_SECONDS = 30.0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run OpenAI structured PICO span extraction.")
    parser.add_argument("--provider", default="openai", choices=("openai",))
    parser.add_argument("--model-id", help="OpenAI model id. Overrides provider config model_id.")
    parser.add_argument(
        "--model-version",
        help="Optional model version or release date. Overrides provider config model_version.",
    )
    parser.add_argument("--provider-config", help="Optional JSON/YAML provider config path.")
    parser.add_argument("--examples", required=True, help="Prepared document examples JSONL.")
    parser.add_argument("--output-dir", required=True, help="Directory for prompts, raw output, and run config.")
    parser.add_argument(
        "--prompt-mode",
        choices=(
            "zero-shot-text",
            "few-shot-text",
            "zero-shot-text-v2",
            "few-shot-text-v2",
            "zero-shot-text-v3",
            "few-shot-text-v3",
            "zero-shot-text-v3-i-only",
            "few-shot-text-v3-i-only",
            "zero-shot-text-v4",
            "few-shot-text-v4",
            "zero-shot-text-v4-i-only",
            "few-shot-text-v4-i-only",
            "zero-shot-text-v5",
            "few-shot-text-v5",
            "few-shot-text-bestof-split-v1",
            "few-shot-text-bestof-split-v2",
            "zero-shot-offsets",
            "few-shot-offsets",
            "zero-shot",
            "few-shot",
        ),
        default="zero-shot-text",
    )
    parser.add_argument("--few-shot-examples", help="Prepared train examples JSONL for few-shot prompt examples.")
    parser.add_argument("--few-shot-count", type=int, default=DEFAULT_FEW_SHOT_EXAMPLES)
    parser.add_argument("--limit", type=int, help="Maximum number of documents to process.")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="Maximum concurrent API requests.")
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES, help="Retry count for per-document API failures.")
    parser.add_argument("--temperature", type=float, help="Override provider/default temperature.")
    parser.add_argument("--timeout-seconds", type=float, help="Override provider/default request timeout.")
    parser.add_argument("--resume", action="store_true", help="Resume from existing outputs and skip completed items.")
    parser.add_argument("--show-progress", action="store_true", help="Print simple progress updates to stderr.")
    parser.add_argument("--dry-run", action="store_true", help="Render prompts and run_config without calling the API.")
    parser.add_argument("--force", action="store_true", help="Replace existing output directory files.")
    parser.add_argument(
        "--label-target",
        choices=tuple(PICO_LABELS),
        help=(
            "Run only a single split label. "
            "Valid only with --prompt-mode few-shot-text-bestof-split-v1 or few-shot-text-bestof-split-v2."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    split_mode = args.prompt_mode in BESTOF_SPLIT_CONFIG_BY_MODE
    if args.label_target is not None and not split_mode:
        raise ValueError(
            "--label-target is valid only with --prompt-mode "
            "few-shot-text-bestof-split-v1 or few-shot-text-bestof-split-v2"
        )

    output_dir = Path(args.output_dir)
    prompts_path = output_dir / "prompts.jsonl"
    raw_path = output_dir / "raw.jsonl"
    error_path = output_dir / "errors.jsonl"
    config_path = output_dir / "run_config.json"
    _check_outputs([prompts_path, raw_path, error_path, config_path], args.force, args.dry_run, args.resume)
    if split_mode and args.label_target is None:
        for label in PICO_LABELS:
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

    examples = read_document_examples(args.examples)
    if args.limit is not None:
        if args.limit < 0:
            raise ValueError("--limit must be non-negative")
        examples = examples[: args.limit]
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

    prompt_schema = PROMPT_SCHEMA_BY_MODE[args.prompt_mode]
    schema_version = SCHEMA_VERSION if prompt_schema == "text" else OFFSET_SCHEMA_VERSION
    split_config = BESTOF_SPLIT_CONFIG_BY_MODE.get(args.prompt_mode)
    if split_mode and args.label_target is None:
        return _run_bestof_split_mode(
            args=args,
            examples=examples,
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
            schema_version=schema_version,
            split_config=split_config,
        )

    label_filter: str | None = None
    label_output_key: str | None = None
    if split_mode and args.label_target is not None:
        label_filter = args.label_target
        assert split_config is not None
        prompt_version = split_config["label_prompt_versions"][label_filter]
        label_output_key = BESTOF_SPLIT_LABEL_OUTPUT_KEYS[label_filter]
        prompt_template = _read_prompt_template(prompt_version)
        label_args = argparse.Namespace(**vars(args))
        if not label_args.few_shot_examples:
            label_args.few_shot_examples = split_config["label_few_shot_paths"][label_filter]
        few_shot_examples = _select_few_shot_examples(label_args)
    else:
        prompt_version = PROMPT_VERSION_BY_MODE[args.prompt_mode]
        prompt_template = _read_prompt_template(prompt_version)
        few_shot_examples = _select_few_shot_examples(args)
    prompt_rows = [
        _build_prompt_row(
            example=example,
            prompt_mode=args.prompt_mode,
            prompt_template=prompt_template,
            prompt_version=prompt_version,
            model_id=model_id,
            model_version=model_version,
            provider=args.provider,
            base_url=base_url,
            temperature=temperature,
            schema_version=schema_version,
            few_shot_examples=few_shot_examples,
            label_filter=label_filter,
        )
        for example in examples
    ]
    if label_filter is not None:
        for row in prompt_rows:
            row["label"] = label_filter
            row["subrequest_id"] = f"{row['doc_id']}::{label_filter}"
    existing_raw_rows: list[dict[str, Any]] = []
    existing_error_rows: list[dict[str, Any]] = []
    completed_doc_ids: set[str] = set()
    if args.resume:
        if raw_path.exists():
            existing_raw_rows = list(read_jsonl(raw_path))
        completed_doc_ids = {
            row["doc_id"]
            for row in existing_raw_rows
            if isinstance(row.get("doc_id"), str)
        }
        if error_path.exists():
            existing_error_rows = list(read_jsonl(error_path))
        prompt_rows = [row for row in prompt_rows if row["doc_id"] not in completed_doc_ids]

    run_config = {
        "provider": args.provider,
        "model_id": model_id,
        "model_version": model_version,
        "base_url": base_url,
        "temperature": temperature,
        "timeout_seconds": timeout_seconds,
        "workers": args.workers,
        "max_retries": args.max_retries,
        "openai_client_max_retries": DEFAULT_OPENAI_CLIENT_MAX_RETRIES,
        "api_mode": api_mode,
        "prompt_mode": args.prompt_mode,
        "prompt_version": prompt_version,
        "schema_version": schema_version,
        "prompt_schema": prompt_schema,
        "api_date": API_DATE,
        "dry_run": args.dry_run,
        "resume": args.resume,
        "show_progress": args.show_progress,
        "input_paths": {
            "examples": args.examples,
            "provider_config": args.provider_config,
            "few_shot_examples": (
                (args.few_shot_examples or split_config["label_few_shot_paths"][label_filter])
                if label_filter is not None and split_mode
                else args.few_shot_examples
            ),
        },
        "output_paths": {
            "prompts": str(prompts_path),
            "raw": str(raw_path),
            "errors": str(error_path),
            "run_config": str(config_path),
        },
        "limit": args.limit,
        "few_shot_doc_ids": [example.doc_id for example in few_shot_examples],
        "existing_raw_rows": len(existing_raw_rows),
        "existing_error_rows": len(existing_error_rows),
        "pending_prompt_rows": len(prompt_rows),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if label_filter is not None and split_mode:
        run_config.update(
            {
                "split_extraction": True,
                "split_strategy": "bestof_pio_v1",
                "label": label_filter,
                "label_output_key": label_output_key,
                "label_prompt_versions": {label_filter: prompt_version},
                "label_few_shot_paths": {
                    label_filter: args.few_shot_examples or split_config["label_few_shot_paths"][label_filter]
                },
                "label_schema_versions": {label_filter: schema_version},
            }
        )

    write_jsonl(prompts_path, prompt_rows)
    write_json(config_path, run_config)

    if args.dry_run:
        return 0
    if not api_key:
        raise RuntimeError(
            "OpenAI API key is required for non-dry-run execution. "
            "Set OPENAI_API_KEY or configure providers.openai.api_key/api_key_env."
        )

    run_result = _call_openai(
        prompt_rows=prompt_rows,
        raw_path=raw_path,
        error_path=error_path,
        api_key=api_key,
        base_url=base_url,
        model_id=model_id,
        temperature=temperature,
        timeout_seconds=timeout_seconds,
        prompt_schema=prompt_schema,
        api_mode=api_mode,
        workers=args.workers,
        show_progress=args.show_progress,
        max_retries=args.max_retries,
    )
    completed_doc_ids.update(
        row["doc_id"]
        for row in read_jsonl(raw_path)
        if isinstance(row.get("doc_id"), str)
    )
    unresolved_error_rows = [
        row
        for row in existing_error_rows
        if isinstance(row.get("doc_id"), str) and row["doc_id"] not in completed_doc_ids
    ]
    if args.resume and error_path.exists():
        write_jsonl(error_path, unresolved_error_rows)
    run_config["completed_raw_rows"] = len(existing_raw_rows) + run_result["written_rows"]
    run_config["failed_rows"] = len(unresolved_error_rows) + run_result["failed_rows"]
    write_json(config_path, run_config)
    if run_config["failed_rows"] > 0:
        raise RuntimeError(
            f"LLM run finished with {run_config['failed_rows']} failed documents. "
            f"See {error_path} and rerun with --resume after adjusting workers/timeouts."
        )
    return 0


def _run_bestof_split_mode(
    args: argparse.Namespace,
    examples: list[DocumentExample],
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
    schema_version: str,
    split_config: dict[str, Any] | None,
) -> int:
    assert split_config is not None
    prompt_schema = PROMPT_SCHEMA_BY_MODE[args.prompt_mode]
    prompt_rows_by_label: dict[str, list[dict[str, Any]]] = {}
    few_shot_examples_by_label: dict[str, list[DocumentExample]] = {}
    existing_raw_rows_by_label: dict[str, list[dict[str, Any]]] = {}
    existing_error_rows_by_label: dict[str, list[dict[str, Any]]] = {}
    completed_subrequests: set[tuple[str, str]] = set()

    for label in PICO_LABELS:
        label_dir = output_dir / "labels" / label
        raw_label_path = label_dir / "raw.jsonl"
        error_label_path = label_dir / "errors.jsonl"
        existing_raw_rows = list(read_jsonl(raw_label_path)) if args.resume and raw_label_path.exists() else []
        existing_error_rows = list(read_jsonl(error_label_path)) if args.resume and error_label_path.exists() else []
        existing_raw_rows_by_label[label] = existing_raw_rows
        existing_error_rows_by_label[label] = existing_error_rows
        for row in existing_raw_rows:
            doc_id = row.get("doc_id")
            if isinstance(doc_id, str):
                completed_subrequests.add((doc_id, label))

    top_prompt_rows: list[dict[str, Any]] = []
    for example in examples:
        top_prompt_rows.append(
            {
                "doc_id": example.doc_id,
                "split_extraction": True,
                "subrequests": [{"label": label} for label in PICO_LABELS],
            }
        )
    write_jsonl(prompts_path, top_prompt_rows)

    for label in PICO_LABELS:
        label_prompt_version = split_config["label_prompt_versions"][label]
        prompt_template = _read_prompt_template(label_prompt_version)
        label_args = argparse.Namespace(**vars(args))
        label_args.few_shot_examples = split_config["label_few_shot_paths"][label]
        few_shot_examples = _select_few_shot_examples(label_args)
        few_shot_examples_by_label[label] = few_shot_examples
        prompt_rows = [
            _build_prompt_row(
                example=example,
                prompt_mode=args.prompt_mode,
                prompt_template=prompt_template,
                prompt_version=label_prompt_version,
                model_id=model_id,
                model_version=model_version,
                provider=args.provider,
                base_url=base_url,
                temperature=temperature,
                schema_version=schema_version,
                few_shot_examples=few_shot_examples,
                label_filter=label,
            )
            for example in examples
            if (example.doc_id, label) not in completed_subrequests
        ]
        for row in prompt_rows:
            row["label"] = label
            row["subrequest_id"] = f"{row['doc_id']}::{label}"
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
                "provider": args.provider,
                "model_id": model_id,
                "model_version": model_version,
                "base_url": base_url,
                "temperature": temperature,
                "timeout_seconds": timeout_seconds,
                "workers": args.workers,
                "max_retries": args.max_retries,
                "openai_client_max_retries": DEFAULT_OPENAI_CLIENT_MAX_RETRIES,
                "api_mode": api_mode,
                "prompt_mode": args.prompt_mode,
                "prompt_version": label_prompt_version,
                "schema_version": schema_version,
                "prompt_schema": prompt_schema,
                "api_date": API_DATE,
                "dry_run": args.dry_run,
                "resume": args.resume,
                "show_progress": args.show_progress,
                "split_extraction": True,
                "split_strategy": "bestof_pio_v1",
                "label": label,
                "label_output_key": BESTOF_SPLIT_LABEL_OUTPUT_KEYS[label],
                "label_prompt_versions": {label: label_prompt_version},
                "label_few_shot_paths": {label: split_config["label_few_shot_paths"][label]},
                "label_schema_versions": {label: schema_version},
                "input_paths": {
                    "examples": args.examples,
                    "provider_config": args.provider_config,
                    "few_shot_examples": split_config["label_few_shot_paths"][label],
                },
                "output_paths": {
                    "prompts": str(label_prompts_path),
                    "raw": str(label_raw_path),
                    "errors": str(label_error_path),
                    "run_config": str(label_config_path),
                },
                "limit": args.limit,
                "few_shot_doc_ids": [example.doc_id for example in few_shot_examples],
                "existing_raw_rows": len(existing_raw_rows_by_label[label]),
                "existing_error_rows": len(existing_error_rows_by_label[label]),
                "pending_prompt_rows": len(prompt_rows),
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    top_run_config = {
        "provider": args.provider,
        "model_id": model_id,
        "model_version": model_version,
        "base_url": base_url,
        "temperature": temperature,
        "timeout_seconds": timeout_seconds,
        "workers": args.workers,
        "max_retries": args.max_retries,
        "openai_client_max_retries": DEFAULT_OPENAI_CLIENT_MAX_RETRIES,
        "api_mode": api_mode,
        "prompt_mode": args.prompt_mode,
        "prompt_version": PROMPT_VERSION_BY_MODE[args.prompt_mode],
        "schema_version": schema_version,
        "prompt_schema": prompt_schema,
        "api_date": API_DATE,
        "dry_run": args.dry_run,
        "resume": args.resume,
        "show_progress": args.show_progress,
        "split_extraction": True,
        "split_strategy": "bestof_pio_v1",
        "label_prompt_versions": dict(split_config["label_prompt_versions"]),
        "label_few_shot_paths": dict(split_config["label_few_shot_paths"]),
        "label_schema_versions": {label: schema_version for label in PICO_LABELS},
        "input_paths": {
            "examples": args.examples,
            "provider_config": args.provider_config,
            "few_shot_examples": None,
        },
        "output_paths": {
            "prompts": str(prompts_path),
            "raw": str(raw_path),
            "errors": str(error_path),
            "run_config": str(config_path),
        },
        "limit": args.limit,
        "few_shot_doc_ids": {
            label: [example.doc_id for example in few_shot_examples_by_label[label]]
            for label in PICO_LABELS
        },
        "existing_raw_rows": sum(len(rows) for rows in existing_raw_rows_by_label.values()),
        "existing_error_rows": sum(len(rows) for rows in existing_error_rows_by_label.values()),
        "pending_prompt_rows": sum(len(rows) for rows in prompt_rows_by_label.values()),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(config_path, top_run_config)

    if args.dry_run:
        return 0
    if not api_key:
        raise RuntimeError(
            "OpenAI API key is required for non-dry-run execution. "
            "Set OPENAI_API_KEY or configure providers.openai.api_key/api_key_env."
        )

    for label in PICO_LABELS:
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
            prompt_schema=prompt_schema,
            api_mode=api_mode,
            workers=args.workers,
            show_progress=args.show_progress,
            max_retries=args.max_retries,
        )
        completed_doc_ids = {
            row["doc_id"]
            for row in read_jsonl(label_dir / "raw.jsonl")
            if isinstance(row.get("doc_id"), str)
        }
        unresolved_error_rows = [
            row
            for row in existing_error_rows_by_label[label]
            if isinstance(row.get("doc_id"), str) and row["doc_id"] not in completed_doc_ids
        ]
        if args.resume and (label_dir / "errors.jsonl").exists():
            write_jsonl(label_dir / "errors.jsonl", unresolved_error_rows)
        label_config_path = label_dir / "run_config.json"
        label_config = json.loads(label_config_path.read_text(encoding="utf-8"))
        label_config["completed_raw_rows"] = len(existing_raw_rows_by_label[label]) + run_result["written_rows"]
        label_config["failed_rows"] = len(unresolved_error_rows) + run_result["failed_rows"]
        write_json(label_config_path, label_config)

    aggregate = _aggregate_split_outputs(output_dir)
    write_jsonl(raw_path, aggregate["raw_rows"])
    write_jsonl(error_path, aggregate["error_rows"])
    top_run_config["completed_subrequests"] = aggregate["completed_subrequests"]
    top_run_config["failed_subrequests"] = aggregate["failed_subrequests"]
    top_run_config["completed_docs"] = aggregate["completed_docs"]
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
        raise FileExistsError(
            f"raw output exists without run_config: {raw_path}; remove it or restore {config_path}"
        )
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
    env_name = provider_settings.get("api_key_env", "OPENAI_API_KEY")
    if isinstance(env_name, str) and env_name:
        env_value = os.environ.get(env_name)
        if env_value:
            return env_value
    api_key = provider_settings.get("api_key")
    if isinstance(api_key, str) and api_key and not api_key.startswith("FILL_ME"):
        return api_key
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


def _select_few_shot_examples(args: argparse.Namespace) -> list[DocumentExample]:
    if args.prompt_mode in {
        "zero-shot",
        "zero-shot-text",
        "zero-shot-text-v2",
        "zero-shot-text-v3",
        "zero-shot-text-v3-i-only",
        "zero-shot-text-v4",
        "zero-shot-text-v4-i-only",
        "zero-shot-text-v5",
        "zero-shot-offsets",
    }:
        return []
    if args.few_shot_count < 0:
        raise ValueError("--few-shot-count must be non-negative")
    if not args.few_shot_examples:
        raise ValueError("--few-shot-examples is required for few-shot prompt modes that do not use built-in split defaults")
    return read_document_examples(args.few_shot_examples)[: args.few_shot_count]


def _build_prompt_row(
    example: DocumentExample,
    prompt_mode: str,
    prompt_template: str,
    prompt_version: str,
    model_id: str,
    model_version: str | None,
    provider: str,
    base_url: str,
    temperature: float,
    schema_version: str,
    few_shot_examples: list[DocumentExample],
    label_filter: str | None,
) -> dict[str, Any]:
    prompt_schema = PROMPT_SCHEMA_BY_MODE[prompt_mode]
    keyed_output_key = KEYED_OUTPUT_KEY_BY_PROMPT_VERSION.get(prompt_version)
    few_shot_block = _render_few_shot_block(
        few_shot_examples,
        prompt_schema,
        label_filter=label_filter,
        include_example_doc_id=prompt_version not in HIDE_FEWSHOT_EXAMPLE_DOC_ID_PROMPT_VERSIONS,
        keyed_output_key=keyed_output_key,
    )
    user_prompt = prompt_template.format(
        doc_id=example.doc_id,
        abstract=example.abstract,
        few_shot_examples=few_shot_block,
    )
    return {
        "doc_id": example.doc_id,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You extract exact PICO spans from randomized controlled trial abstracts. "
                    "Return only data that matches the provided JSON schema."
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
            "prompt_mode": prompt_mode,
            "prompt_version": prompt_version,
            "schema_version": schema_version,
            "prompt_schema": prompt_schema,
            "api_date": API_DATE,
            "few_shot_doc_ids": [shot.doc_id for shot in few_shot_examples],
            "label_filter": label_filter,
            "keyed_output_key": keyed_output_key,
        },
    }


def _render_few_shot_block(
    examples: list[DocumentExample],
    prompt_schema: str,
    label_filter: str | None,
    include_example_doc_id: bool,
    keyed_output_key: str | None,
) -> str:
    if not examples:
        return ""
    rendered: list[str] = []
    for example in examples:
        spans = []
        for span in example.gold_spans:
            if label_filter is not None and span.label != label_filter:
                continue
            item: Any = {"label": span.label, "text": span.text}
            if (
                prompt_schema == "offsets"
                and span.char_start is not None
                and span.char_end is not None
            ):
                item["char_start"] = span.char_start
                item["char_end"] = span.char_end
            spans.append(item)
        header = f"Example doc_id: {example.doc_id}\n" if include_example_doc_id else ""
        rendered_payload: Any = {"spans": spans}
        if keyed_output_key is not None:
            rendered_payload = {keyed_output_key: [span["text"] for span in spans]}
        rendered.append(
            "{header}Abstract:\n{abstract}\nExpected JSON:\n{spans}".format(
                header=header,
                abstract=example.abstract,
                spans=json.dumps(rendered_payload, ensure_ascii=False, sort_keys=True),
            )
        )
    return "\n\n".join(rendered)


def _call_openai(
    prompt_rows: list[dict[str, Any]],
    raw_path: Path,
    error_path: Path,
    api_key: str,
    base_url: str,
    model_id: str,
    temperature: float,
    timeout_seconds: float,
    prompt_schema: str,
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
                prompt_schema=prompt_schema,
                api_mode=api_mode,
                max_retries=max_retries,
            ): index
            for index, prompt_row in enumerate(prompt_rows)
        }
        for future in concurrent.futures.as_completed(futures):
            _index = futures[future]
            try:
                row = future.result()
            except Exception as exc:
                failed_rows += 1
                doc_id = prompt_rows[_index]["doc_id"]
                append_jsonl(
                    error_path,
                    [
                        {
                            "doc_id": doc_id,
                            "error_type": type(exc).__name__,
                            "message": str(exc),
                        }
                    ],
                )
                progress.failed(doc_id=doc_id, message=str(exc))
                continue
            append_jsonl(raw_path, [row])
            written_rows += 1
            progress.done(doc_id=row["doc_id"])
    progress.finish()
    return {"written_rows": written_rows, "failed_rows": failed_rows}


def _call_single_prompt(
    prompt_row: dict[str, Any],
    api_key: str,
    base_url: str,
    model_id: str,
    temperature: float,
    timeout_seconds: float,
    prompt_schema: str,
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
                prompt_schema=prompt_schema,
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
    prompt_row: dict[str, Any],
    api_key: str,
    base_url: str,
    model_id: str,
    temperature: float,
    timeout_seconds: float,
    prompt_schema: str,
    api_mode: str,
) -> dict[str, Any]:
    try:
        from openai import BadRequestError, OpenAI
        from openai import NotFoundError
    except ImportError as exc:
        raise RuntimeError("The openai package is required for Phase 8 LLM runs") from exc

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout_seconds,
        max_retries=DEFAULT_OPENAI_CLIENT_MAX_RETRIES,
    )
    request_mode = api_mode
    try:
        if request_mode == "responses":
            response = client.responses.create(
                model=model_id,
                input=prompt_row["messages"],
                temperature=temperature,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "pico_spans",
                        "schema": _response_schema(
                            prompt_schema,
                            prompt_row["metadata"].get("label_filter"),
                            prompt_row["metadata"].get("keyed_output_key"),
                        ),
                        "strict": True,
                    }
                },
            )
            parsed = _parse_response_text(
                response.output_text,
                keyed_output_key=prompt_row["metadata"].get("keyed_output_key"),
            )
            response_id = getattr(response, "id", None)
        else:
            parsed, response_id, request_mode = _call_chat_completions(
                client=client,
                prompt_row=prompt_row,
                model_id=model_id,
                temperature=temperature,
                prompt_schema=prompt_schema,
            )
    except NotFoundError:
        if request_mode != "responses":
            raise
        parsed, response_id, request_mode = _call_chat_completions(
            client=client,
            prompt_row=prompt_row,
            model_id=model_id,
            temperature=temperature,
            prompt_schema=prompt_schema,
        )
    except BadRequestError:
        if request_mode != "responses":
            raise
        parsed, response_id, request_mode = _call_chat_completions(
            client=client,
            prompt_row=prompt_row,
            model_id=model_id,
            temperature=temperature,
            prompt_schema=prompt_schema,
        )
    return {
        "doc_id": prompt_row["doc_id"],
        "response": json.dumps(
            _normalize_response_items(
                parsed["spans"],
                prompt_row["metadata"].get("label_filter"),
                prompt_row["metadata"].get("keyed_output_key"),
            ),
            ensure_ascii=False,
            sort_keys=True,
        ),
        "metadata": {
            **prompt_row["metadata"],
            "api_mode": request_mode,
            "openai_response_id": response_id,
        },
    }


def _call_chat_completions(
    client: Any,
    prompt_row: dict[str, Any],
    model_id: str,
    temperature: float,
    prompt_schema: str,
) -> tuple[dict[str, Any], Any, str]:
    try:
        from openai import BadRequestError
    except ImportError as exc:
        raise RuntimeError("The openai package is required for Phase 8 LLM runs") from exc

    attempts: list[tuple[str, dict[str, Any] | None]] = [
        (
            "chat_completions_json_schema",
            {
                "type": "json_schema",
                "json_schema": {
                    "name": "pico_spans",
                    "schema": _response_schema(
                        prompt_schema,
                        prompt_row["metadata"].get("label_filter"),
                        prompt_row["metadata"].get("keyed_output_key"),
                    ),
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
        return (
            _parse_response_text(
                content,
                keyed_output_key=prompt_row["metadata"].get("keyed_output_key"),
            ),
            getattr(response, "id", None),
            mode_name,
        )
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

    def done(self, doc_id: str) -> None:
        if not self.enabled:
            return
        with self._lock:
            self.completed += 1
            print(
                f"[run_llm] completed {self.completed}/{self.total} doc_id={doc_id}",
                file=sys.stderr,
                flush=True,
            )

    def failed(self, doc_id: str, message: str) -> None:
        if not self.enabled:
            return
        with self._lock:
            self.completed += 1
            print(
                f"[run_llm] failed {self.completed}/{self.total} doc_id={doc_id} error={message}",
                file=sys.stderr,
                flush=True,
            )

    def finish(self) -> None:
        if not self.enabled:
            return
        print(f"[run_llm] finished {self.completed}/{self.total}", file=sys.stderr, flush=True)


def _response_schema(
    prompt_schema: str,
    label_filter: str | None = None,
    keyed_output_key: str | None = None,
) -> dict[str, Any]:
    if keyed_output_key is not None:
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
    allowed_labels = [label_filter] if label_filter is not None else list(PICO_LABELS)
    item_properties: dict[str, Any] = {
        "label": {"type": "string", "enum": allowed_labels},
        "text": {"type": "string"},
    }
    required = ["label", "text"]
    if prompt_schema == "offsets":
        item_properties["char_start"] = {"type": "integer", "minimum": 0}
        item_properties["char_end"] = {"type": "integer", "minimum": 0}
        required.extend(["char_start", "char_end"])
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "spans": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": item_properties,
                    "required": required,
                },
            }
        },
        "required": ["spans"],
    }


def _parse_response_text(output_text: str, keyed_output_key: str | None = None) -> dict[str, Any]:
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
    if keyed_output_key is not None:
        if isinstance(parsed, dict) and isinstance(parsed.get(keyed_output_key), list):
            return {"spans": parsed[keyed_output_key]}
        for invalid_key in BESTOF_SPLIT_LABEL_OUTPUT_KEYS.values():
            if invalid_key == keyed_output_key:
                continue
            if isinstance(parsed, dict) and invalid_key in parsed:
                raise ValueError(
                    f"OpenAI response must use the {keyed_output_key!r} key, not {invalid_key!r}"
                )
        raise ValueError(f"OpenAI response must be an object with a {keyed_output_key!r} array")
    if isinstance(parsed, list):
        parsed = {"spans": parsed}
    if not isinstance(parsed, dict) or not isinstance(parsed.get("spans"), list):
        raise ValueError("OpenAI response must be an object with a spans array")
    return parsed


def _normalize_response_items(
    items: list[Any],
    label_filter: Any,
    keyed_output_key: str | None,
) -> list[dict[str, str]]:
    if keyed_output_key is None:
        return items
    if not isinstance(label_filter, str) or not label_filter:
        raise ValueError(f"{keyed_output_key}-key responses require a string label_filter")
    normalized: list[dict[str, str]] = []
    for item in items:
        if isinstance(item, str):
            normalized.append({"label": label_filter, "text": item})
            continue
        if isinstance(item, dict):
            text = item.get("text")
            if isinstance(text, str):
                normalized.append({"label": label_filter, "text": text})
                continue
        raise ValueError(
            f"{keyed_output_key}-key response items must be strings or objects with string text"
        )
    return normalized


def _strip_markdown_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if not lines:
        return stripped
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _extract_first_json_value(text: str) -> Any | None:
    decoder = json.JSONDecoder()
    for idx, ch in enumerate(text):
        if ch not in "{[":
            continue
        try:
            value, _end = decoder.raw_decode(text[idx:])
        except json.JSONDecodeError:
            continue
        return value
    return None


def _aggregate_split_outputs(output_dir: Path) -> dict[str, Any]:
    rows_by_doc: dict[str, dict[str, dict[str, Any]]] = {}
    errors_by_doc: dict[str, dict[str, dict[str, Any]]] = {}
    completed_subrequests: list[str] = []
    failed_subrequests: list[str] = []

    for label in PICO_LABELS:
        label_dir = output_dir / "labels" / label
        raw_path = label_dir / "raw.jsonl"
        error_path = label_dir / "errors.jsonl"
        if raw_path.exists():
            for row in read_jsonl(raw_path):
                doc_id = row.get("doc_id")
                if isinstance(doc_id, str):
                    rows_by_doc.setdefault(doc_id, {})[label] = row
                    completed_subrequests.append(f"{doc_id}::{label}")
        if error_path.exists():
            for row in read_jsonl(error_path):
                doc_id = row.get("doc_id")
                if isinstance(doc_id, str):
                    errors_by_doc.setdefault(doc_id, {})[label] = row
                    failed_subrequests.append(f"{doc_id}::{label}")

    raw_rows: list[dict[str, Any]] = []
    error_rows: list[dict[str, Any]] = []
    completed_docs: list[str] = []
    all_doc_ids = sorted(set(rows_by_doc) | set(errors_by_doc))
    for doc_id in all_doc_ids:
        label_rows = rows_by_doc.get(doc_id, {})
        if all(label in label_rows for label in PICO_LABELS):
            merged: list[dict[str, Any]] = []
            label_metadata: dict[str, Any] = {}
            parse_failed = False
            for label in PICO_LABELS:
                row = label_rows[label]
                label_metadata[label] = row.get("metadata", {})
                parsed = json.loads(row["response"])
                if not isinstance(parsed, list):
                    parse_failed = True
                    break
                merged.extend(parsed)
            if not parse_failed:
                raw_rows.append(
                    {
                        "doc_id": doc_id,
                        "response": json.dumps(merged, ensure_ascii=False, sort_keys=True),
                        "metadata": {
                            "split_extraction": True,
                            "split_strategy": "bestof_pio_v1",
                            "label_metadata": label_metadata,
                        },
                    }
                )
                completed_docs.append(doc_id)
                continue
        missing_labels = [label for label in PICO_LABELS if label not in label_rows]
        error_rows.append(
            {
                "doc_id": doc_id,
                "error_type": "SplitDocumentIncomplete",
                "message": "Not all label subrequests completed successfully",
                "failed_labels": missing_labels,
                "label_errors": errors_by_doc.get(doc_id, {}),
            }
        )

    return {
        "raw_rows": raw_rows,
        "error_rows": error_rows,
        "completed_subrequests": sorted(set(completed_subrequests)),
        "failed_subrequests": sorted(set(failed_subrequests)),
        "completed_docs": sorted(completed_docs),
    }


if __name__ == "__main__":
    raise SystemExit(main())
