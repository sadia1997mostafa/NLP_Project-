"""Long-lived HTTP process for Partner B's application."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from src.pipeline.service import QueryPipeline, model_ready
from src.response.local_generator import configured_model_path, local_generator_ready


def _sse_message(event: str, payload: dict) -> str:
    """Serialize one compact server-sent event without logging query data."""
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {data}\n\n"


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

    @app.middleware("http")
    async def no_store_api(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/api/status")
    def status() -> JSONResponse:
        generator_path = configured_model_path()
        answer_generator = app.state.pipeline.answer_generator
        answer_available = answer_generator is not None and local_generator_ready()
        answer_ready = bool(
            answer_available and getattr(answer_generator, "is_loaded", False)
        )
        return JSONResponse({
            "model_ready": model_ready(),
            "answer_generator_configured": bool(generator_path and generator_path.is_file()),
            "answer_generator_available": answer_available,
            "answer_generator_ready": answer_ready,
            "answer_generator_status": (
                "ready" if answer_ready
                else "available_on_demand" if answer_available
                else "unavailable"
            ),
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

    @app.post("/api/query/stream")
    async def analyze_stream(request: Request) -> StreamingResponse:
        """Stream genuine single-pass pipeline stages and the final response."""
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

        async def event_stream():
            loop = asyncio.get_running_loop()
            queue: asyncio.Queue[tuple[str, dict]] = asyncio.Queue()

            def publish(event: str, payload: dict) -> None:
                try:
                    loop.call_soon_threadsafe(
                        queue.put_nowait,
                        (event, payload),
                    )
                except RuntimeError:
                    # A disconnected browser must not interrupt model inference.
                    pass

            async def analyze_once() -> None:
                try:
                    result = await run_in_threadpool(
                        app.state.pipeline.analyze,
                        query,
                        publish,
                    )
                except Exception:
                    publish("error", {
                        "message": "Analysis is temporarily unavailable",
                    })
                else:
                    publish("complete", result)

            worker = asyncio.create_task(analyze_once())
            yield _sse_message("started", {"status": "started"})
            while True:
                event, payload = await queue.get()
                yield _sse_message(event, payload)
                if event in {"complete", "error"}:
                    break
            await worker

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-store",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get("/api/guidance")
    def catalog() -> JSONResponse:
        return JSONResponse(app.state.pipeline.guidance_catalog(), headers={"Cache-Control": "no-store"})

    @app.post("/api/guidance")
    async def selected_guidance(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(400, "Expected a guidance selection") from None
        fields = {"service", "parent_topic_id", "query_topic_id"}
        if (not isinstance(body, dict) or set(body) not in (fields, fields | {"language"})
                or not isinstance(body.get("service"), str)
                or body.get("language", "en") not in ("en", "bn")
                or any(body[key] is not None and not isinstance(body[key], str)
                       for key in ("parent_topic_id", "query_topic_id"))):
            raise HTTPException(400, "Invalid guidance selection")
        try:
            result = app.state.pipeline.selected_guidance(
                body["service"], body["parent_topic_id"], body["query_topic_id"],
                body.get("language", "en"),
            )
        except KeyError:
            raise HTTPException(404, "Guidance for that selection is unavailable") from None
        return JSONResponse(result, headers={"Cache-Control": "no-store"})

    return app


app = create_app()
