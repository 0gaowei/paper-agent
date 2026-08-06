"""Shim module for backwards compatibility. Import from evoscholar.paper_ranker instead.

.. deprecated::
    Import directly from ``evoscholar.paper_ranker`` instead.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "evoscholar.research.ranking is deprecated, use evoscholar.paper_ranker",
    DeprecationWarning,
    stacklevel=2,
)

from evoscholar.paper_ranker.ranker import *

from evoscholar.paper_ranker.mmr import rank_with_mmr

__all__ = ["ascore_papers", "rank_with_mmr", "score_papers"]
