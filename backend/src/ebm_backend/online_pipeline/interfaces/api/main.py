"""FastAPI application entry point for the Online EBM module backend."""

from __future__ import annotations

from fastapi import FastAPI

from ebm_backend.online_pipeline.interfaces.api.routes_modules import router as modules_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Online EBM Pipeline",
        version="1.0.0",
        description="Module-level APIs for the Online EBM backend. Some modules remain placeholder interfaces until concrete methods are added.",
    )
    app.include_router(modules_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
