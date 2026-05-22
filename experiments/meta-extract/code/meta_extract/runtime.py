"""Runtime helpers for task-based experiment execution."""

from __future__ import annotations

import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .constants import RUN_SUBDIRS, TASK_SPECS
from .io_utils import atomic_write_text, ensure_dir, iter_jsonl, write_json


class ProgressPrinter:
    def __init__(self, *, enabled: bool, label: str, total: int, skipped: int = 0, failed: int = 0):
        self.enabled = enabled
        self.label = label
        self.total = total
        self.skipped = skipped
        self.failed = failed
        self.completed = 0
        self._lock = threading.Lock()
        if self.enabled:
            self._print()

    def step(self, *, failed: bool = False) -> None:
        if not self.enabled:
            return
        with self._lock:
            self.completed += 1
            if failed:
                self.failed += 1
            self._print()

    def close(self) -> None:
        if self.enabled:
            sys.stderr.write("\n")
            sys.stderr.flush()

    def _print(self) -> None:
        sys.stderr.write(
            f"\r[{self.label}] completed={self.completed}/{self.total} skipped={self.skipped} failed={self.failed}"
        )
        sys.stderr.flush()


@dataclass(frozen=True)
class TaskPaths:
    task_name: str
    run_dir: Path
    instances_path: Path
    predictions_path: Path
    run_summary_path: Path
    failed_instances_path: Path
    scores_path: Path
    task_summary_path: Path


RunFn = Callable[[dict], dict]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_run_dir(run_dir: str | Path) -> Path:
    run_root = ensure_dir(run_dir)
    for subdir in RUN_SUBDIRS:
        ensure_dir(run_root / subdir)
    return run_root


def resolve_task_paths(*, task_name: str, run_dir: str | Path) -> TaskPaths:
    spec = TASK_SPECS[task_name]
    run_root = ensure_run_dir(run_dir)
    return TaskPaths(
        task_name=task_name,
        run_dir=run_root,
        instances_path=run_root / "instances" / spec["instance_filename"],
        predictions_path=run_root / "predictions" / spec["prediction_filename"],
        run_summary_path=run_root / "predictions" / spec["run_summary_filename"],
        failed_instances_path=run_root / "predictions" / spec["failed_filename"],
        scores_path=run_root / "scores" / spec["score_filename"],
        task_summary_path=run_root / "scores" / spec["summary_filename"],
    )


def append_jsonl_row(path: str | Path, row: dict) -> None:
    path_obj = Path(path)
    ensure_dir(path_obj.parent)
    with path_obj.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True))
        handle.write("\n")


def initialize_output_file(path: str | Path, *, resume: bool) -> None:
    path_obj = Path(path)
    ensure_dir(path_obj.parent)
    if not resume:
        atomic_write_text(path_obj, "")


def load_completed_instance_ids(path: str | Path) -> set[str]:
    completed = set()
    for row in iter_jsonl(path) or []:
        instance_id = row.get("instance_id")
        if instance_id:
            completed.add(instance_id)
    return completed


def load_failed_rows(path: str | Path) -> list[dict]:
    return list(iter_jsonl(path) or [])


def write_manifest(path: str | Path, payload: dict) -> None:
    write_json(path, payload)


def execute_task_run(
    *,
    task_name: str,
    rows: list[dict],
    run_dir: str | Path,
    predict_fn: RunFn,
    run_metadata: dict,
    num_workers: int = 1,
    resume: bool = False,
    flush_every: int = 1,
    continue_on_error: bool = True,
    max_attempts: int = 1,
    show_progress: bool = True,
    instance_source_path: str | Path | None = None,
) -> dict:
    task_paths = resolve_task_paths(task_name=task_name, run_dir=run_dir)
    existing_ids = load_completed_instance_ids(task_paths.predictions_path) if resume else set()
    pending_rows = [row for row in rows if row.get("instance_id") not in existing_ids]
    initialize_output_file(task_paths.predictions_path, resume=resume)
    initialize_output_file(task_paths.failed_instances_path, resume=resume)

    progress = ProgressPrinter(
        enabled=show_progress,
        label=task_name,
        total=len(pending_rows),
        skipped=len(existing_ids),
    )
    counts = {
        "completed": 0,
        "failed": 0,
        "skipped": len(existing_ids),
    }
    lock = threading.Lock()
    failure_rows: list[dict] = []

    def run_one(row: dict) -> tuple[dict | None, dict | None]:
        last_error = None
        for attempt in range(1, max_attempts + 1):
            try:
                result = predict_fn(row)
                return result, None
            except Exception as exc:  # pragma: no cover
                last_error = {
                    "instance_id": row.get("instance_id"),
                    "task_name": task_name,
                    "attempt": attempt,
                    "error": repr(exc),
                }
        assert last_error is not None
        return None, last_error

    def persist_failure(failure: dict) -> None:
        failure_rows.append(failure)
        append_jsonl_row(task_paths.failed_instances_path, failure)

    try:
        if num_workers <= 1:
            for row in pending_rows:
                result, failure = run_one(row)
                if failure is not None:
                    counts["failed"] += 1
                    persist_failure(failure)
                    progress.step(failed=True)
                    if not continue_on_error:
                        raise RuntimeError(failure["error"])
                    continue
                append_jsonl_row(task_paths.predictions_path, result)
                counts["completed"] += 1
                progress.step()
        else:
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = {executor.submit(run_one, row): row for row in pending_rows}
                for future in as_completed(futures):
                    result, failure = future.result()
                    with lock:
                        if failure is not None:
                            counts["failed"] += 1
                            persist_failure(failure)
                            progress.step(failed=True)
                            if not continue_on_error:
                                raise RuntimeError(failure["error"])
                            continue
                        append_jsonl_row(task_paths.predictions_path, result)
                        counts["completed"] += 1
                        progress.step()
    finally:
        progress.close()

    summary = {
        **run_metadata,
        "task_name": task_name,
        "run_dir": str(task_paths.run_dir),
        "instance_source_path": str(instance_source_path) if instance_source_path else str(task_paths.instances_path),
        "instances": len(rows),
        "pending_instances": len(pending_rows),
        "completed_now": counts["completed"],
        "failed_now": counts["failed"],
        "skipped_existing": counts["skipped"],
        "resume": resume,
        "continue_on_error": continue_on_error,
        "max_attempts": max_attempts,
        "num_workers": num_workers,
        "flush_every": flush_every,
        "started_at": run_metadata.get("started_at", utc_now_iso()),
        "finished_at": utc_now_iso(),
        "prediction_path": str(task_paths.predictions_path),
        "failed_instances_path": str(task_paths.failed_instances_path),
        "failure_count": len(failure_rows),
    }
    write_json(task_paths.run_summary_path, summary)
    return summary
