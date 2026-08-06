"""Shim for backward compatibility - re-exports from iterative_search.

.. deprecated::
    Import directly from ``evoscholar.iterative_search.callbacks`` instead.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "evoscholar.research.callbacks is deprecated, use evoscholar.iterative_search.callbacks",
    DeprecationWarning,
    stacklevel=2,
)

from evoscholar.iterative_search.callbacks import *
