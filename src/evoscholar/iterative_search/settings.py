"""Settings for the iterative search package.

This module hosts package-specific Pydantic settings used by the
iterative research engine (ResearchEngine). It also exposes a few
helpers (``_FormatDict``, ``get_formatted_variables``,
``AsyncContextSerializer``) that the wider ``evoscholar`` settings
aggregate relies on.

The aggregated ``Settings`` class in ``literature_qa.settings``
imports ``ResearchSettings`` from this module.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import (
    Protocol,
    runtime_checkable,
)

from pydantic import BaseModel, ConfigDict, Field


# AsyncContextSerializer lives here because it is the type for
# ``Settings.custom_context_serializer`` (which is configured on the
# aggregated ``Settings`` in ``literature_qa.settings``). Keeping the
# Protocol near the iterative_search runtime helpers makes the
# boundary explicit.


@runtime_checkable
class AsyncContextSerializer(Protocol):
    """Protocol for generating a context string from settings and context."""

    async def __call__(
        self,
        settings: "Settings",
        contexts: Sequence["Context"],
        question: str,
        pre_str: str | None,
    ) -> str: ...


class _FormatDict(dict):  # noqa: FURB189
    """Mock a dictionary and store any missing items."""

    def __init__(self) -> None:
        self.key_set: set[str] = set()

    def __missing__(self, key: str) -> str:
        self.key_set.add(key)
        return key


def get_formatted_variables(s: str) -> set[str]:
    """Returns the set of variables implied by the format string."""
    format_dict = _FormatDict()
    s.format_map(format_dict)
    return format_dict.key_set


class ResearchSettings(BaseModel):
    """Configuration for bounded, multi-provider academic research."""

    model_config = ConfigDict(extra="ignore")

    providers: list[str] = Field(
        default_factory=lambda: ["openalex"]
    )
    max_rounds: int = Field(default=3, ge=1)
    max_candidates_per_round: int = Field(default=20, ge=1)
    max_references_per_node: int = Field(default=10, ge=0)
    partial_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    high_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    ranking_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "relevance": 0.55,
            "recency": 0.15,
            "citation": 0.15,
            "diversity": 0.15,
        }
    )
    per_field_quota: dict[str, int] = Field(default_factory=dict)
    concurrency: int = Field(default=2, ge=1)
    llm_budget_usd: float = Field(default=5.0, ge=0.0)
    token_budget: int = Field(default=200_000, ge=0)
    api_budget: int = Field(default=1000, ge=0)
    embedding_model: str | None = None


__all__ = [
    "AsyncContextSerializer",
    "ResearchSettings",
    "_FormatDict",
    "get_formatted_variables",
]