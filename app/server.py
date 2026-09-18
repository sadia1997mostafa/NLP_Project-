"""Long-lived HTTP process for Partner B's application."""

from __future__ import annotations

import os
import subprocess
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.pipeline.service import QueryPipeline, model_ready


@lru_cache(maxsize=1)
def app_commit() -> str:
    configured = os.environ.get("NAGORIKSHEBA_APP_COMMIT")
    if configured:
        return configured
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def create_app(pipeline: QueryPipeline | None = None) -> FastAPI:
    app = FastAPI(title="NagorikSheba AI")
    app.state.pipeline = pipeline or QueryPipeline()
    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/api/status")
    def status() -> JSONResponse:
        return JSONResponse({
            "model_ready": model_ready(),
            "runtime_freeze_commit": "38a343d",
            "results_commit": "f2f4e3e",
            "app_commit": app_commit(),
        }, headers={"Cache-Control": "no-store"})

    @app.post("/api/analyze")
    async def analyze(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(400, "Expected a JSON object") from None
        if not isinstance(body, dict) or not isinstance(body.get("text"), str):
            raise HTTPException(400, "A text string is required")
        query = body["text"].strip()
        if not query or len(query) > 4000:
            raise HTTPException(400, "Text must contain 1 to 4000 characters")
        if pipeline is None and not model_ready():
            raise HTTPException(503, "Classifier files are unavailable")
        try:
            result = await run_in_threadpool(app.state.pipeline.analyze, query)
            return JSONResponse(result, headers={"Cache-Control": "no-store"})
        except Exception:
            # Never include raw query text or model exception details in a response or log.
            raise HTTPException(503, "Analysis is temporarily unavailable") from None

    return app


app = create_app()
