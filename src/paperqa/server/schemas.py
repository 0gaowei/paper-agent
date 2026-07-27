"""Pydantic schemas for the server API and research domain models.

These schemas are designed to be:
- Compatible with existing PaperQA Pydantic v2 defaults (model_config)
- JSON-serializable for SSE events and API responses
- Independent of the core paperqa library types where needed
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Research domain models (stub implementations for the server layer)
# These may be replaced by real implementations from src/paperqa/research/models.py
# when that module is available in a later task.
# ---------------------------------------------------------------------------


class RelevanceTier(str, Enum):
    """Relevance tier for a paper in a search session."""

    HIGH = "high"
    PARTIAL = "partial"
    IRRELEVANT = "irrelevant"


class PaperSource(str, Enum):
    """Source of a paper in a search session."""

    SEMANTIC_SCHOLAR = "semantic_scholar"
    OPENTALEX = "openalex"
    CROSSREF = "crossref"
    MANUAL = "manual"


class EvidenceSnippet(BaseModel):
    """A snippet of evidence from a paper."""

    text: str = Field(description="The evidence text.")
    page: int | None = Field(default=None, description="Page number in the PDF.")
    score: float = Field(
        default=0.0,
        ge=0.0,
        description="Relevance score (0–10, matching PaperQA Context.score).",
    )


class AcademicPaper(BaseModel):
    """An academic paper found during a research session."""

    model_config = BaseModel.model_config

    id: str = Field(
        description="Stable paper ID (DOI > S2 ID > openalex_id > title+year hash)."
    )
    title: str = Field(description="Paper title.")
    year: int | None = Field(default=None, description="Publication year.")
    authors: list[str] = Field(default_factory=list, description="List of author names.")
    doi: str | None = Field(default=None, description="DOI (without URL prefix).")
    s2_id: str | None = Field(default=None, description="Semantic Scholar paper ID.")
    openalex_id: str | None = Field(
        default=None, description="OpenAlex work ID (e.g. W1234567890)."
    )
    citation_count: int | None = Field(
        default=None, description="Total citation count."
    )
    relevance_tier: RelevanceTier = Field(
        default=RelevanceTier.IRRELEVANT,
        description="Relevance tier based on dual-threshold scoring.",
    )
    abstract: str | None = Field(default=None, description="Paper abstract.")
    url: str | None = Field(
        default=None, description="URL to the paper PDF or landing page."
    )
    source: PaperSource | None = Field(
        default=None, description="Which search provider found this paper."
    )
    referenced_works: list[str] = Field(
        default_factory=list,
        description=(
            "IDs of works cited by this paper "
            "(used for citation graph expansion)."
        ),
    )
    citing_works: list[str] = Field(
        default_factory=list,
        description="IDs of works that cite this paper.",
    )
    embedding: list[float] | None = Field(
        default=None,
        exclude=True,
        description="Semantic embedding vector (not serialized by default).",
    )

    def to_event_dict(self) -> dict[str, Any]:
        """Convert to dict for SSE event data."""
        return self.model_dump(exclude={"embedding"}, exclude_none=True)


class SubQuery(BaseModel):
    """A sub-query generated from query understanding."""

    model_config = BaseModel.model_config

    text: str = Field(description="The sub-query text.")
    intent: str | None = Field(
        default=None,
        description="The intent of this sub-query (e.g. 'specific_finding', 'background').",
    )
    round: int = Field(
        default=0, ge=0, description="The research round this sub-query belongs to."
    )


class QueryUnderstanding(BaseModel):
    """Result of understanding a user query."""

    model_config = BaseModel.model_config

    intent: str = Field(
        description=(
            "High-level intent: 'survey' (broad overview), "
            "'domain' (specific field), or 'general' (answer a question)."
        )
    )
    domain: str | None = Field(
        default=None, description="The scientific domain or field."
    )
    entities: list[str] = Field(
        default_factory=list,
        description="Key entities extracted from the query.",
    )
    suitable_sources: list[str] = Field(
        default_factory=list,
        description="Recommended search sources.",
    )
    subqueries: list[SubQuery] = Field(
        default_factory=list, description="Expanded search sub-queries."
    )


class ResearchSession(BaseModel):
    """A research session containing query, papers, and results."""

    model_config = BaseModel.model_config

    id: str = Field(description="Unique session identifier.")
    query: str = Field(description="The original user query.")
    status: Literal[
        "pending", "running", "done", "cancelled", "error"
    ] = Field(default="pending", description="Session status.")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Session creation timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp.",
    )
    understanding: QueryUnderstanding | None = Field(
        default=None, description="Query understanding result."
    )
    papers: dict[str, AcademicPaper] = Field(
        default_factory=dict,
        description="Map of paper ID -> AcademicPaper.",
    )
    subqueries: list[SubQuery] = Field(
        default_factory=list,
        description="All sub-queries generated across rounds.",
    )
    rounds: int = Field(
        default=0, ge=0, description="Number of research rounds completed."
    )
    answer: str | None = Field(
        default=None, description="Synthesized answer text."
    )
    evidence: dict[str, list[EvidenceSnippet]] = Field(
        default_factory=dict,
        description="Map of paper ID -> list of evidence snippets.",
    )
    stop_reason: str | None = Field(
        default=None,
        description=(
            "Why the search stopped: 'max_rounds', 'high_relevance_collected', "
            "'budget_exhausted', 'cancelled', 'error'."
        ),
    )
    error_message: str | None = Field(
        default=None, description="Error message if status is 'error'."
    )
    usage: UsageStats | None = Field(
        default=None, description="Aggregated token and cost usage."
    )

    def to_event_dict(self) -> dict[str, Any]:
        """Convert to dict for SSE event data."""
        return self.model_dump(exclude={"usage"}, exclude_none=True)


class UsageStats(BaseModel):
    """Aggregated usage statistics for a session or user."""

    model_config = BaseModel.model_config

    total_tokens: int = Field(default=0, ge=0, description="Total tokens used.")
    prompt_tokens: int = Field(default=0, ge=0, description="Prompt tokens.")
    completion_tokens: int = Field(default=0, ge=0, description="Completion tokens.")
    total_cost: float = Field(default=0.0, ge=0.0, description="Total cost in USD.")
    llm_calls: int = Field(default=0, ge=0, description="Number of LLM calls.")
    search_calls: int = Field(default=0, ge=0, description="Number of search API calls.")
    rounds: int = Field(default=0, ge=0, description="Number of research rounds.")


# ---------------------------------------------------------------------------
# API request / response models
# ---------------------------------------------------------------------------


class NewSessionRequest(BaseModel):
    """Request body for POST /api/sessions."""

    query: str = Field(min_length=1, description="The research question or query.")
    config: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional researcher configuration overrides. "
            "Keys match ResearchSettings field names."
        ),
    )


class SessionResponse(BaseModel):
    """Response for GET /api/sessions/{id}."""

    session: ResearchSession = Field(description="The full research session.")
    papers: list[AcademicPaper] = Field(
        description="Papers in the session as a list."
    )
    events_emitted: int = Field(
        default=0, ge=0, description="Number of SSE events emitted so far."
    )


class HistoryEntry(BaseModel):
    """A brief entry for session history listing."""

    id: str = Field(description="Session ID.")
    query: str = Field(description="The original query.")
    status: str = Field(description="Final session status.")
    created_at: datetime = Field(description="Session creation time.")
    updated_at: datetime = Field(description="Last update time.")
    papers_count: int = Field(description="Number of papers found.")
    rounds: int = Field(description="Number of rounds completed.")
    answer_length: int = Field(
        default=0, description="Character length of the answer."
    )
    duration: float = Field(
        default=0.0, description="Session duration in seconds."
    )
    cost: float = Field(
        default=0.0, description="Total cost in USD."
    )


class SettingsPayload(BaseModel):
    """Settings read/write via the API (never exposes API keys)."""

    researcher_llm: str | None = Field(
        default=None,
        description="LLM model used for research.",
    )
    researcher_llm_config: dict[str, Any] | None = Field(
        default=None,
        description="LLM configuration (no API keys).",
    )
    summary_llm: str | None = Field(
        default=None,
        description="LLM model used for summarization.",
    )
    # API configuration fields (stored server-side, returned without exposing secrets)
    llm_api_key: str | None = Field(
        default=None,
        description="LLM API key (stored server-side, never returned to client).",
    )
    llm_base_url: str | None = Field(
        default=None,
        description="LLM base URL for custom endpoints.",
    )
    llm_provider: str | None = Field(
        default=None,
        description="LLM provider (e.g., openai, anthropic).",
    )
    max_rounds: int | None = Field(
        default=None, ge=1, description="Maximum research rounds."
    )
    candidates_per_round: int | None = Field(
        default=None, ge=1, description="Candidates per round."
    )
    citation_expansion_limit: int | None = Field(
        default=None, ge=0, description="Max citation expansions per round."
    )
    high_relevance_threshold: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="High relevance threshold (0–1)."
    )
    partial_relevance_threshold: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="Partial relevance threshold (0–1)."
    )

    # Key configuration status — always read-only booleans, never keys
    llm_configured: bool = Field(
        default=False,
        description="Whether an LLM API key is configured.",
    )
    s2_configured: bool = Field(
        default=False,
        description="Whether a Semantic Scholar API key is configured.",
    )
    openalex_configured: bool = Field(
        default=False,
        description="Whether an OpenAlex API key is configured.",
    )
