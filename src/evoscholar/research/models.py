"""Domain models for the research package.

.. deprecated::
    Most models have been migrated to their respective functional packages:
    - ``EvidenceSnippet``, ``AnswerSummary``, ``UsageStats`` → ``evoscholar.synthesis``
    - ``AcademicPaper``, ``ResearchSession``, ``SearchResult``, etc. → ``evoscholar.iterative_search``
    - ``RelevanceTier`` → ``evoscholar.paper_ranker``
    - ``QueryIntent``, ``Domain`` → ``evoscholar.query_understanding``
"""
from __future__ import annotations

import warnings

warnings.warn(
    "evoscholar.research.models is deprecated, use evoscholar.iterative_search.models "
    "and evoscholar.synthesis.models instead",
    DeprecationWarning,
    stacklevel=2,
)

from evoscholar.iterative_search.models import (
    AcademicPaper,
    AnswerSummary,
    CitationEdge,
    EvidenceSnippet,
    ResearchSession,
    SearchResult,
    SearchRound,
    StopReason,
    UsageStats,
)
from evoscholar.query_understanding.models import QueryIntent, Domain
from evoscholar.paper_ranker.relevance import RelevanceTier

__all__ = [
    "AcademicPaper",
    "AnswerSummary",
    "CitationEdge",
    "Domain",
    "EvidenceSnippet",
    "QueryIntent",
    "RelevanceTier",
    "ResearchSession",
    "SearchResult",
    "SearchRound",
    "StopReason",
    "UsageStats",
]
