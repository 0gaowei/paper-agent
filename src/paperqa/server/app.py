"""FastAPI application for the PaperQA research server.

Exports:
    app: The FastAPI application instance.
    run(): Run the server with uvicorn (programmatic).
    serve(): CLI entry point via `pqa-serve`.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Annotated, Any

import anyio
import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from paperqa.server.events import EventPublisher, EventType, SSEEvent, SSEEventGenerator
from paperqa.server.repository import JSONFileRepository

logger = logging.getLogger(__name__)


def _build_research_engine(
    client: httpx.AsyncClient, *, providers: list[str] | None = None
) -> Any:
    """Instantiate a ResearchEngine.

    Imports are deferred so that the server can start even when the
    `paperqa.research` package (or its LLM/search deps) is missing in a
    lightweight test environment. On failure we log and return ``None``
    so the routes keep responding with their stub events.
    """
    try:
        from paperqa.research import ResearchEngine
        from paperqa.settings import Settings
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "ResearchEngine unavailable; create_session will return 503: %s", exc
        )
        return None
    try:
        settings = Settings()
        if providers is not None:
            settings.research.providers = providers
        return ResearchEngine(settings=settings, providers=client)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "ResearchEngine init failed; create_session will return 503: %s", exc
        )
        return None


# ---------------------------------------------------------------------------
# Lifespan state
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup → shared resources → shutdown cleanup."""

    # Shared httpx.AsyncClient (reused by downstream clients/engines)
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        app.state.client = client  # type: ignore[attr-defined]

        # JSON session repository
        app.state.repository = JSONFileRepository()  # type: ignore[attr-defined]

        # SSE event hub
        app.state.publisher = EventPublisher()  # type: ignore[attr-defined]

        # Background tasks keyed by session_id (for cancellation)
        app.state.tasks: dict[str, asyncio.Task[None]] = {}  # type: ignore[attr-defined]

        # Real ResearchEngine (lazily constructed; may be None in tests)
        app.state.engine = _build_research_engine(client)  # type: ignore[attr-defined]

        logger.info(
            "PaperQA server started — engine=%s",
            "ready" if app.state.engine is not None else "unavailable",
        )

        yield

        # Shutdown: cancel any in-flight research tasks
        tasks: dict[str, asyncio.Task[None]] = getattr(app.state, "tasks", {})
        for sid, task in list(tasks.items()):
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks.values(), return_exceptions=True)

        engine = getattr(app.state, "engine", None)
        if engine is not None:
            try:
                await engine.aclose()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Error closing engine on shutdown: %s", exc)

        logger.info("PaperQA server shutdown complete.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="PaperQA Research API",
    description=(
        "Asynchronous research API for academic paper search, citation graphs, "
        "and evidence synthesis. Emits Server-Sent Events for real-time progress."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS configuration (localhost:5173 for Vite dev, configurable via env)
# ---------------------------------------------------------------------------

_cors_origins = os.environ.get(
    "PQA_CORS_ORIGINS",
    "http://localhost:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Lightweight health endpoint."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Import and mount routers
# ---------------------------------------------------------------------------

from paperqa.server.routes import graph, history, papers, sessions, settings, usage

app.include_router(sessions.router, prefix="/api")
app.include_router(papers.router, prefix="/api")
app.include_router(graph.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(usage.router, prefix="/api")


# ---------------------------------------------------------------------------
# SSE events endpoint (registered after routers so route order is clear)
# ---------------------------------------------------------------------------


@app.get(
    "/api/sessions/{session_id}/events",
    summary="Stream SSE events for a session",
    response_class=StreamingResponse,
)
async def sse_events(session_id: str) -> StreamingResponse:
    """Stream Server-Sent Events for a research session.

    Clients should:
    1. First call POST /api/sessions to create (or GET /api/sessions/{id} to resume)
    2. Subscribe here for real-time updates
    3. Parse SSE lines: `event: <type>\\ndata: <json>\\n\\n`

    Event types:
      understanding → subqueries → round_started → paper_found (×N)
        → partial_documents → answer → usage → done
      error / cancelled may appear at any point.

    Client disconnect automatically unsubscribes and unblocks the generator.
    """
    from paperqa.server.repository import JSONFileRepository

    repository: JSONFileRepository = app.state.repository  # type: ignore[attr-defined]
    publisher: EventPublisher = app.state.publisher  # type: ignore[attr-defined]
    session = await repository.get(session_id)
    if session is None:
        return StreamingResponse(
            iter([
                SSEEvent(
                    event=EventType.ERROR,
                    data={"message": f"Session {session_id!r} not found."},
                ).to_sse_line().encode("utf-8"),
                SSEEvent(event=EventType.DONE, data={}).to_sse_line().encode("utf-8"),
            ]),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    async def event_stream() -> SSEEventGenerator:
        async for event in publisher.events(session_id):
            yield event.to_sse_line().encode("utf-8")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Programmatic and CLI entry points
# ---------------------------------------------------------------------------


def run(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False,
    log_level: str = "info",
) -> None:
    """Run the server programmatically with uvicorn."""
    uvicorn.run(
        "paperqa.server.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )


def serve() -> None:
    """CLI entry point: `pqa-serve`."""
    import sys

    host = os.environ.get("PQA_HOST", "0.0.0.0")
    port_str = os.environ.get("PQA_PORT", "8000")
    try:
        port = int(port_str)
    except ValueError:
        sys.stderr.write(f"[pqa-serve] PQA_PORT must be an integer, got {port_str!r}. Using 8000.\n")
        port = 8000

    log_level = os.environ.get("PQA_LOG_LEVEL", "info")
    reload = os.environ.get("PQA_RELOAD", "0") in ("1", "true", "yes")

    logger.info("Starting pqa-serve on %s:%s (reload=%s)", host, port, reload)
    run(host=host, port=port, reload=reload, log_level=log_level)


if __name__ == "__main__":
    serve()
