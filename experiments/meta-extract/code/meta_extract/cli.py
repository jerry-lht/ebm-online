"""CLI entrypoints for benchmark2-v2 experiments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .instances import prepare_instances
from .llm_backend import default_model_name, make_client
from .predictors import (
    DEFAULT_PROMPT_VARIANT,
    rerun_failures,
    run_oracle_extraction,
    run_proposal,
    run_routed_extraction,
    run_support,
)
from .reporting import build_report
from .runtime import ensure_run_dir, resolve_task_paths, write_manifest
from .scoring import score_all, score_oracle_extraction, score_proposal, score_routed_extraction, score_support


def _add_runtime_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--split")
    parser.add_argument("--mode", default="llm", choices=["oracle", "empty", "llm"])
    parser.add_argument("--prompt-variant", default=DEFAULT_PROMPT_VARIANT)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--num-workers", type=int, default=1)
    parser.add_argument("--flush-every", type=int, default=1)
    parser.add_argument("--continue-on-error", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--max-attempts", type=int, default=1)
    parser.add_argument("--no-progress", action="store_true")


def _resolve_run_dir(run_dir: str | None, output_dir: str | None) -> Path:
    resolved = run_dir or output_dir
    if not resolved:
        raise ValueError("One of --run-dir or --output-dir is required")
    return ensure_run_dir(resolved)


def prepare_data_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-path", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--dev-fraction", type=float, default=0.2)
    parser.add_argument("--split-seed", default="meta-extract-benchmark2-v2-split-v1")
    parser.add_argument("--max-samples", type=int)
    parser.add_argument("--max-settings", type=int)
    parser.add_argument("--target-split", choices=["dev", "test"])
    parser.add_argument("--evidence-mode", default="full-text")
    args = parser.parse_args(argv)
    prepare_instances(
        dataset_path=args.dataset_path,
        output_dir=args.output_dir,
        dev_fraction=args.dev_fraction,
        split_seed=args.split_seed,
        max_samples=args.max_samples,
        max_settings=args.max_settings,
        target_split=args.target_split,
        evidence_mode=args.evidence_mode,
    )
    return 0


def _run_main(argv: list[str] | None, *, task_name: str, runner, default_filename: str) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instances-path")
    parser.add_argument("--run-dir")
    parser.add_argument("--output-dir")
    _add_runtime_args(parser)
    args = parser.parse_args(argv)
    run_dir = _resolve_run_dir(args.run_dir, args.output_dir)
    task_paths = resolve_task_paths(task_name=task_name, run_dir=run_dir)
    instances_path = Path(args.instances_path) if args.instances_path else task_paths.instances_path
    summary = runner(
        instances_path=instances_path,
        run_dir=run_dir,
        split=args.split,
        mode=args.mode,
        prompt_variant=args.prompt_variant,
        num_workers=args.num_workers,
        resume=args.resume,
        flush_every=args.flush_every,
        continue_on_error=args.continue_on_error,
        max_attempts=args.max_attempts,
        show_progress=not args.no_progress,
    )
    write_manifest(run_dir / "manifests" / f"{task_name}_latest_command.json", {"task_name": task_name, "instances_path": str(instances_path), "summary": summary})
    return 0


def run_support_main(argv: list[str] | None = None) -> int:
    return _run_main(argv, task_name="support", runner=run_support, default_filename="support_instances.jsonl")


def run_proposal_main(argv: list[str] | None = None) -> int:
    return _run_main(argv, task_name="proposal", runner=run_proposal, default_filename="proposal_instances.jsonl")


def run_oracle_extraction_main(argv: list[str] | None = None) -> int:
    return _run_main(argv, task_name="oracle_extraction", runner=run_oracle_extraction, default_filename="oracle_extraction_instances.jsonl")


def run_routed_extraction_main(argv: list[str] | None = None) -> int:
    return _run_main(argv, task_name="routed_extraction", runner=run_routed_extraction, default_filename="routed_extraction_instances.jsonl")


def score_support_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instances-path")
    parser.add_argument("--predictions-path")
    parser.add_argument("--run-dir")
    parser.add_argument("--output-dir")
    args = parser.parse_args(argv)
    run_dir = _resolve_run_dir(args.run_dir, args.output_dir)
    task_paths = resolve_task_paths(task_name="support", run_dir=run_dir)
    score_support(instances_path=Path(args.instances_path) if args.instances_path else task_paths.instances_path, predictions_path=Path(args.predictions_path) if args.predictions_path else task_paths.predictions_path, output_dir=run_dir / "scores")
    return 0


def score_proposal_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instances-path")
    parser.add_argument("--predictions-path")
    parser.add_argument("--run-dir")
    parser.add_argument("--output-dir")
    args = parser.parse_args(argv)
    run_dir = _resolve_run_dir(args.run_dir, args.output_dir)
    task_paths = resolve_task_paths(task_name="proposal", run_dir=run_dir)
    score_proposal(instances_path=Path(args.instances_path) if args.instances_path else task_paths.instances_path, predictions_path=Path(args.predictions_path) if args.predictions_path else task_paths.predictions_path, output_dir=run_dir / "scores")
    return 0


def score_oracle_extraction_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instances-path")
    parser.add_argument("--predictions-path")
    parser.add_argument("--run-dir")
    parser.add_argument("--output-dir")
    args = parser.parse_args(argv)
    run_dir = _resolve_run_dir(args.run_dir, args.output_dir)
    task_paths = resolve_task_paths(task_name="oracle_extraction", run_dir=run_dir)
    score_oracle_extraction(instances_path=Path(args.instances_path) if args.instances_path else task_paths.instances_path, predictions_path=Path(args.predictions_path) if args.predictions_path else task_paths.predictions_path, output_dir=run_dir / "scores")
    return 0


def score_routed_extraction_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instances-path")
    parser.add_argument("--predictions-path")
    parser.add_argument("--run-dir")
    parser.add_argument("--output-dir")
    args = parser.parse_args(argv)
    run_dir = _resolve_run_dir(args.run_dir, args.output_dir)
    task_paths = resolve_task_paths(task_name="routed_extraction", run_dir=run_dir)
    score_routed_extraction(instances_path=Path(args.instances_path) if args.instances_path else task_paths.instances_path, predictions_path=Path(args.predictions_path) if args.predictions_path else task_paths.predictions_path, output_dir=run_dir / "scores")
    return 0


def score_all_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args(argv)
    score_all(run_dir=args.run_dir)
    return 0


def build_report_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--score-dir")
    parser.add_argument("--run-dir")
    parser.add_argument("--output-path")
    parser.add_argument("--output-dir")
    args = parser.parse_args(argv)
    if args.run_dir:
        run_dir = Path(args.run_dir)
        score_dir = run_dir / "scores"
        output_path = Path(args.output_path or args.output_dir or (run_dir / "reports"))
    else:
        score_dir = Path(args.score_dir)
        output_path = Path(args.output_path or args.output_dir)
    build_report(score_dir=score_dir, output_path=output_path)
    return 0


def rerun_failures_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, choices=["support", "proposal", "oracle_extraction", "routed_extraction"])
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--mode", default="llm", choices=["oracle", "empty", "llm"])
    parser.add_argument("--prompt-variant", default=DEFAULT_PROMPT_VARIANT)
    parser.add_argument("--num-workers", type=int, default=1)
    parser.add_argument("--flush-every", type=int, default=1)
    parser.add_argument("--continue-on-error", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--max-attempts", type=int, default=1)
    parser.add_argument("--no-progress", action="store_true")
    args = parser.parse_args(argv)
    rerun_failures(task_name=args.task, run_dir=args.run_dir, mode=args.mode, prompt_variant=args.prompt_variant, num_workers=args.num_workers, flush_every=args.flush_every, continue_on_error=args.continue_on_error, max_attempts=args.max_attempts, show_progress=not args.no_progress)
    return 0


def llm_ping_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=default_model_name())
    parser.add_argument("--prompt", default='Reply with compact JSON only: {"ok": true}')
    args = parser.parse_args(argv)
    client = make_client()
    response = client.chat.completions.create(
        model=args.model,
        messages=[{"role": "system", "content": "Return plain text only."}, {"role": "user", "content": args.prompt}],
        temperature=0,
    )
    print(json.dumps({"model": args.model, "content": response.choices[0].message.content}, ensure_ascii=True))
    return 0
