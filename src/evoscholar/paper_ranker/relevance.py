"""Relevance tier for paper candidates based on score thresholds."""
from __future__ import annotations

from enum import StrEnum


class RelevanceTier(StrEnum):
    """Relevance tier for paper candidates based on score thresholds."""

    HIGH = "high"
    """Score >= high_threshold (default 0.75). Paper is highly relevant."""

    PARTIAL = "partial"
    """Score >= partial_threshold but < high_threshold (0.5 to 0.75)."""

    LOW = "low"
    """Score < partial_threshold (0.5). Not very relevant."""
