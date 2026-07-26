"""Session management routes."""

from __future__ import annotations

import asyncio
import datetime
import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from starlette.responses import StreamingResponse

from paperqa.server.events import EventPublisher, EventType, SSEEvent
from paperqa.server.repository import JSONFileRepository
from paperqa.server.schemas import (
    AcademicPaper,
    EvidenceSnippet,
    NewSessionRequest,
    QueryUnderstanding,
    ResearchSession,
    SessionResponse,
    SubQuery,
    UsageStats,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["sessions"])


def _build_phony_session(session_id: str, query: str) -> ResearchSession:
    """Build a phony session with a few dummy papers for testing."""
    papers: dict[str, AcademicPaper] = {
        "paper-1": AcademicPaper(
            id="paper-1",
            title=f"Research on: {query}",
            year=2024,
            authors=["Author A.", "Author B."],
            relevance_tier="high",
            abstract=f"This paper discusses {query} in depth.",
            citation_count=42,
            source="semantic_scholar",
        ),
        "paper-2": AcademicPaper(
            id="paper-2",
            title=f"Further study on {query}",
            year=2023,
            authors=["Author C."],
            relevance_tier="partial",
            abstract=f"Additional findings related to {query}.",
            citation_count=15,
            source="openalex",
        ),
    }
    return ResearchSession(
        id=session_id,
        query=query,
        status="done",
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow(),
        understanding=QueryUnderstanding(
            intent="general",
            domain="computer science",
            entities=[query],
            suitable_sources=["semantic_scholar", "openalex"],
            subqueries=[SubQuery(text=query, intent="general", round=0)],
        ),
        papers=papers,
        subqueries=[SubQuery(text=query, intent="general", round=0)],
        rounds=1,
        answer=(
            f"This is a synthesized answer to the query '{query}'. "
            "The research found 2 relevant papers."
        ),
        evidence={
            "paper-1": [
                EvidenceSnippet(
                    text=f"Key finding from paper-1 regarding {query}.",
                    score=8.5,
                )
            ]
        },
        stop_reason="high_relevance_collected",
        usage=UsageStats(
            total_tokens=1200,
            prompt_tokens=800,
            completion_tokens=400,
            total_cost=0.05,
            llm_calls=3,
            search_calls=2,
            rounds=1,
        ),
    )


async def _emit_phony_events(
    session_id: str,
    query: str,
    publisher: EventPublisher,
) -> None:
    """Emit a sequence of phony SSE events for testing."""
    async def emit(event_type: EventType, data: dict) -> None:
        await publisher.publish(
            session_id,
            SSEEvent(event=event_type, data=data),
        )
        await asyncio.sleep(0.05)

    await emit(EventType.UNDERSTANDING, {
        "intent": "general",
        "domain": "computer science",
        "entities": [query],
        "suitable_sources": ["semantic_scholar", "openalex"],
        "subqueries": [{"text": query, "intent": "general", "round": 0}],
    })
    await emit(EventType.SUBQUERIES, {
        "subqueries": [{"text": query, "intent": "general", "round": 0}],
    })
    await emit(EventType.ROUND_STARTED, {"round": 0, "active_subqueries": [query]})
    await emit(EventType.PAPER_FOUND, {
        "id": "paper-1",
        "title": f"Research on: {query}",
        "year": 2024,
        "authors": ["Author A.", "Author B."],
        "relevance_tier": "high",
        "abstract": f"This paper discusses {query} in depth.",
        "citation_count": 42,
        "source": "semantic_scholar",
    })
    await emit(EventType.PAPER_FOUND, {
        "id": "paper-2",
        "title": f"Further study on {query}",
        "year": 2023,
        "authors": ["Author C."],
        "relevance_tier": "partial",
        "abstract": f"Additional findings related to {query}.",
        "citation_count": 15,
        "source": "openalex",
    })
    await emit(EventType.PARTIAL_DOCUMENTS, {
        "papers_count": 2,
        "high_relevance_count": 1,
        "partial_count": 1,
    })
    await emit(EventType.ANSWER, {
        "answer": (
            f"This is a synthesized answer to the query '{query}'. "
            "The research found 2 relevant papers."
        ),
        "papers_used": ["paper-1", "paper-2"],
    })
    await emit(EventType.USAGE, {
        "total_tokens": 1200,
        "prompt_tokens": 800,
        "completion_tokens": 400,
        "total_cost": 0.05,
        "llm_calls": 3,
        "search_calls": 2,
        "rounds": 1,
    })
    await emit(EventType.DONE, {
        "stop_reason": "high_relevance_collected",
        "rounds": 1,
        "papers_count": 2,
    })


