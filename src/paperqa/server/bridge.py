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

from paperqa.server.events import EventType
from paperqa.server.schemas import (
    AcademicPaper as ServerPaper,
)
from paperqa.server.schemas import (
    EvidenceSnippet as ServerEvidence,
)
from paperqa.server.schemas import (
    PaperSource,
    QueryUnderstanding,
    RelevanceTier,
    ResearchSession as ServerSession,
)
from paperqa.server.schemas import (
    SubQuery as ServerSubQuery,
)
from paperqa.server.schemas import (
    UsageStats as ServerUsage,
)

if TYPE_CHECKING:
    from paperqa.research.models import ResearchSession as ResearchSessionModel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Source enums -> server enums
# ---------------------------------------------------------------------------

_SOURCE_TO_SERVER: dict[str, PaperSource] = {
    "semantic_scholar": PaperSource.SEMANTIC_SCHOLAR,
    "openalex": PaperSource.OPENTALEX,
    "crossref": PaperSource.CROSSREF,
    "manual": PaperSource.MANUAL,
}

_TIER_TO_SERVER: dict[str, RelevanceTier] = {
    "high": RelevanceTier.HIGH,
    "partial": RelevanceTier.PARTIAL,
    "low": RelevanceTier.IRRELEVANT,
}


def _to_server_paper(paper: Any) -> ServerPaper:
    """Map a research `AcademicPaper` to the server `AcademicPaper`."""
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
        abstract=paper.abstract,
        url=paper.pdf_url or paper.url,
        source=source,
        referenced_works=list(paper.citation_ids or []),
        citing_works=list(paper.cited_by_ids or []),
    )


def _to_server_subquery(sub: Any) -> ServerSubQuery:
    """Map a research `SubQuery` to the server `SubQuery`."""
    purpose = getattr(sub, "purpose", "") or ""
    return ServerSubQuery(
        text=sub.query,
        intent=purpose or "general",
        round=0,
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
        _to_server_subquery(s) for s in (getattr(ru, "subqueries", []) or [])
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
    papers = {
        p.stable_id: _to_server_paper(p)
        for p in (getattr(rs, "all_papers", {}) or {}).values()
    }
    evidence = _to_server_evidence(getattr(rs, "evidence", []) or [])
    answer_text = ""
    if rs.answer is not None:
        answer_text = rs.answer.answer or rs.answer.raw_answer or ""
    subqueries: list[ServerSubQuery] = []
    if rs.query_understanding is not None:
        subqueries = [
            _to_server_subquery(s)
            for s in (rs.query_understanding.subqueries or [])
        ]
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
            _to_server_subquery(s).model_dump(exclude_none=True)
            for s in (ru.subqueries if ru else [])
        ] or [{"text": self.rs.query, "intent": "general", "round": 0}]
        events.append(self._emit(EventType.SUBQUERIES, {"subqueries": sub_payload}))

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
                        _to_server_paper(paper).to_event_dict(),
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

        events.append(
            self._emit(
                EventType.DONE,
                {
                    "stop_reason": str(self.rs.stop_reason.value)
                    if self.rs.stop_reason
                    else None,
                    "rounds": int(getattr(self.rs.usage, "search_rounds", 0)),
                    "papers_count": len(self.rs.all_papers or {}),
                },
            )
        )
        return events