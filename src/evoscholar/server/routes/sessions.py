"""Session management routes."""


from __future__ import annotations

import asyncio
import datetime
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from evoscholar.server.dependencies import get_engine, get_publisher, get_repository, get_tasks
from evoscholar.server.events import EventPublisher, EventType, SSEEvent
from evoscholar.server.repository import JSONFileRepository
from evoscholar.server.schemas import (
    NewSessionRequest,
    ResearchSession,
    SessionResponse,
)
from evoscholar.server.sse_callback import SSEProgressCallback

logger = logging.getLogger(__name__)
router = APIRouter(tags=["sessions"])


# ---------------------------------------------------------------------------
# Background engine runner
# ---------------------------------------------------------------------------


async def _run_research_engine(
    session_id: str,
    query: str,
    repository: JSONFileRepository,
    engine,
    tasks: dict[str, asyncio.Task[None]],
    progress_callback,  # SSEProgressCallback
) -> None:
    """Run the real ResearchEngine in the background and publish SSE events.

    This coroutine is scheduled by `create_session` via
    `asyncio.create_task(...)`. On CancelledError we emit CANCELLED and
    update the persisted session. On any other exception we emit ERROR.
    """
    from evoscholar.server.bridge import (
        ResearchEventBridge,
        research_to_server_session,
    )
    from evoscholar.research.query_understanding import analyze_and_expand_query

    try:
        if engine is None:
            await progress_callback.on_error(
                session_id, "ResearchEngine is not configured on this server."
            )
            await progress_callback.on_done(session_id)
            session = await repository.get(session_id)
            if session is not None:
                session.status = "error"
                session.error_message = "engine_unavailable"
                session.updated_at = datetime.datetime.now(datetime.timezone.utc)
                await repository.save(session)
            return

        tracked_llm = engine.llm_model
        precomputed_understanding = await analyze_and_expand_query(
            query, engine.settings, tracked_llm
        )

        research_session = await engine.arun(
            query,
            precomputed_understanding=precomputed_understanding,
            progress_callback=progress_callback,
            session_id=session_id,
        )
        server_session = research_to_server_session(research_session, session_id)
        await repository.save(server_session)

        # Populate paper cache for fast lookups
        from evoscholar.server.routes.papers import register_paper
        for paper in server_session.papers.values():
            register_paper(paper)

        bridge = ResearchEventBridge(session_id, research_session)
        for payload in bridge.build_events():
            await progress_callback.publish_raw(
                session_id,
                payload["type"],
                payload["data"],
            )
    except asyncio.CancelledError:
        await progress_callback.on_cancelled(session_id, "Cancelled by client.")
        session = await repository.get(session_id)
        if session is not None:
            session.status = "cancelled"
            session.stop_reason = "cancelled"
            session.updated_at = datetime.datetime.now(datetime.timezone.utc)
            await repository.save(session)
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("ResearchEngine run failed for %s", session_id)
        error_msg = f"ResearchEngine failure: {exc!s}"
        await progress_callback.on_error(session_id, error_msg)
        await progress_callback.on_done(session_id)
        session = await repository.get(session_id)
        if session is not None:
            session.status = "error"
            session.error_message = str(exc)
            session.updated_at = datetime.datetime.now(datetime.timezone.utc)
            await repository.save(session)
    finally:
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
async def create_session(
    request: NewSessionRequest,
    repository: JSONFileRepository = Depends(get_repository),
    publisher: EventPublisher = Depends(get_publisher),
    engine=Depends(get_engine),
    tasks: dict = Depends(get_tasks),
) -> dict:
    """Create a new research session and immediately return 202 Accepted.

    The session is launched in the background via an `asyncio.Task`.
    Subscribe to GET /api/sessions/{id}/events for real-time progress
    via SSE. Returns 503 when the ResearchEngine is unavailable.
    """
    session_id = str(uuid4())

    session = ResearchSession(
        id=session_id,
        query=request.query,
        status="running",
    )
    await repository.save(session)

    if engine is None:
        session.status = "error"
        session.error_message = "engine_unavailable"
        await repository.save(session)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ResearchEngine is not configured on this server.",
        )

    # Create SSE progress callback for this session
    progress_callback = SSEProgressCallback(publisher, session_id)

    task = asyncio.create_task(
        _run_research_engine(
            session_id, request.query, repository, engine, tasks, progress_callback
        ),
        name=f"research-{session_id}",
    )
    tasks[session_id] = task

    return {"id": session_id}


@router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    summary="Get a research session",
)
async def get_session(
    session_id: str,
    repository: JSONFileRepository = Depends(get_repository),
) -> SessionResponse:
    """Return the full session JSON for a given session ID.

    Use this to refresh the session state after a client reconnects.
    """
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
async def cancel_session(
    session_id: str,
    repository: JSONFileRepository = Depends(get_repository),
    publisher: EventPublisher = Depends(get_publisher),
    tasks: dict = Depends(get_tasks),
) -> dict:
    """Cancel a running research session.

    This sends a cancellation signal to the running task and emits
    an error event to all SSE subscribers.
    """
    session = await repository.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id!r} not found.",
        )

    task = tasks.get(session_id)

    session.status = "cancelled"
    session.stop_reason = "cancelled"
    session.updated_at = datetime.datetime.now(datetime.timezone.utc)
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
async def get_session_history(
    session_id: str,
    repository: JSONFileRepository = Depends(get_repository),
) -> SessionResponse:
    """Alias for GET /sessions/{session_id} for backwards compatibility."""
    return await get_session(session_id, repository)