def _phony_sse_stream(query: str):
    import time
    events = [
        (EventType.UNDERSTANDING, {
            "intent": "general", "domain": "computer science",
            "entities": [query],
            "suitable_sources": ["semantic_scholar", "openalex"],
            "subqueries": [{"text": query, "intent": "general", "round": 0}],
        }),
        (EventType.SUBQUERIES, {
            "subqueries": [{"text": query, "intent": "general", "round": 0}],
        }),
        (EventType.ROUND_STARTED, {"round": 0, "active_subqueries": [query]}),
        (EventType.PAPER_FOUND, {
            "id": "paper-1", "title": f"Research on: {query}",
            "year": 2024, "authors": ["Author A.", "Author B."],
            "relevance_tier": "high",
            "abstract": f"This paper discusses {query} in depth.",
            "citation_count": 42, "source": "semantic_scholar",
        }),
        (EventType.PAPER_FOUND, {
            "id": "paper-2", "title": f"Further study on {query}",
            "year": 2023, "authors": ["Author C."],
            "relevance_tier": "partial",
            "abstract": f"Additional findings related to {query}.",
            "citation_count": 15, "source": "openalex",
        }),
        (EventType.PARTIAL_DOCUMENTS, {
            "papers_count": 2, "high_relevance_count": 1, "partial_count": 1,
        }),
        (EventType.ANSWER, {
            "answer": f"This is a synthesized answer to the query '{query}'. The research found 2 relevant papers.",
            "papers_used": ["paper-1", "paper-2"],
        }),
        (EventType.USAGE, {
            "total_tokens": 1200, "prompt_tokens": 800,
            "completion_tokens": 400, "total_cost": 0.05,
            "llm_calls": 3, "search_calls": 2, "rounds": 1,
        }),
        (EventType.DONE, {
            "stop_reason": "high_relevance_collected",
            "rounds": 1, "papers_count": 2,
        }),
    ]
    for event_type, data in events:
        time.sleep(0.05)  # simulate async delay synchronously
        yield SSEEvent(event=event_type, data=data).to_sse_line().encode("utf-8")


@router.post(
    "/sessions",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=dict,
    summary="Create a new research session",
)
async def create_session(request: NewSessionRequest) -> dict:
    """Create a new research session and immediately return 202 Accepted.

    The session is launched in the background. Subscribe to
    GET /api/sessions/{id}/events for real-time progress via SSE.
    """
    from paperqa.server.app import app

    session_id = str(uuid4())
    repository: JSONFileRepository = app.state.repository

    session = ResearchSession(id=session_id, query=request.query)
    await repository.save(session)

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

    if session.status not in ("pending", "running"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Session {session_id!r} is already {session.status}; "
                "cancellation is not applicable."
            ),
        )

    session.status = "cancelled"
    session.stop_reason = "cancelled"
    session.updated_at = datetime.datetime.utcnow()
    await repository.save(session)

    await publisher.publish_cancelled(session_id)
    await publisher.publish(
        session_id,
        SSEEvent(
            event=EventType.CANCELLED,
            data={"reason": "Cancelled by client."},
        ),
    )

    return {"id": session_id, "status": "cancelled"}


@router.get(
    "/sessions/{session_id}/history",
    summary="Get session history (alias for get_session)",
)
async def get_session_history(session_id: str) -> SessionResponse:
    """Alias for GET /sessions/{session_id} for backwards compatibility."""
    return await get_session(session_id)
