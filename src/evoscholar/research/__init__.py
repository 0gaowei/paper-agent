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
    raise AttributeError(name)
