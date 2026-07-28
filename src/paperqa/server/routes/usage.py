"""Usage aggregation routes."""


from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from paperqa.server.dependencies import get_repository
from paperqa.server.schemas import UsageStats

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/usage", tags=["usage"])

# In-memory user-level usage accumulator
_user_usage: UsageStats = UsageStats()


@router.get(
    "",
    response_model=UsageStats,
    summary="Get aggregated usage statistics",
)
async def get_usage(
    repository=Depends(get_repository),
) -> UsageStats:
    """Return aggregated usage statistics across all sessions for the current user.

    Usage is accumulated in memory for the lifetime of the server process.
    """
    global _user_usage

    # Recompute from all persisted sessions
    sessions = await repository.list_(limit=1000)

    total = UsageStats()
    for session in sessions:
        if session.usage:
            total.total_tokens += session.usage.total_tokens
            total.prompt_tokens += session.usage.prompt_tokens
            total.completion_tokens += session.usage.completion_tokens
            total.total_cost += session.usage.total_cost
            total.llm_calls += session.usage.llm_calls
            total.search_calls += session.usage.search_calls
            total.rounds += session.usage.rounds

    _user_usage = total
    return _user_usage
