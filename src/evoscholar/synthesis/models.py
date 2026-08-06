"""Domain models for the synthesis package.

Contains evidence, answer, and usage statistics models that are
owned by the synthesis package.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvidenceSnippet(BaseModel):
    """A piece of evidence extracted from a paper."""

    paper_id: str = Field(description="Stable ID of the source paper.")
    paper_title: str | None = Field(default=None, description="Title of the source paper.")
    content: str = Field(description="The evidence content (summary or excerpt).")
    relevance_score: float = Field(
        description="0-1 relevance score for this evidence.",
    )
    subquery_addressed: str | None = Field(
        default=None,
        description="Which sub-query this evidence addresses.",
    )
    citation: str | None = Field(
        default=None,
        description="Citation text for this evidence.",
    )
    provider: str = Field(
        default="unknown",
        description="Source provider for this evidence.",
    )


class AnswerSummary(BaseModel):
    """Final synthesized answer from the research."""

    answer: str = Field(description="The synthesized answer text.")
    subqueries_covered: list[str] = Field(
        default_factory=list,
        description="Sub-queries that were addressed.",
    )
    evidence_used: int = Field(
        default=0,
        description="Number of evidence snippets used.",
    )
    papers_cited: list[str] = Field(
        default_factory=list,
        description="Stable IDs of papers cited in the answer.",
    )
    citations: list[str] = Field(
        default_factory=list,
        description="Formatted citation strings.",
    )
    raw_answer: str | None = Field(
        default=None,
        description="Raw LLM answer before formatting.",
    )
    has_successful_answer: bool | None = Field(
        default=None,
        description="Whether the answer was successfully generated.",
    )


class UsageStats(BaseModel):
    """Statistics about resource usage during research."""

    llm_calls: int = Field(default=0, description="Number of LLM API calls.")
    llm_prompt_tokens: int = Field(default=0, description="Total LLM prompt tokens.")
    llm_completion_tokens: int = Field(
        default=0, description="Total LLM completion tokens."
    )
    llm_cost_usd: float = Field(default=0.0, description="Total LLM cost in USD.")
    embedding_calls: int = Field(default=0, description="Number of embedding calls.")
    embedding_tokens: int = Field(default=0, description="Total embedding tokens.")
    api_calls_by_provider: dict[str, int] = Field(
        default_factory=dict,
        description="API calls per provider.",
    )
    search_rounds: int = Field(default=0, description="Number of search rounds.")
    papers_discovered: int = Field(default=0, description="Total papers discovered.")
    papers_evaluated: int = Field(default=0, description="Total papers evaluated.")
    papers_in_final_set: int = Field(
        default=0, description="Papers in final ranked set."
    )
    total_duration_ms: int | None = Field(
        default=None, description="Total duration in milliseconds."
    )
