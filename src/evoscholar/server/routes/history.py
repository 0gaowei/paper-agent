"""History routes for session listing and deletion."""


from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from evoscholar.server.dependencies import get_repository
from evoscholar.server.schemas import HistoryEntry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/history", tags=["history"])


@router.get(
    "",
    response_model=list[HistoryEntry],
    summary="List recent sessions",
)
async def list_history(
    limit: int = 100,
    repository=Depends(get_repository),
) -> list[HistoryEntry]:
    """Return the most recent research sessions, up to `limit`.

    Only sessions with a terminal status (done / cancelled / error) are returned.
    """
    sessions = await repository.list_(limit=limit)

    entries: list[HistoryEntry] = []
    for session in sessions:
        if session.status not in ("done", "cancelled", "error"):
            continue
        # Compute duration from timestamps (seconds)
        duration = 0.0
        if session.updated_at and session.created_at:
            try:
                delta = session.updated_at - session.created_at
                duration = max(0.0, delta.total_seconds())
            except (TypeError, ValueError):
                pass
        cost = float(getattr(getattr(session, "usage", None), "total_cost", 0.0) or 0.0)
        entries.append(
            HistoryEntry(
                id=session.id,
                query=session.query,
                status=session.status,
                created_at=session.created_at,
                updated_at=session.updated_at,
                papers_count=len(session.papers),
                rounds=session.rounds,
                answer_length=len(session.answer) if session.answer else 0,
                duration=duration,
                cost=cost,
            )
        )
    return entries


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a session",
)
async def delete_history(
    session_id: str,
    repository=Depends(get_repository),
) -> None:
    """Permanently delete a research session and its file."""
    deleted = await repository.delete(session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id!r} not found.",
        )
