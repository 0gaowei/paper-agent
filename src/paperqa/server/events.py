"""Server-Sent Events (SSE) definitions and publisher for research sessions."""

from __future__ import annotations

import asyncio
import json
from enum import Enum
from typing import Any, AsyncGenerator

import anyio
from pydantic import BaseModel, Field

from paperqa.server.schemas import AcademicPaper


class EventType(str, Enum):
    """Types of SSE events emitted during a research session."""

    UNDERSTANDING = "understanding"
    SUBQUERIES = "subqueries"
    ROUND_STARTED = "round_started"
    PAPER_FOUND = "paper_found"
    CITATION_EXPANDED = "citation_expanded"
    PARTIAL_DOCUMENTS = "partial_documents"
    ANSWER = "answer"
    USAGE = "usage"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


class DocsJsonSchema(BaseModel):
    """JSON Schema representation of a document in SSE events."""

    model_config = BaseModel.model_config

    id: str = Field(description="Stable document ID (DOI > S2 ID > title+year).")
    title: str | None = Field(default=None, description="Paper title.")
    year: int | None = Field(default=None, description="Publication year.")
    authors: list[str] = Field(default_factory=list, description="Author names.")
    doi: str | None = Field(default=None, description="DOI.")
    s2_id: str | None = Field(default=None, description="Semantic Scholar ID.")
    openalex_id: str | None = Field(default=None, description="OpenAlex ID.")
    citation_count: int | None = Field(default=None, description="Number of citations.")
    relevance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Relevance score (0–1, where 1 is highest relevance).",
    )
    abstract: str | None = Field(default=None, description="Paper abstract.")
    url: str | None = Field(default=None, description="URL to paper.")
    source: str | None = Field(
        default=None,
        description="Which search provider found this paper.",
    )


class SSEEvent(BaseModel):
    """A Server-Sent Event payload."""

    event: EventType = Field(description="Event type.")
    data: dict[str, Any] = Field(default_factory=dict, description="Event payload.")
    id: str | None = Field(default=None, description="Optional event ID for retry.")

    def to_sse_line(self) -> str:
        """Format as an SSE line: event: <type>\ndata: <json>\n\n"""
        lines = []
        if self.id:
            lines.append(f"id: {self.id}")
        lines.append(f"event: {self.event.value}")
        lines.append(f"data: {json.dumps(self.data, ensure_ascii=False)}")
        return "\n".join(lines) + "\n\n"


class EventPublisher:
    """Publishes SSE events to subscriber queues.

    Each subscriber registers a queue that receives events for a session.
    When the subscriber's client disconnects (queue.get() raises),
    the subscriber is unregistered automatically.

    Events published *before* the first subscriber connects are buffered
    in a per-session replay buffer (bounded by ``_BUFFER_LIMIT``) so a
    slow client doesn't miss the start of the research stream.
    """

    _BUFFER_LIMIT = 1024

    def __init__(self) -> None:
        self._subscribers: dict[str, asyncio.Queue[SSEEvent | None]] = {}
        self._buffers: dict[str, list[SSEEvent]] = {}

    async def subscribe(self, session_id: str) -> asyncio.Queue[SSEEvent | None]:
        """Subscribe to events for a session.

        Any buffered events are flushed into the new queue before this
        returns, so callers see the full stream from the beginning.
        """
        queue: asyncio.Queue[SSEEvent | None] = asyncio.Queue()
        buffer = self._buffers.pop(session_id, None)
        if buffer:
            for event in buffer:
                queue.put_nowait(event)
        self._subscribers[session_id] = queue
        return queue

    async def unsubscribe(self, session_id: str) -> None:
        """Unsubscribe and drain the queue to unblock any waiters."""
        self._subscribers.pop(session_id, None)

    async def publish(self, session_id: str, event: SSEEvent) -> None:
        """Publish an event to all subscribers of a session.

        If no subscriber is connected, the event is appended to the
        per-session replay buffer (capped at ``_BUFFER_LIMIT``).
        Uses a fast-path put_nowait; if the subscriber's queue is full
        (client is slow), the event is dropped rather than blocking.
        """
        queue = self._subscribers.get(session_id)
        if queue is None:
            buffer = self._buffers.setdefault(session_id, [])
            if len(buffer) < self._BUFFER_LIMIT:
                buffer.append(event)
            return
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            pass  # Slow client: drop the event

    async def publish_cancelled(self, session_id: str) -> None:
        """Publish None sentinel to unblock all subscribers of a session."""
        # Cancel sentinel is not buffered — late subscribers are not
        # expected to see a cancellation that already happened.
        queue = self._subscribers.get(session_id)
        if queue is not None:
            try:
                queue.put_nowait(None)
            except asyncio.QueueFull:
                pass

    async def events(self, session_id: str) -> SSEEventGenerator:
        """Yield SSE events as they arrive, until the client disconnects.

        On disconnect (queue.get() raises), automatically unsubscribes.
        Terminates cleanly after a DONE event has been yielded so the
        outer StreamingResponse doesn't hang waiting for more bytes.
        """
        queue = await self.subscribe(session_id)
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield event
                if event.event == EventType.DONE:
                    break
        except GeneratorExit:
            pass
        finally:
            await self.unsubscribe(session_id)


SSEEventGenerator = AsyncGenerator[SSEEvent, None]
