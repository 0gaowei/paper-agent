"""SSE event publisher adapter for the research progress callback protocol.

This module implements the ResearchProgressCallback protocol by converting
callback events into SSE events published via the EventPublisher.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from evoscholar.server.events import EventPublisher, EventType

logger = logging.getLogger(__name__)


class SSEProgressCallback:
    """Convert research progress callbacks to SSE events.
    
    This class bridges the domain layer's callback protocol with the
    server layer's SSE event system, keeping the domain layer free
    from transport concerns.
    """

    def __init__(self, publisher: "EventPublisher", session_id: str) -> None:
        self.publisher = publisher
        self.session_id = session_id

    async def on_evidence_extraction_start(
        self, session_id: str | None, total: int = 0
    ) -> None:
        from evoscholar.server.events import EventType, SSEEvent

        await self.publisher.publish(
            self.session_id,
            SSEEvent(
                event=EventType.EVIDENCE_EXTRACTION_START,
                data={
                    "message": "Starting evidence extraction from papers...",
                    "total": total,
                },
            ),
        )

    async def on_evidence_extraction_done(
        self, session_id: str | None, snippets_found: int
    ) -> None:
        from evoscholar.server.events import EventType, SSEEvent

        await self.publisher.publish(
            self.session_id,
            SSEEvent(
                event=EventType.EVIDENCE_EXTRACTION_DONE,
                data={"snippets_found": snippets_found},
            ),
        )

    async def on_answer_synthesis_start(
        self, session_id: str | None, message: str
    ) -> None:
        from evoscholar.server.events import EventType, SSEEvent

        await self.publisher.publish(
            self.session_id,
            SSEEvent(
                event=EventType.ANSWER_SYNTHESIS_START,
                data={"message": message},
            ),
        )

    async def on_answer_synthesis_done(
        self, session_id: str | None, answer_length: int
    ) -> None:
        from evoscholar.server.events import EventType, SSEEvent

        await self.publisher.publish(
            self.session_id,
            SSEEvent(
                event=EventType.ANSWER_SYNTHESIS_DONE,
                data={"answer_length": answer_length},
            ),
        )

    async def on_error(self, session_id: str | None, error: str) -> None:
        from evoscholar.server.events import EventType, SSEEvent

        await self.publisher.publish(
            self.session_id,
            SSEEvent(
                event=EventType.ERROR,
                data={"error": error},
            ),
        )

    async def on_done(self, session_id: str | None) -> None:
        from evoscholar.server.events import EventType, SSEEvent

        await self.publisher.publish(
            self.session_id,
            SSEEvent(event=EventType.DONE, data={}),
        )

    async def on_cancelled(self, session_id: str | None, reason: str) -> None:
        from evoscholar.server.events import EventType, SSEEvent

        await self.publisher.publish(
            self.session_id,
            SSEEvent(
                event=EventType.CANCELLED,
                data={"reason": reason},
            ),
        )

    async def publish_raw(
        self, session_id: str | None, event_type: "EventType", data: dict[str, Any]
    ) -> None:
        from evoscholar.server.events import SSEEvent

        await self.publisher.publish(
            self.session_id,
            SSEEvent(event=event_type, data=data),
        )
