"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI

from ebm_backend.online_pipeline.interfaces.api.routes_pipeline import router as pipeline_router
from ebm_backend.online_pipeline.interfaces.api.routes_retrieval import router as retrieval_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Online EBM Pipeline",
        version="0.5.0",
        description="Simplified Phase 5 API for inspecting Module 2 and Module 3 pipeline traces.",
    )
    app.include_router(pipeline_router)
    app.include_router(retrieval_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
