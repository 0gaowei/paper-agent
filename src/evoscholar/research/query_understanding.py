"""Compatibility shim: re-export from query_understanding package.

.. deprecated::
    Import directly from ``evoscholar.query_understanding`` instead.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "evoscholar.research.query_understanding is deprecated, use evoscholar.query_understanding",
    DeprecationWarning,
    stacklevel=2,
)

from evoscholar.query_understanding.analyze import analyze_and_expand_query

__all__ = ["analyze_and_expand_query"]
