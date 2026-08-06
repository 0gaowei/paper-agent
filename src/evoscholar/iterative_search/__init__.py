"""
Iterative search package for academic paper research.

This package contains the core components for iterative paper search:
- ResearchEngine: Main engine for running research sessions
- Models: Domain models for papers, sessions, and search results
- Callbacks: Progress callback interface
"""

from __future__ import annotations

from typing import Any

from .engine import ResearchEngine
from .models import (
    AcademicPaper,
    ResearchSession,
    SearchResult,
    SearchRound,
    StopReason,
    CitationEdge,
)
from .callbacks import NoOpProgressCallback, ResearchProgressCallback

__all__ = [
    "AcademicPaper",
    "CitationEdge",
    "NoOpProgressCallback",
    "ResearchEngine",
    "ResearchProgressCallback",
    "ResearchSession",
    "SearchResult",
    "SearchRound",
    "StopReason",
]


def __getattr__(name: str) -> Any:
    if name == "ResearchEngine":
        from .engine import ResearchEngine

        return ResearchEngine
    raise AttributeError(name)
