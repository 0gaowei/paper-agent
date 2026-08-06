"""Shim module for backwards compatibility. Import from evoscholar.paper_ranker instead."""

from evoscholar.paper_ranker.ranker import *

from evoscholar.paper_ranker.mmr import rank_with_mmr

__all__ = ["ascore_papers", "rank_with_mmr", "score_papers"]
