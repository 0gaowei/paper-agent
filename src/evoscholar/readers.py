"""Compatibility shim so ``paperqa_pypdf`` / ``paperqa_pymupdf`` wheels that
still reference ``from paperqa.readers import ...`` continue to load.

``paperqa`` is an alias for ``evoscholar`` set in
``evoscholar/__init__.py``.
"""
from __future__ import annotations

from evoscholar.literature_qa.readers import (
    resolve_page_range,
)

__all__ = [
    "resolve_page_range",
]
