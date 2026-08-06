"""Shim for backward compatibility - re-exports from iterative_search.

.. deprecated::
    Import ResearchEngine directly from ``evoscholar.iterative_search`` instead.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "evoscholar.research.engine is deprecated, use evoscholar.iterative_search.engine",
    DeprecationWarning,
    stacklevel=2,
)

from evoscholar.iterative_search.engine import *
