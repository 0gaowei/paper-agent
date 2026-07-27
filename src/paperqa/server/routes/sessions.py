"""Session management routes."""

from __future__ import annotations

import asyncio
import datetime
import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from paperqa.server.events import EventPublisher, EventType, SSEEvent
from paperqa.server.repository import JSONFileRepository
from paperqa.server.schemas import (
    NewSessionRequest,
    ResearchSession,
    SessionResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["sessions"])


# ---------------------------------------------------------------------------
# Background engine runner
# ---------------------------------------------------------------------------


async def _run_research_engine(
    session_id: str, query: str, publisher: EventPublisher
) -> None:
    """Run the real ResearchEngine in the background and publish SSE events.

    This coroutine is scheduled by `create_session` via
    `asyncio.create_task(...)`. On CancelledError we emit CANCELLED and
    update the persisted session. On any other exception we emit ERROR.
    """
    from paperqa.server.app import app
    from paperqa.server.bridge import (
        ResearchEventBridge,
        research_to_server_session,
    )
    from paperqa.research.query_understanding import analyze_and_expand_query

    engine = getattr(app.state, "engine", None)
    repository: JSONFileRepository = app.state.repository

    try:
        if engine is None:
            await publisher.publish(
                session_id,
                SSEEvent(
                    event=EventType.ERROR,
                    data={"error": "ResearchEngine is not configured on this server."},
                ),
            )
            await publisher.publish(
                session_id, SSEEvent(event=EventType.DONE, data={})
            )
            session = await repository.get(session_id)
            if session is not None:
                session.status = "error"
                session.error_message = "engine_unavailable"
                session.updated_at = datetime.datetime.utcnow()
                await repository.save(session)
            return

        tracked_llm = engine.llm_model
        precomputed_understanding = await analyze_and_expand_query(
            query, engine.settings, tracked_llm
        )
        if precomputed_understanding.fallback_used:
            await publisher.publish(
                session_id,
                SSEEvent(
                    event=EventType.HEURISTIC_WARNING,
                    data={
                        "message": (
                            "No LLM available for query understanding. "
                            "Using heuristic fallback with limited understanding."
                        ),
                        "error": precomputed_understanding.error_message,
                    },
                ),
            )

        research_session = await engine.arun(
            query,
            precomputed_understanding=precomputed_understanding,
            publisher=publisher,
            session_id=session_id,
        )
        server_session = research_to_server_session(research_session, session_id)
        await repository.save(server_session)

        bridge = ResearchEventBridge(session_id, research_session)
        for payload in bridge.build_events():
            await publisher.publish(
                session_id,
                SSEEvent(event=payload["type"], data=payload["data"]),
            )
    except asyncio.CancelledError:
        await publisher.publish(
            session_id,
            SSEEvent(
                event=EventType.CANCELLED,
                data={"reason": "Cancelled by client."},
            ),
        )
        session = await repository.get(session_id)
        if session is not None:
            session.status = "cancelled"
            session.stop_reason = "cancelled"
            session.updated_at = datetime.datetime.utcnow()
            await repository.save(session)
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("ResearchEngine run failed for %s", session_id)
        error_msg = f"ResearchEngine failure: {exc!s}"
        await publisher.publish(
            session_id,
            SSEEvent(
                event=EventType.ERROR,
                data={"error": error_msg},
            ),
        )
        await publisher.publish(
            session_id, SSEEvent(event=EventType.DONE, data={})
        )
        session = await repository.get(session_id)
        if session is not None:
            session.status = "error"
            session.error_message = str(exc)
            session.updated_at = datetime.datetime.utcnow()
            await repository.save(session)
    finally:
        tasks: dict[str, asyncio.Task[None]] = getattr(app.state, "tasks", {})
        tasks.pop(session_id, None)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/sessions",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=dict,
    summary="Create a new research session",
)
async def create_session(request: NewSessionRequest) -> dict:
    """Create a new research session and immediately return 202 Accepted.

    The session is launched in the background via an `asyncio.Task`.
    Subscribe to GET /api/sessions/{id}/events for real-time progress
    via SSE. Returns 503 when the ResearchEngine is unavailable.
    """
    from paperqa.server.app import app

    session_id = str(uuid4())
    repository: JSONFileRepository = app.state.repository
    publisher: EventPublisher = app.state.publisher

    session = ResearchSession(
        id=session_id,
        query=request.query,
        status="running",
    )
    await repository.save(session)

    engine = getattr(app.state, "engine", None)
    if engine is None:
        session.status = "error"
        session.error_message = "engine_unavailable"
        await repository.save(session)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ResearchEngine is not configured on this server.",
        )

    task = asyncio.create_task(
        _run_research_engine(session_id, request.query, publisher),
        name=f"research-{session_id}",
    )
    tasks: dict[str, asyncio.Task[None]] = getattr(app.state, "tasks", {})
    tasks[session_id] = task

    return {"id": session_id}


@router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    summary="Get a research session",
)
async def get_session(session_id: str) -> SessionResponse:
    """Return the full session JSON for a given session ID.

    Use this to refresh the session state after a client reconnects.
    """
    from paperqa.server.app import app

    repository: JSONFileRepository = app.state.repository
    session = await repository.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id!r} not found.",
        )
    return SessionResponse(
        session=session,
        papers=list(session.papers.values()),
        events_emitted=0,
    )


@router.post(
    "/sessions/{session_id}/cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancel a running research session",
)
async def cancel_session(session_id: str) -> dict:
    """Cancel a running research session.

    This sends a cancellation signal to the running task and emits
    an error event to all SSE subscribers.
    """
    from paperqa.server.app import app

    repository: JSONFileRepository = app.state.repository
    publisher: EventPublisher = app.state.publisher

    session = await repository.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id!r} not found.",
        )

    tasks: dict[str, asyncio.Task[None]] = getattr(app.state, "tasks", {})
    task = tasks.get(session_id)

    session.status = "cancelled"
    session.stop_reason = "cancelled"
    session.updated_at = datetime.datetime.utcnow()
    await repository.save(session)

    if task is not None and not task.done():
        task.cancel()

    await publisher.publish(
        session_id,
        SSEEvent(
            event=EventType.CANCELLED,
            data={"reason": "Cancelled by client."},
        ),
    )
    await publisher.publish_cancelled(session_id)

    return {"id": session_id, "status": "cancelled"}


@router.get(
    "/sessions/{session_id}/history",
    summary="Get session history (alias for get_session)",
)
async def get_session_history(session_id: str) -> SessionResponse:
    """Alias for GET /sessions/{session_id} for backwards compatibility."""
    return await get_session(session_id)