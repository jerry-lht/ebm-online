"""Evaluate q2pico predictions using an LLM rubric judge."""

from __future__ import annotations

import argparse
import csv
import os
import tempfile
from pathlib import Path
from typing import Any

from q2pico.config import get_provider_config, load_config
from q2pico.io_utils import read_question_examples, read_slot_predictions, write_jsonl, write_metrics
from q2pico.judge_evaluate import (
    DEFAULT_BASE_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_WORKERS,
    JUDGE_EVALUATOR_VERSION,
    JUDGE_PROMPT_VERSION,
    build_judge_inputs,
    run_llm_judge,
    summarize_judge_rows_for_labels,
)
from q2pico.schemas import parse_label_scope


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate q2pico predictions with an LLM rubric judge.")
    parser.add_argument("--gold", required=True, help="Gold question examples JSONL.")
    parser.add_argument("--pred", required=True, help="Validated slot prediction JSONL.")
    parser.add_argument("--provider-config", help="Optional JSON/YAML provider config path.")
    parser.add_argument("--provider", default="openai", choices=("openai",))
    parser.add_argument("--model-id", help="Judge model id. Overrides provider config model_id.")
    parser.add_argument("--output", required=True, help="Per-question judge JSONL output path.")
    parser.add_argument("--summary-output", required=True, help="Judge summary JSON output path.")
    parser.add_argument("--method", default="llm")
    parser.add_argument("--setting", default="default")
    parser.add_argument("--split", default="test59")
    parser.add_argument("--labels", default="P,I,C,O", help="Comma-separated label scope, e.g. P,I")
    parser.add_argument("--tables-dir", default="results/tables")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    parser.add_argument("--resume", action="store_true", help="Skip question_ids already present in --output.")
    parser.add_argument("--show-progress", action="store_true", help="Print simple progress updates to stderr.")
    parser.add_argument("--force", action="store_true", help="Replace existing table rows for this run key.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.workers <= 0:
        raise ValueError("--workers must be positive")
    if args.max_retries < 0:
        raise ValueError("--max-retries must be non-negative")

    examples = read_question_examples(args.gold)
    predictions = read_slot_predictions(args.pred)
    labels = parse_label_scope(args.labels)
    judge_inputs = build_judge_inputs(examples, predictions, labels=labels)

    existing_rows_by_question_id: dict[str, dict[str, Any]] = {}
    if args.resume and Path(args.output).exists():
        for row in _read_jsonl_if_exists(args.output):
            question_id = row.get("question_id")
            if isinstance(question_id, str):
                existing_rows_by_question_id[question_id] = row
        if existing_rows_by_question_id:
            judge_inputs = [item for item in judge_inputs if item.question_id not in existing_rows_by_question_id]

    provider_settings = _load_provider_settings(args.provider_config, args.provider)
    model_id = args.model_id or provider_settings.get("model_id")
    if not isinstance(model_id, str) or not model_id:
        raise RuntimeError("Judge model id is required. Pass --model-id or set providers.openai.model_id.")
    base_url = str(provider_settings.get("base_url") or DEFAULT_BASE_URL)
    api_key = _resolve_api_key(provider_settings)
    if not api_key:
        raise RuntimeError(
            "OpenAI API key is required. Set OPENAI_API_KEY or configure providers.openai.api_key/api_key_env."
        )
    api_mode = _resolve_api_mode(provider_settings, base_url)

    new_rows, failures = run_llm_judge(
        judge_inputs,
        provider=args.provider,
        model_id=model_id,
        api_key=api_key,
        base_url=base_url,
        timeout_seconds=float(args.timeout_seconds),
        workers=int(args.workers),
        max_retries=int(args.max_retries),
        api_mode=api_mode,
        prompt_version=JUDGE_PROMPT_VERSION,
        show_progress=args.show_progress,
        labels=labels,
    )

    merged_by_question_id = {**existing_rows_by_question_id}
    for row in new_rows:
        merged_by_question_id[row["question_id"]] = row
    ordered_question_ids = [example.question_id for example in examples]
    merged_rows = [merged_by_question_id[qid] for qid in ordered_question_ids if qid in merged_by_question_id]
    write_jsonl(args.output, merged_rows)

    summary = summarize_judge_rows_for_labels(merged_rows, labels=labels)
    summary.update(
        {
            "judge_evaluator_version": JUDGE_EVALUATOR_VERSION,
            "judge_prompt_version": JUDGE_PROMPT_VERSION,
            "inputs": {
                "gold_path": args.gold,
                "pred_path": args.pred,
                "provider_config": args.provider_config,
            },
            "outputs": {
                "judge_path": args.output,
                "summary_path": args.summary_output,
            },
            "method": args.method,
            "setting": args.setting,
            "split": args.split,
            "labels": list(labels),
            "runtime": {
                "provider": args.provider,
                "judge_model": model_id,
                "base_url": base_url,
                "api_mode": api_mode,
                "workers": args.workers,
                "timeout_seconds": args.timeout_seconds,
                "max_retries": args.max_retries,
                "resume": args.resume,
            },
            "counts": {
                **summary.get("counts", {}),
                "existing_rows": len(existing_rows_by_question_id),
                "new_rows": len(new_rows),
                "failed_rows": len(failures),
            },
            "failures": [
                {
                    "question_id": failure.question_id,
                    "error_type": failure.error_type,
                    "message": failure.message,
                }
                for failure in failures
            ],
        }
    )
    write_metrics(args.summary_output, summary)
    _write_tables(
        tables_dir=Path(args.tables_dir),
        summary=summary,
        method=args.method,
        setting=args.setting,
        split=args.split,
        pred_path=args.pred,
        judge_path=args.output,
        summary_path=args.summary_output,
        force=args.force,
    )
    if failures:
        preview = "; ".join(
            f"question_id={failure.question_id} error={failure.message}"
            for failure in failures[:3]
        )
        raise RuntimeError(f"LLM judge failed for {len(failures)} questions. {preview}")
    return 0


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


def _write_tables(
    *,
    tables_dir: Path,
    summary: dict[str, Any],
    method: str,
    setting: str,
    split: str,
    pred_path: str,
    judge_path: str,
    summary_path: str,
    force: bool,
) -> None:
    base = {
        "method": method,
        "setting": setting,
        "split": split,
        "pred_path": pred_path,
        "judge_path": judge_path,
        "summary_path": summary_path,
        "judge_evaluator_version": summary["judge_evaluator_version"],
        "judge_prompt_version": summary["judge_prompt_version"],
    }
    per_label_rows: list[dict[str, Any]] = []
    for label, dimensions in summary["per_label"].items():
        for dimension, distribution in dimensions.items():
            for value, stats in distribution.items():
                per_label_rows.append(
                    {
                        **base,
                        "label": label,
                        "dimension": dimension,
                        "value": value,
                        "count": stats["count"],
                        "rate": stats["rate"],
                    }
                )
    _upsert_rows(tables_dir / "llm_judge_per_label.csv", per_label_rows, force)

    overall_rows: list[dict[str, Any]] = []
    for dimension, distribution in summary["overall"].items():
        for value, stats in distribution.items():
            overall_rows.append(
                {
                    **base,
                    "dimension": dimension,
                    "value": value,
                    "count": stats["count"],
                    "rate": stats["rate"],
                }
            )
    _upsert_rows(tables_dir / "llm_judge_overall.csv", overall_rows, force)


def _upsert_rows(path: Path, new_rows: list[dict[str, Any]], force: bool) -> None:
    if not new_rows:
        return
    fieldnames = list(new_rows[0].keys())
    rows = _read_csv_rows(path, fieldnames)
    new_keys = {_row_key(row) for row in new_rows}
    existing_conflicts = [row for row in rows if _row_key(row) in new_keys]
    if existing_conflicts and not force:
        conflict = existing_conflicts[0]
        raise ValueError(
            "Table row already exists for "
            f"{conflict['method']}/{conflict['setting']}/{conflict['split']}/"
            f"{conflict['pred_path']}/{conflict.get('label', 'overall')}/"
            f"{conflict['dimension']}/{conflict['value']}; pass --force to replace"
        )
    rows = [row for row in rows if _row_key(row) not in new_keys]
    rows.extend(new_rows)
    _atomic_write_csv(path, fieldnames, rows)


def _read_csv_rows(path: Path, fieldnames: list[str]) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != fieldnames:
            raise ValueError(f"Unexpected CSV header in {path}: {reader.fieldnames}")
        return list(reader)


def _atomic_write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="",
        dir=path.parent,
        delete=False,
    ) as handle:
        temp_name = handle.name
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temp_name, path)


def _row_key(row: dict[str, Any]) -> tuple[str, str, str, str, str, str, str]:
    return (
        str(row["method"]),
        str(row["setting"]),
        str(row["split"]),
        str(row["pred_path"]),
        str(row.get("label", "overall")),
        str(row["dimension"]),
        str(row["value"]),
    )


def _read_jsonl_if_exists(path: str | Path) -> list[dict[str, Any]]:
    path_obj = Path(path)
    if not path_obj.exists():
        return []
    with path_obj.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
