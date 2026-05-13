"""Pipeline API routes for the simplified Phase 5 backend."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from ebm_backend.online_pipeline.application.run_pipeline import DEFAULT_LOCAL_INDEX_PATH, PipelineOrchestrator
from ebm_backend.online_pipeline.infrastructure.pipeline_repository import DEFAULT_PIPELINE_STORE, PipelineRunState


router = APIRouter(prefix="/pipeline", tags=["pipeline"])


class PipelineRunCreate(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    use_mock: bool = False
    index_path: str | None = None


class PipelineRunSummary(BaseModel):
    run_id: str
    status: str
    question: str
    top_k: int
    use_mock: bool
    index_path: str | None
    step_count: int
    error: str | None = None


@router.post("/runs", response_model=PipelineRunSummary)
async def create_pipeline_run(request: PipelineRunCreate, background_tasks: BackgroundTasks) -> PipelineRunSummary:
    orchestrator = PipelineOrchestrator(
        store=DEFAULT_PIPELINE_STORE,
        index_path=Path(request.index_path or DEFAULT_LOCAL_INDEX_PATH),
    )
    run = orchestrator.create_pending_run(
        question=request.question,
        top_k=request.top_k,
        use_mock=request.use_mock,
        index_path=request.index_path,
    )
    background_tasks.add_task(_run_pipeline_background, orchestrator, run)
    return _summary(run)


@router.get("/runs", response_model=list[PipelineRunSummary])
def list_pipeline_runs() -> list[PipelineRunSummary]:
    return [_summary(run) for run in DEFAULT_PIPELINE_STORE.list()]


@router.get("/runs/{run_id}")
def get_pipeline_run(run_id: str) -> dict[str, Any]:
    run = _get_run_or_404(run_id)
    payload = asdict(run)
    payload["steps"] = [
        {
            "name": step.name,
            "status": step.status,
            "started_at": step.started_at,
            "completed_at": step.completed_at,
            "summary": step.summary,
            "error": step.error,
        }
        for step in run.steps
    ]
    return payload


@router.get("/runs/{run_id}/trace")
def get_pipeline_trace(run_id: str) -> dict[str, Any]:
    run = _get_run_or_404(run_id)
    return {
        "run": _summary(run).model_dump(),
        "steps": [asdict(step) for step in run.steps],
        "result": run.result,
    }


@router.get("/runs/{run_id}/results")
def get_pipeline_results(run_id: str) -> dict[str, Any]:
    run = _get_run_or_404(run_id)
    if run.result is None:
        return {
            "run": _summary(run).model_dump(),
            "result": None,
        }
    return {
        "run": _summary(run).model_dump(),
        "result": {
            "candidates": run.result.get("candidates", []),
            "screening": run.result.get("screening"),
            "planning": run.result.get("planning"),
            "extraction": run.result.get("extraction"),
            "risk_of_bias": run.result.get("risk_of_bias"),
            "aggregation": run.result.get("aggregation"),
            "grade": run.result.get("grade"),
            "warnings": run.result.get("warnings", []),
        },
    }


def _get_run_or_404(run_id: str) -> PipelineRunState:
    run = DEFAULT_PIPELINE_STORE.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Pipeline run not found: {run_id}")
    return run


def _run_pipeline_background(orchestrator: PipelineOrchestrator, run: PipelineRunState) -> None:
    import asyncio

    asyncio.run(orchestrator.run_existing(run))


def _summary(run: PipelineRunState) -> PipelineRunSummary:
    return PipelineRunSummary(
        run_id=run.run_id,
        status=run.status.value,
        question=run.question,
        top_k=run.top_k,
        use_mock=run.use_mock,
        index_path=run.index_path,
        step_count=len(run.steps),
        error=run.error,
    )
