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
    CitationEdge,
    ResearchSession,
    SearchResult,
    SearchRound,
    StopReason,
)
from .callbacks import NoOpProgressCallback, ResearchProgressCallback

# Re-export synthesis types for backward compatibility
from evoscholar.synthesis.models import AnswerSummary, EvidenceSnippet, UsageStats

__all__ = [
    "AcademicPaper",
    "AnswerSummary",
    "CitationEdge",
    "EvidenceSnippet",
    "NoOpProgressCallback",
    "ResearchEngine",
    "ResearchProgressCallback",
    "ResearchSession",
    "SearchResult",
    "SearchRound",
    "StopReason",
    "UsageStats",
]


def __getattr__(name: str) -> Any:
    if name == "ResearchEngine":
        from .engine import ResearchEngine

        return ResearchEngine
    raise AttributeError(name)
