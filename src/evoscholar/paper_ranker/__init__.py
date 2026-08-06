"""Paper ranking package for scoring and ranking academic papers."""

from __future__ import annotations

from .embedder import embed_texts_async, embed_texts_sync
from .mmr import rank_with_mmr
from .ranker import ascore_papers, score_papers
from .relevance import RelevanceTier

__all__ = [
    "ascore_papers",
    "embed_texts_async",
    "embed_texts_sync",
    "rank_with_mmr",
    "RelevanceTier",
    "score_papers",
]
