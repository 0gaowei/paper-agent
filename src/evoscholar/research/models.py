"""
Domain models for the research pipeline.

These models define the data structures used throughout the academic search
and research workflow, including query understanding, paper candidates,
evidence snippets, and final answer summaries.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


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


class RelevanceTier(StrEnum):
    """Relevance tier for paper candidates based on score thresholds."""

    HIGH = "high"
    """Score >= high_threshold (default 0.75). Paper is highly relevant."""

    PARTIAL = "partial"
    """Score >= partial_threshold but < high_threshold (0.5 to 0.75)."""

    LOW = "low"
    """Score < partial_threshold (0.5). Not very relevant."""


class StopReason(StrEnum):
    """Reason why the research session stopped."""

    MAX_ROUNDS_REACHED = "max_rounds_reached"
    """Maximum number of search rounds completed."""

    MAX_HIGH_RELEVANT = "max_high_relevant"
    """Sufficient high-relevance papers found."""

    QUEUE_EMPTY = "queue_empty"
    """No more papers to explore in the queue."""

    BUDGET_EXCEEDED = "budget_exceeded"
    """Token or cost budget exceeded."""

    NO_NEW_PAPERS = "no_new_papers"
    """No new relevant papers found in last round."""

    ERROR = "error"
    """Stopped due to an error."""


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


class CitationEdge(BaseModel):
    """A citation relationship between two papers."""

    source_id: str = Field(description="Stable ID of the citing paper.")
    target_id: str = Field(description="Stable ID of the cited paper.")
    edge_type: str = Field(
        default="cites",
        description="Type of citation relationship ('cites' or 'cited_by').",
    )
    provider: str = Field(
        default="unknown",
        description="Source provider that found this citation edge.",
    )


class AcademicPaper(BaseModel):
    """
    A paper candidate discovered during research.

    This is the primary unit of the research pipeline - papers are discovered,
    scored, ranked, and ultimately used as evidence sources.
    """

    model_config = ConfigDict(extra="ignore")

    stable_id: str = Field(
        description=(
            "Stable unique identifier for this paper. Priority: DOI > "
            "SemanticScholar ID > OpenAlex ID > normalized title+year."
        ),
    )
    title: str | None = Field(default=None, description="Paper title.")
    abstract: str | None = Field(default=None, description="Paper abstract.")
    authors: list[str] = Field(default_factory=list, description="Author names.")
    year: int | None = Field(default=None, description="Publication year.")
    publication_date: datetime | None = Field(
        default=None, description="Full publication date."
    )
    journal: str | None = Field(default=None, description="Journal or venue.")
    doi: str | None = Field(default=None, description="Digital Object Identifier.")
    citation_count: int | None = Field(
        default=None, description="Number of citations."
    )
    pdf_url: str | None = Field(default=None, description="URL to PDF if available.")
    url: str | None = Field(
        default=None, description="Paper URL (e.g., Semantic Scholar page)."
    )
    fields_of_study: list[str] = Field(
        default_factory=list,
        description="Fields of study (e.g., ['Computer Science', 'AI']).",
    )
    source: str = Field(
        default="unknown",
        description="Provider that found this paper (e.g., 'semantic_scholar').",
    )
    sources: list[str] = Field(
        default_factory=list,
        description="All providers that have this paper.",
    )
    citation_ids: list[str] = Field(
        default_factory=list,
        description="IDs of papers this paper cites.",
    )
    cited_by_ids: list[str] = Field(
        default_factory=list,
        description="IDs of papers that cite this paper.",
    )

    relevance_score: float | None = Field(
        default=None,
        description="0-1 relevance score to the query.",
    )
    relevance_tier: RelevanceTier = Field(
        default=RelevanceTier.LOW,
        description="Computed relevance tier based on thresholds.",
    )
    ranking_factors: dict[str, float] = Field(
        default_factory=dict,
        description="Detailed ranking factor scores.",
    )

    def __hash__(self) -> int:
        return hash(self.stable_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AcademicPaper):
            return NotImplemented
        return self.stable_id == other.stable_id


class SearchRound(BaseModel):
    """A single round of the BFS search process."""

    round_number: int = Field(description="1-indexed round number.")
    queries_executed: list[str] = Field(
        default_factory=list,
        description="Queries that were executed in this round.",
    )
    papers_discovered: int = Field(
        default=0,
        description="Number of new papers discovered.",
    )
    papers_evaluated: int = Field(
        default=0,
        description="Number of papers evaluated for relevance.",
    )
    high_relevant_found: int = Field(
        default=0,
        description="Number of high-relevance papers found.",
    )
    partial_relevant_found: int = Field(
        default=0,
        description="Number of partial-relevance papers found.",
    )
    citations_expanded: int = Field(
        default=0,
        description="Number of citation edges explored.",
    )
    subqueries_generated: int = Field(
        default=0,
        description="Number of new subqueries generated for next round.",
    )
    duration_ms: int | None = Field(
        default=None,
        description="Duration of this round in milliseconds.",
    )


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


class SearchResult(BaseModel):
    """Result from an academic search provider."""

    papers: list[AcademicPaper] = Field(
        default_factory=list,
        description="Papers returned by the search.",
    )
    provider: str = Field(description="Provider name (e.g., 'semantic_scholar').")
    query: str = Field(description="The query that was searched.")
    elapsed_ms: int | None = Field(
        default=None,
        description="Time taken for the search in milliseconds.",
    )
    success: bool = Field(
        default=True,
        description="Whether the search was successful.",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if the search failed.",
    )
    total_results: int | None = Field(
        default=None,
        description="Total results available (may be larger than returned).",
    )


class ResearchSession(BaseModel):
    """
    Complete research session tracking all state and results.

    This is the main output of the research pipeline and contains
    everything needed to understand the research process and results.
    """

    model_config = ConfigDict(extra="ignore")

    id: UUID = Field(default_factory=uuid4, description="Unique session identifier.")
    query: str = Field(description="The original research query.")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the session was created.",
    )
    completed_at: datetime | None = Field(
        default=None, description="When the session completed."
    )

    query_understanding: QueryUnderstanding | None = Field(
        default=None,
        description="LLM analysis of the query.",
    )

    search_rounds: list[SearchRound] = Field(
        default_factory=list,
        description="All search rounds executed.",
    )
    citation_graph: list[CitationEdge] = Field(
        default_factory=list,
        description="Citation edges discovered.",
    )
    all_papers: dict[str, AcademicPaper] = Field(
        default_factory=dict,
        description="All papers discovered (stable_id -> paper).",
    )

    evidence: list[EvidenceSnippet] = Field(
        default_factory=list,
        description="Collected evidence snippets.",
    )
    final_papers: list[AcademicPaper] = Field(
        default_factory=list,
        description="Final ranked and selected papers.",
    )

    answer: AnswerSummary | None = Field(
        default=None, description="Final synthesized answer."
    )

    usage: UsageStats = Field(
        default_factory=UsageStats,
        description="Resource usage statistics.",
    )

    stop_reason: StopReason | None = Field(
        default=None,
        description="Why the session stopped.",
    )
    error: str | None = Field(
        default=None,
        description="Error message if session failed.",
    )

    @property
    def high_relevant_papers(self) -> list[AcademicPaper]:
        """Papers with high relevance."""
        return [
            p for p in self.final_papers if p.relevance_tier == RelevanceTier.HIGH
        ]

    @property
    def partial_relevant_papers(self) -> list[AcademicPaper]:
        """Papers with partial relevance."""
        return [
            p for p in self.final_papers if p.relevance_tier == RelevanceTier.PARTIAL
        ]
