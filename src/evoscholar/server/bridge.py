"""Bridge between `paperqa.research` (the real engine) and
`paperqa.server` (the FastAPI layer with its own stub schemas).

The server exposes its own Pydantic models (`schemas.ResearchSession`,
`schemas.AcademicPaper`, `schemas.UsageStats`, …) that the frontend
already consumes. The `research` package defines a richer
`ResearchSession` (with UUID id, list-shaped `evidence`, `AnswerSummary`
object, `SearchRound`, `CitationEdge`, …).

This module converts:
  - a research `ResearchSession` → server `ResearchSession`
  - research progress signals → SSE `SSEEvent` payloads matching the
    exact ordering the frontend store expects:
        understanding → subqueries → round_started → paper_found
        → partial_documents → answer → usage → done.

The bridge is intentionally side-effect free so it can be unit-tested
without spinning up the FastAPI app or any external LLM/provider.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from evoscholar.server.events import EventType
from evoscholar.server.schemas import (
    AcademicPaper as ServerPaper,
)
from evoscholar.server.schemas import (
    EvidenceSnippet as ServerEvidence,
)
from evoscholar.server.schemas import (
    PaperSource,
    QueryUnderstanding,
    RelevanceTier,
    ResearchSession as ServerSession,
)
from evoscholar.server.schemas import (
    SubQuery as ServerSubQuery,
)
from evoscholar.server.schemas import (
    UsageStats as ServerUsage,
)

if TYPE_CHECKING:
    from evoscholar.iterative_search.models import ResearchSession as ResearchSessionModel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Source enums -> server enums
# ---------------------------------------------------------------------------

_SOURCE_TO_SERVER: dict[str, PaperSource] = {
    "openalex": PaperSource.OPENTALEX,
    "crossref": PaperSource.CROSSREF,
    "manual": PaperSource.MANUAL,
}

_TIER_TO_SERVER: dict[str, RelevanceTier] = {
    "high": RelevanceTier.HIGH,
    "partial": RelevanceTier.PARTIAL,
    "low": RelevanceTier.IRRELEVANT,
}


def _to_server_paper(paper: Any, round_number: int | None = None) -> ServerPaper:
    """Map a research `AcademicPaper` to the server `AcademicPaper`.

    Args:
        paper: The research AcademicPaper model.
        round_number: The 0-indexed round in which this paper was discovered.
            None if the round is unknown.
    """
    source = _SOURCE_TO_SERVER.get(
        str(paper.source).lower(),
        PaperSource.MANUAL,
    )
    tier = _TIER_TO_SERVER.get(
        str(getattr(paper, "relevance_tier", "low")).lower(),
        RelevanceTier.IRRELEVANT,
    )
    return ServerPaper(
        id=paper.stable_id,
        title=paper.title or "",
        year=paper.year,
        authors=list(paper.authors or []),
        doi=paper.doi,
        citation_count=paper.citation_count,
        relevance_tier=tier,
        round=round_number,
        abstract=paper.abstract,
        url=paper.pdf_url or paper.url,
        source=source,
        referenced_works=list(paper.citation_ids or []),
        citing_works=list(paper.cited_by_ids or []),
    )


def _to_server_subquery(sub: Any, round_number: int = 0) -> ServerSubQuery:
    """Map a research `SubQuery` to the server `SubQuery`.

    Args:
        sub: The research SubQuery model.
        round_number: The 0-indexed round this subquery belongs to.
            Subqueries generated during query understanding (before search rounds)
            should use round=0. Subqueries generated during search rounds
            should use 1-indexed round numbers converted to 0-indexed.
    """
    purpose = getattr(sub, "purpose", "") or ""
    return ServerSubQuery(
        text=sub.query,
        intent=purpose or "general",
        round=round_number,
    )


def _to_server_understanding(query: str, ru: Any | None) -> QueryUnderstanding:
    """Map a research `QueryUnderstanding` to the server one."""
    if ru is None:
        return QueryUnderstanding(
            intent="general",
            domain=None,
            entities=[],
            suitable_sources=[],
            subqueries=[ServerSubQuery(text=query, intent="general", round=0)],
        )
    domains = [str(d).replace("cs_ai", "computer science").replace("_", " ")
               for d in (getattr(ru, "domains", []) or [])]
    domain = domains[0] if domains else None
    subqueries = [
        _to_server_subquery(s, round_number=0) for s in (getattr(ru, "subqueries", []) or [])
    ] or [ServerSubQuery(text=query, intent="general", round=0)]
    return QueryUnderstanding(
        intent=str(getattr(ru, "intent", "general") or "general"),
        domain=domain,
        entities=list(getattr(ru, "entities", []) or []),
        suitable_sources=list(getattr(ru, "suitable_sources", []) or []),
        subqueries=subqueries,
    )


def _to_server_usage(usage: Any) -> ServerUsage:
    """Map a research `UsageStats` to the server `UsageStats`."""
    total_tokens = int(
        getattr(usage, "llm_prompt_tokens", 0)
        + getattr(usage, "llm_completion_tokens", 0)
    )
    api_calls = sum(
        int(v) for v in (getattr(usage, "api_calls_by_provider", {}) or {}).values()
    )
    return ServerUsage(
        total_tokens=total_tokens,
        prompt_tokens=int(getattr(usage, "llm_prompt_tokens", 0)),
        completion_tokens=int(getattr(usage, "llm_completion_tokens", 0)),
        total_cost=float(getattr(usage, "llm_cost_usd", 0.0)),
        llm_calls=int(getattr(usage, "llm_calls", 0)),
        search_calls=api_calls,
        rounds=int(getattr(usage, "search_rounds", 0)),
    )


def _to_server_evidence(snippets: list[Any]) -> dict[str, list[ServerEvidence]]:
    """Map research `EvidenceSnippet` list to a per-paper dict."""
    out: dict[str, list[ServerEvidence]] = {}
    for snippet in snippets or []:
        paper_id = getattr(snippet, "paper_id", None) or "unknown"
        out.setdefault(paper_id, []).append(
            ServerEvidence(
                text=snippet.content or "",
                page=None,
                score=float(snippet.relevance_score or 0.0) * 10.0,
            )
        )
    return out


def _stop_reason_to_status(stop_reason: Any) -> str:
    """Map a research `StopReason` to the server session status."""
    if stop_reason is None:
        return "running"
    value = str(stop_reason).lower()
    if value.endswith("error"):
        return "error"
    if value.endswith("budget_exceeded"):
        return "done"
    return "done"


def research_to_server_session(
    rs: "ResearchSessionModel", server_id: str
) -> ServerSession:
    """Convert a research `ResearchSession` to the server shape.

    Args:
        rs: The output of `ResearchEngine.arun()`.
        server_id: The session ID the server assigned (we cannot use the
            research UUID because the frontend and repository store the
            server-issued string id).
    """
    # Build a mapping of paper_id -> round_number (0-indexed) for papers discovered during search
    paper_rounds: dict[str, int] = {}
    if rs.search_rounds:
        for rnd in rs.search_rounds:
            round_idx = rnd.round_number - 1  # Convert to 0-indexed
            # Papers discovered in this round: candidates from searches + expanded refs
            # The engine adds papers to session.all_papers as they are discovered
            # We track papers by their order of appearance in rounds
            pass
    # Track papers discovered per round by looking at search results per round
    # For now, we'll assign round based on when papers first appear in all_papers
    # and match against the papers_discovered count per round
    papers = {}
    paper_order: list[str] = list((getattr(rs, "all_papers", {}) or {}).keys())
    if rs.search_rounds:
        # Calculate cumulative papers discovered up to each round
        cumulative = 0
        for rnd in rs.search_rounds:
            round_idx = rnd.round_number - 1  # 0-indexed
            # Papers discovered in this round
            round_end = cumulative + rnd.papers_discovered
            for paper_id in paper_order[cumulative:round_end]:
                paper_rounds[paper_id] = round_idx
            cumulative = round_end
            if cumulative >= len(paper_order):
                break
    papers = {
        p_id: _to_server_paper(p, round_number=paper_rounds.get(p_id))
        for p_id, p in ((getattr(rs, "all_papers", {}) or {}).items())
    }
    evidence = _to_server_evidence(getattr(rs, "evidence", []) or [])
    answer_text = ""
    if rs.answer is not None:
        answer_text = rs.answer.answer or rs.answer.raw_answer or ""
    subqueries: list[ServerSubQuery] = []
    if rs.query_understanding is not None:
        # Initial subqueries from query understanding stage are at round 0
        for s in (rs.query_understanding.subqueries or []):
            subqueries.append(_to_server_subquery(s, round_number=0))
    # Add follow-up subqueries from search rounds (1-indexed -> 0-indexed)
    if rs.search_rounds:
        for rnd in rs.search_rounds:
            if rnd.subqueries_generated > 0:
                # Follow-up subqueries generated during this round
                for query_text in rnd.queries_executed:
                    # Check if this query is a follow-up (not in initial subqueries)
                    is_followup = True
                    if rs.query_understanding:
                        for init_sq in (rs.query_understanding.subqueries or []):
                            if init_sq.query == query_text:
                                is_followup = False
                                break
                    if is_followup:
                        subqueries.append(ServerSubQuery(
                            text=query_text,
                            intent="followup",
                            round=rnd.round_number - 1,  # Convert to 0-indexed
                        ))
    return ServerSession(
        id=server_id,
        query=rs.query,
        status=_stop_reason_to_status(rs.stop_reason),
        created_at=rs.created_at,
        updated_at=rs.completed_at or rs.created_at,
        understanding=_to_server_understanding(rs.query, rs.query_understanding),
        papers=papers,
        subqueries=subqueries,
        rounds=int(getattr(rs.usage, "search_rounds", 0)),
        answer=answer_text,
        evidence=evidence,
        stop_reason=str(rs.stop_reason.value) if rs.stop_reason else None,
        error_message=rs.error,
        usage=_to_server_usage(rs.usage),
    )


# ---------------------------------------------------------------------------
# SSE event generation from a research session
# ---------------------------------------------------------------------------


class ResearchEventBridge:
    """Translate research progress into the SSE events the frontend expects.

    The frontend store relies on a specific event sequence:
        understanding → subqueries → (round_started → paper_found → partial_documents)*
        → answer → usage → done.

    The research engine exposes a list of `SearchRound`s after the fact
    (the engine runs to completion synchronously from the caller's
    perspective). We replay those rounds as a stream of events so the
    UI sees progress instead of a single block at the end.
    """

    def __init__(self, session_id: str, rs: "ResearchSessionModel") -> None:
        self.session_id = session_id
        self.rs = rs

    def _emit(self, event_type: EventType, data: dict[str, Any]) -> dict[str, Any]:
        return {"session_id": self.session_id, "type": event_type, "data": data}

    def build_events(self) -> list[dict[str, Any]]:
        """Return the ordered list of SSE payloads to publish."""
        events: list[dict[str, Any]] = []
        ru = self.rs.query_understanding
        events.append(
            self._emit(
                EventType.UNDERSTANDING,
                _to_server_understanding(self.rs.query, ru).model_dump(
                    exclude_none=True
                ),
            )
        )
        sub_payload = [
            _to_server_subquery(s, round_number=0).model_dump(exclude_none=True)
            for s in (ru.subqueries if ru else [])
        ] or [{"text": self.rs.query, "intent": "general", "round": 0}]
        events.append(self._emit(EventType.SUBQUERIES, {"subqueries": sub_payload}))

        # Build paper -> round mapping for SSE events
        paper_order: list[str] = list((self.rs.all_papers or {}).keys())
        paper_rounds: dict[str, int] = {}
        if self.rs.search_rounds:
            cumulative = 0
            for rnd in self.rs.search_rounds:
                round_idx = rnd.round_number - 1  # 0-indexed
                round_end = cumulative + rnd.papers_discovered
                for paper_id in paper_order[cumulative:round_end]:
                    paper_rounds[paper_id] = round_idx
                cumulative = round_end
                if cumulative >= len(paper_order):
                    break

        papers_seen: set[str] = set()
        for round_ in self.rs.search_rounds or []:
            events.append(
                self._emit(
                    EventType.ROUND_STARTED,
                    {
                        "round": round_.round_number - 1,
                        "active_subqueries": list(round_.queries_executed),
                    },
                )
            )
            for paper_id, paper in (self.rs.all_papers or {}).items():
                if paper_id in papers_seen:
                    continue
                if getattr(paper, "relevance_tier", None) is None:
                    continue
                papers_seen.add(paper_id)
                events.append(
                    self._emit(
                        EventType.PAPER_FOUND,
                        _to_server_paper(paper, round_number=paper_rounds.get(paper_id)).to_event_dict(),
                    )
                )
            events.append(
                self._emit(
                    EventType.PARTIAL_DOCUMENTS,
                    {
                        "papers_count": round_.papers_evaluated,
                        "high_relevance_count": round_.high_relevant_found,
                        "partial_count": round_.partial_relevant_found,
                        "round": round_.round_number,
                    },
                )
            )

        # Edge count: emit one citation_expanded event per round that expanded refs
        for round_ in self.rs.search_rounds or []:
            if round_.citations_expanded:
                events.append(
                    self._emit(
                        EventType.CITATION_EXPANDED,
                        {
                            "round": round_.round_number,
                            "edges_added": round_.citations_expanded,
                        },
                    )
                )

        if self.rs.answer is not None:
            answer_text = self.rs.answer.answer or self.rs.answer.raw_answer or ""
            cited = list(self.rs.answer.papers_cited or [])
            events.append(
                self._emit(
                    EventType.ANSWER,
                    {
                        "answer": answer_text,
                        "papers_used": cited,
                        "answerSummary": answer_text,
                    },
                )
            )

        events.append(
            self._emit(EventType.USAGE, _to_server_usage(self.rs.usage).model_dump())
        )

        # Emit ERROR event if the session encountered an error.
        # The engine may set session.error without setting stop_reason=ERROR
        # (e.g. evidence/answer stage catches exceptions internally and falls
        # back to abstracts). We check both signals.
        is_error_stop = (
            self.rs.stop_reason is not None
            and str(self.rs.stop_reason.value).endswith("error")
        )
        if is_error_stop or self.rs.error:
            error_msg = self.rs.error or (
                f"Search failed: {self.rs.stop_reason.value}"
                if self.rs.stop_reason
                else "Unknown error"
            )
            events.append(
                self._emit(
                    EventType.ERROR,
                    {
                        "error": error_msg,
                        "stop_reason": str(self.rs.stop_reason.value)
                        if self.rs.stop_reason
                        else None,
                    },
                )
            )

        # Count papers by relevance tier (same formula as in ResearchSession.papers)
        papers = (self.rs.all_papers or {}).values()
        relevant_count = sum(
            1 for p in papers
            if getattr(p, "relevance_tier", None) in ("high", "partial")
        )
        server_usage = _to_server_usage(self.rs.usage)
        events.append(
            self._emit(
                EventType.DONE,
                {
                    "stop_reason": str(self.rs.stop_reason.value)
                    if self.rs.stop_reason
                    else None,
                    "rounds": int(getattr(self.rs.usage, "search_rounds", 0)),
                    "papers_count": len(self.rs.all_papers or {}),
                    "relevant_papers": relevant_count,
                    "total_tokens": server_usage.total_tokens,
                    "prompt_tokens": server_usage.prompt_tokens,
                    "completion_tokens": server_usage.completion_tokens,
                    "total_cost": server_usage.total_cost,
                    "llm_calls": server_usage.llm_calls,
                    "search_calls": server_usage.search_calls,
                },
            )
        )
        return events