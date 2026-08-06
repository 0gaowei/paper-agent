"""Shim for backward compatibility - re-exports from iterative_search.

.. deprecated::
    The ``research`` package is deprecated. Import from the appropriate
    functional package instead:
    - ``from evoscholar.iterative_search import ResearchEngine``
    - ``from evoscholar.synthesis import AnswerSummary, EvidenceSnippet``
    - ``from evoscholar.research.models import AcademicPaper`` (moved to iterative_search)
"""
from __future__ import annotations

import warnings
from typing import Any

warnings.warn(
    "evoscholar.research is deprecated, use evoscholar.iterative_search "
    "and evoscholar.synthesis instead",
    DeprecationWarning,
    stacklevel=2,
)

from evoscholar.iterative_search.engine import *

__all__ = [
    "AcademicPaper",
    "AnswerSummary",
    "CitationEdge",
    "EvidenceSnippet",
    "QueryUnderstanding",
    "RelevanceTier",
    "ResearchEngine",
    "ResearchSession",
    "SearchResult",
    "StopReason",
    "UsageStats",
]


def __getattr__(name: str) -> Any:
    if name == "ResearchEngine":
        from evoscholar.iterative_search.engine import ResearchEngine

        return ResearchEngine
    if name in ("score_papers", "ascore_papers", "rank_with_mmr"):
        from evoscholar.paper_ranker import (
            ascore_papers,
            rank_with_mmr,
            score_papers,
        )

        return locals()[name]
    raise AttributeError(name)
