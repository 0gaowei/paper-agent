"""SSE event payload formatting for the synthesis package.

This module contains the SSE event payload formatting functions that convert
server schemas to SSE payloads with camelCase field names for the frontend.

Per the field mapping rules (roadmap.md §6), SSE events MUST use:
  - totalTokens (NOT tokenUsage)
  - totalCost (NOT cost)
  - searchCalls (NOT apiCalls)
  - llmCalls
"""

from __future__ import annotations

from typing import Any


def format_usage_event(
    total_tokens: int,
    total_cost: float,
    search_calls: int,
    llm_calls: int,
    **extra: Any,
) -> dict[str, Any]:
    """Format a usage/stats SSE event payload with camelCase field names.

    Args:
        total_tokens: Total LLM tokens (prompt + completion).
        total_cost: Total cost in USD.
        search_calls: Number of search API calls.
        llm_calls: Number of LLM API calls.
        **extra: Additional fields to include in the payload.

    Returns:
        SSE event data dict with camelCase field names matching frontend SearchStats.
    """
    payload = {
        "totalTokens": total_tokens,
        "totalCost": total_cost,
        "searchCalls": search_calls,
        "llmCalls": llm_calls,
    }
    payload.update(extra)
    return payload


def format_answer_event(
    answer: str,
    papers_used: list[str] | None = None,
    citations: list[str] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Format an answer SSE event payload.

    Args:
        answer: The synthesized answer text.
        papers_used: List of paper IDs used in the answer.
        citations: List of citation strings.
        **extra: Additional fields to include in the payload.

    Returns:
        SSE event data dict for the answer event.
    """
    payload: dict[str, Any] = {
        "answer": answer,
        "answerSummary": answer,
    }
    if papers_used is not None:
        payload["papers_used"] = papers_used
    if citations is not None:
        payload["citations"] = citations
    payload.update(extra)
    return payload


def format_progress_event(
    event_type: str,
    message: str | None = None,
    snippets_found: int | None = None,
    answer_length: int | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Format a progress SSE event payload.

    Args:
        event_type: Type of progress event (e.g., 'evidence_extraction', 'answer_synthesis').
        message: Optional message for the event.
        snippets_found: Number of evidence snippets found.
        answer_length: Length of the synthesized answer.
        **extra: Additional fields to include in the payload.

    Returns:
        SSE event data dict for the progress event.
    """
    payload: dict[str, Any] = {}
    if message is not None:
        payload["message"] = message
    if snippets_found is not None:
        payload["snippets_found"] = snippets_found
    if answer_length is not None:
        payload["answer_length"] = answer_length
    payload.update(extra)
    return payload


def format_round_event(
    round_num: int,
    active_subqueries: list[str] | None = None,
    papers_count: int | None = None,
    high_relevance_count: int | None = None,
    partial_count: int | None = None,
    edges_added: int | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Format a search round SSE event payload.

    Args:
        round_num: The 0-indexed round number.
        active_subqueries: List of subqueries executed in this round.
        papers_count: Number of papers evaluated.
        high_relevance_count: Number of highly relevant papers found.
        partial_count: Number of partially relevant papers found.
        edges_added: Number of citation edges added.
        **extra: Additional fields to include in the payload.

    Returns:
        SSE event data dict for the round event.
    """
    payload: dict[str, Any] = {"round": round_num}
    if active_subqueries is not None:
        payload["active_subqueries"] = active_subqueries
    if papers_count is not None:
        payload["papers_count"] = papers_count
    if high_relevance_count is not None:
        payload["high_relevance_count"] = high_relevance_count
    if partial_count is not None:
        payload["partial_count"] = partial_count
    if edges_added is not None:
        payload["edges_added"] = edges_added
    payload.update(extra)
    return payload


def format_paper_found_event(
    paper_id: str,
    title: str,
    year: int | None = None,
    authors: list[str] | None = None,
    doi: str | None = None,
    citation_count: int | None = None,
    relevance_tier: str | None = None,
    round_num: int | None = None,
    abstract: str | None = None,
    url: str | None = None,
    source: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Format a paper_found SSE event payload.

    Args:
        paper_id: Stable paper ID.
        title: Paper title.
        year: Publication year.
        authors: List of author names.
        doi: DOI.
        citation_count: Number of citations.
        relevance_tier: Relevance tier (high/partial/low).
        round_num: The 0-indexed round in which this paper was discovered.
        abstract: Paper abstract.
        url: Paper URL.
        source: Source provider.
        **extra: Additional fields to include in the payload.

    Returns:
        SSE event data dict for the paper_found event.
    """
    payload: dict[str, Any] = {
        "id": paper_id,
        "title": title,
    }
    if year is not None:
        payload["year"] = year
    if authors is not None:
        payload["authors"] = authors
    if doi is not None:
        payload["doi"] = doi
    if citation_count is not None:
        payload["citationCount"] = citation_count
    if relevance_tier is not None:
        payload["relevanceTier"] = relevance_tier
    if round_num is not None:
        payload["round"] = round_num
    if abstract is not None:
        payload["abstract"] = abstract
    if url is not None:
        payload["url"] = url
    if source is not None:
        payload["source"] = source
    payload.update(extra)
    return payload


def format_understanding_event(
    intent: str,
    domain: str | None = None,
    entities: list[str] | None = None,
    suitable_sources: list[str] | None = None,
    subqueries: list[dict[str, Any]] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Format an understanding SSE event payload.

    Args:
        intent: Query intent.
        domain: Research domain.
        entities: Key entities in the query.
        suitable_sources: Recommended search sources.
        subqueries: List of subquery dicts.
        **extra: Additional fields to include in the payload.

    Returns:
        SSE event data dict for the understanding event.
    """
    payload: dict[str, Any] = {"intent": intent}
    if domain is not None:
        payload["domain"] = domain
    if entities is not None:
        payload["entities"] = entities
    if suitable_sources is not None:
        payload["suitable_sources"] = suitable_sources
    if subqueries is not None:
        payload["subqueries"] = subqueries
    payload.update(extra)
    return payload


def format_error_event(
    error: str,
    stop_reason: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Format an error SSE event payload.

    Args:
        error: Error message.
        stop_reason: Stop reason if applicable.
        **extra: Additional fields to include in the payload.

    Returns:
        SSE event data dict for the error event.
    """
    payload: dict[str, Any] = {"error": error}
    if stop_reason is not None:
        payload["stop_reason"] = stop_reason
    payload.update(extra)
    return payload


def format_done_event(
    stop_reason: str | None = None,
    rounds: int | None = None,
    papers_count: int | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Format a done SSE event payload.

    Args:
        stop_reason: Why the session stopped.
        rounds: Number of search rounds completed.
        papers_count: Total papers discovered.
        **extra: Additional fields to include in the payload.

    Returns:
        SSE event data dict for the done event.
    """
    payload: dict[str, Any] = {}
    if stop_reason is not None:
        payload["stop_reason"] = stop_reason
    if rounds is not None:
        payload["rounds"] = rounds
    if papers_count is not None:
        payload["papers_count"] = papers_count
    payload.update(extra)
    return payload
