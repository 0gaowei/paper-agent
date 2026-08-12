"""Callback interface for research progress events.

This module defines the protocol that the research engine uses to emit
progress events. The server layer implements this protocol to convert
events into SSE notifications, keeping the domain layer (engine) free
from server-layer dependencies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from evoscholar.server.events import EventType


class ResearchProgressCallback(Protocol):
    """Protocol for receiving research progress events.

    The research engine calls these methods to emit progress events.
    Implementors can choose to:
    - Publish SSE events (server layer)
    - Write to a log
    - Update internal state
    - Ignore the event entirely

    This decouples the domain layer (engine) from the transport layer (SSE).
    """

    async def on_evidence_extraction_start(
        self, session_id: str | None, total: int = 0
    ) -> None:
        """Called when evidence extraction begins; ``total`` papers to process."""
        ...

    async def on_evidence_extraction_done(
        self, session_id: str | None, snippets_found: int
    ) -> None:
        """Called when evidence extraction completes."""
        ...

    async def on_answer_synthesis_start(
        self, session_id: str | None, message: str
    ) -> None:
        """Called when answer synthesis begins."""
        ...

    async def on_answer_synthesis_done(
        self, session_id: str | None, answer_length: int
    ) -> None:
        """Called when answer synthesis completes."""
        ...

    async def on_error(self, session_id: str | None, error: str) -> None:
        """Called when an error occurs."""
        ...

    async def on_done(self, session_id: str | None) -> None:
        """Called when the research session completes."""
        ...

    async def on_cancelled(self, session_id: str | None, reason: str) -> None:
        """Called when the research session is cancelled."""
        ...

    async def publish_raw(
        self, session_id: str | None, event_type: "EventType", data: dict[str, Any]
    ) -> None:
        """Publish a raw SSE event."""
        ...


class NoOpProgressCallback:
    """A no-op implementation of ResearchProgressCallback.

    Use this when progress events are not needed (e.g., in tests).
    """

    async def on_evidence_extraction_start(
        self, session_id: str | None, total: int = 0
    ) -> None:
        pass

    async def on_evidence_extraction_done(
        self, session_id: str | None, snippets_found: int
    ) -> None:
        pass

    async def on_answer_synthesis_start(
        self, session_id: str | None, message: str
    ) -> None:
        pass

    async def on_answer_synthesis_done(
        self, session_id: str | None, answer_length: int
    ) -> None:
        pass

    async def on_error(self, session_id: str | None, error: str) -> None:
        pass

    async def on_done(self, session_id: str | None) -> None:
        pass

    async def on_cancelled(self, session_id: str | None, reason: str) -> None:
        pass

    async def publish_raw(
        self, session_id: str | None, event_type: Any, data: dict[str, Any]
    ) -> None:
        pass
