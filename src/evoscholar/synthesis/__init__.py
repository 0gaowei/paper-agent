"""Synthesis package for building evidence and answers.

This package contains the core logic for:
- Building evidence snippets from papers (builder.py)
- SSE event payload formatting (sse_formatter.py)
- Domain models for synthesis (models.py)
"""

from __future__ import annotations

from .models import AnswerSummary, EvidenceSnippet, UsageStats
from .sse_formatter import (
    format_usage_event,
    format_answer_event,
    format_progress_event,
    format_round_event,
    format_paper_found_event,
    format_understanding_event,
    format_error_event,
    format_done_event,
)

__all__ = [
    "AnswerSummary",
    "EvidenceSnippet",
    "UsageStats",
    "format_usage_event",
    "format_answer_event",
    "format_progress_event",
    "format_round_event",
    "format_paper_found_event",
    "format_understanding_event",
    "format_error_event",
    "format_done_event",
]


def __getattr__(name: str):
    """Lazily import builder to avoid circular imports with iterative_search."""
    if name == "build_evidence_and_answer":
        from .builder import build_evidence_and_answer

        return build_evidence_and_answer
    raise AttributeError(name)
