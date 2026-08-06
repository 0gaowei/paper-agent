from __future__ import annotations

from typing import Any

from .models import (
    AcademicPaper,
    QueryUnderstanding,
    RelevanceTier,
    ResearchSession,
    SearchResult,
    StopReason,
)

__all__ = [
    "AcademicPaper",
    "QueryUnderstanding",
    "RelevanceTier",
    "ResearchEngine",
    "ResearchSession",
    "SearchResult",
    "StopReason",
]


def __getattr__(name: str) -> Any:
    if name == "ResearchEngine":
        from .engine import ResearchEngine

        return ResearchEngine
    if name in ("score_papers", "ascore_papers", "rank_with_mmr"):
        from evoscholar.paper_ranker import (
            ascore_papers,
            rank_with_mmr,
            score_papers,
        )

        return locals()[name]
    raise AttributeError(name)
