"""In-memory pipeline run state management for the simplified Phase 5 API."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Any


class PipelineStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PipelineStepTrace:
    name: str
    status: StepStatus = StepStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    summary: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class PipelineRunState:
    run_id: str
    question: str
    status: PipelineStatus = PipelineStatus.PENDING
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    completed_at: datetime | None = None
    top_k: int = 5
    use_mock: bool = False
    index_path: str | None = None
    steps: list[PipelineStepTrace] = field(default_factory=list)
    result: dict[str, Any] | None = None
    error: str | None = None


class InMemoryPipelineStore:
    """Small process-local store used until database-backed run state exists."""

    def __init__(self):
        self._runs: dict[str, PipelineRunState] = {}
        self._lock = Lock()

    def create(self, run: PipelineRunState) -> PipelineRunState:
        with self._lock:
            self._runs[run.run_id] = run
            return run

    def get(self, run_id: str) -> PipelineRunState | None:
        with self._lock:
            return self._runs.get(run_id)

    def list(self) -> list[PipelineRunState]:
        with self._lock:
            return list(self._runs.values())

    def save(self, run: PipelineRunState) -> PipelineRunState:
        run.updated_at = utc_now()
        with self._lock:
            self._runs[run.run_id] = run
            return run


DEFAULT_PIPELINE_STORE = InMemoryPipelineStore()
