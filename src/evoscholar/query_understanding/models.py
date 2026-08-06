"""Domain models for query understanding.

Extracts QueryIntent, Domain, SubQuery, and QueryUnderstanding from research/models.py.
These models are owned by the query_understanding package.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class QueryIntent(StrEnum):
    """The primary intent of a research query."""

    SURVEY = "survey"
    """Comprehensive overview of a topic."""

    SPECIFIC = "specific"
    """Looking for specific information or facts."""

    COMPARATIVE = "comparative"
    """Comparing multiple approaches or papers."""

    CURRENT_STATE = "current_state"
    """Finding the current state of research in an area."""

    BACKGROUND = "background"
    """Finding foundational or background literature."""

    GENERAL = "general"
    """General exploration without specific goal."""


class Domain(StrEnum):
    """Research domain categories."""

    CS_AI = "cs_ai"
    """Computer Science / Artificial Intelligence."""

    NLP = "nlp"
    """Natural Language Processing."""

    ML = "ml"
    """Machine Learning."""

    CV = "cv"
    """Computer Vision."""

    BIO = "bio"
    """Biology and Life Sciences."""

    MED = "med"
    """Medicine and Health Sciences."""

    PHYSICS = "physics"
    """Physics."""

    CHEMISTRY = "chemistry"
    """Chemistry."""

    ECONOMICS = "economics"
    """Economics."""

    PSYCHOLOGY = "psychology"
    """Psychology."""

    SOCIAL = "social"
    """Social Sciences."""

    MULTIDISCIPLINARY = "multidisciplinary"
    """Cross-disciplinary or general."""

    UNKNOWN = "unknown"


class SubQuery(BaseModel):
    """A decomposed sub-query generated from query understanding."""

    query: str = Field(description="The sub-query text for searching.")
    purpose: str = Field(
        default="",
        description="Why this sub-query was generated.",
    )
    priority: int = Field(
        default=1,
        ge=0,
        le=10,
        description="Priority of this sub-query (higher = more important).",
    )
    parent_intent: QueryIntent = Field(
        default=QueryIntent.GENERAL,
        description="The parent query intent this addresses.",
    )
    domain: Domain = Field(
        default=Domain.UNKNOWN,
        description="Primary domain for this sub-query.",
    )


class QueryUnderstanding(BaseModel):
    """Result of analyzing and expanding a research query."""

    original_query: str = Field(description="The original user query.")
    intent: QueryIntent = Field(
        default=QueryIntent.GENERAL,
        description="Primary intent of the query.",
    )
    domains: list[Domain] = Field(
        default_factory=lambda: [Domain.UNKNOWN],
        description="Relevant research domains.",
    )
    entities: list[str] = Field(
        default_factory=list,
        description="Key entities mentioned in the query.",
    )
    suitable_sources: list[str] = Field(
        default_factory=list,
        description="Recommended data sources (e.g., 'semantic_scholar', 'openalex').",
    )
    subqueries: list[SubQuery] = Field(
        default_factory=list,
        description="Decomposed sub-queries for searching.",
    )
    search_strategy: str = Field(
        default="general",
        description="Overall search strategy (e.g., 'survey', 'domain', 'general').",
    )
