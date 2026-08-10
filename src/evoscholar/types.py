"""Compatibility shim so ``paperqa_pypdf`` / ``paperqa_pymupdf`` wheels that
still reference ``from paperqa.types import ParsedMedia, ParsedMetadata, ParsedText``
continue to load.
"""
from __future__ import annotations

from evoscholar.literature_qa.types import ParsedMedia, ParsedMetadata, ParsedText

__all__ = [
    "ParsedMedia",
    "ParsedMetadata",
    "ParsedText",
]
