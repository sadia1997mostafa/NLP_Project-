"""Long-lived HTTP process for Partner B's application."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.pipeline.service import QueryPipeline, model_ready


def create_app(pipeline: QueryPipeline | None = None) -> FastAPI:
    app = FastAPI(title="NagorikSheba AI")
    app.state.pipeline = pipeline or QueryPipeline()
    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/api/status")
    def status() -> dict:
        return {"model_ready": model_ready()}

    @app.post("/api/analyze")
    async def analyze(request: Request) -> dict:
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
            return JSONResponse(app.state.pipeline.analyze(query), headers={"Cache-Control": "no-store"})
        except Exception:
            # Never include raw query text or model exception details in a response or log.
            raise HTTPException(503, "Analysis is temporarily unavailable") from None

    return app


app = create_app()
