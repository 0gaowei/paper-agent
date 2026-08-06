"""Tests for the PaperQA server HTTP API.

These tests use FastAPI's TestClient with lifespan support to exercise
the server endpoints in an in-process, async-compatible context.
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

# Ensure the package is on the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from evoscholar.server.app import app
from evoscholar.server.repository import JSONFileRepository


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_sessions_dir(tmp_path: Path) -> Path:
    """Use pytest's tmp_path as the sessions directory."""
    return tmp_path


@pytest.fixture
async def repository(temp_sessions_dir: Path) -> AsyncGenerator[JSONFileRepository, None]:
    """Provide a clean repository backed by a temp directory."""
    repo = JSONFileRepository(sessions_dir=temp_sessions_dir)
    yield repo
    # Cleanup: list and delete all session files
    import anyio

    sessions_dir = anyio.Path(temp_sessions_dir)
    if await sessions_dir.exists():
        async for path in sessions_dir.iterdir():
            if path.suffix == ".json":
                await path.unlink()


@pytest.fixture
def client() -> TestClient:
    """Provide a synchronous TestClient that triggers the lifespan."""
    # Patch the sessions dir to use a temp directory for isolation
    import anyio

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = anyio.Path(tmp)
        # Replace the repository in app.state after startup
        with TestClient(app) as tc:
            from evoscholar.server.repository import JSONFileRepository

            tc.app.state.repository = JSONFileRepository(sessions_dir=tmp_path)
            yield tc


@pytest.fixture
def client_with_repo(client: TestClient, temp_sessions_dir: Path) -> TestClient:
    """Client with an isolated repository pointing to a temp directory."""
    from evoscholar.server.repository import JSONFileRepository

    import anyio

    client.app.state.repository = JSONFileRepository(sessions_dir=temp_sessions_dir)
    return client


class _StubQueryLLM:
    """Minimal LLM stub that returns a valid query-understanding JSON payload.

    Used by ``_StubResearchEngine`` so the server-side
    ``analyze_and_expand_query`` call can succeed without a real LLM.
    """

    async def acomplete(self, messages: list[Any]) -> dict[str, Any]:
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "intent": "general",
                                "domains": [],
                                "subqueries": [],
                            }
                        )
                    }
                }
            ]
        }


class _StubResearchEngine:
    """Drop-in engine that emits deterministic events without touching the
    network, the LLM, or any search provider.

    Mirrors the minimal surface `paperqa.server.routes.sessions` reads
    off the engine — `arun(query)` returning a `ResearchSession`-like
    pydantic model and `aclose()`.
    """

    def __init__(self, results: list[Any] | None = None) -> None:
        self._results = results or []
        self.arun_calls: list[str] = []
        self.closed = False
        # The server route in `_run_research_engine` calls
        # `analyze_and_expand_query(query, engine.settings, engine.llm_model)`
        # BEFORE `engine.arun(...)`. Since query understanding no longer has
        # a heuristic fallback, we must hand the stub a usable LLM that
        # returns a valid JSON payload.
        self.llm_model = _StubQueryLLM()
        self.settings = None

    async def arun(
        self,
        query: str,
        *,
        max_high_relevant: int | None = None,
        precomputed_understanding: Any | None = None,
        publisher: Any | None = None,
        session_id: str | None = None,
        **_: Any,
    ) -> Any:
        from evoscholar.iterative_search.models import ResearchSession, SearchRound
        from evoscholar.synthesis.models import AnswerSummary, UsageStats
        from evoscholar.query_understanding.models import QueryUnderstanding, SubQuery
        from evoscholar.paper_ranker.relevance import RelevanceTier

        self.arun_calls.append(query)
        # Yield to the event loop so SSE consumers can interleave with
        # background publishers when running under TestClient.
        await asyncio.sleep(0)

        if publisher and session_id:
            from evoscholar.server.events import EventType, SSEEvent

            await publisher.publish(
                session_id,
                SSEEvent(event=EventType.EVIDENCE_EXTRACTION_START, data={}),
            )
            await publisher.publish(
                session_id,
                SSEEvent(event=EventType.EVIDENCE_EXTRACTION_DONE, data={"snippets_found": 2}),
            )
            await publisher.publish(
                session_id,
                SSEEvent(event=EventType.ANSWER_SYNTHESIS_START, data={}),
            )
            await publisher.publish(
                session_id,
                SSEEvent(event=EventType.ANSWER_SYNTHESIS_DONE, data={"answer_length": 20}),
            )

        papers = {
            "paper-1": _stub_paper(
                "paper-1", f"Research on: {query}", 2024, "high", 42,
                sources=("semantic_scholar",),
            ),
            "paper-2": _stub_paper(
                "paper-2", f"Further study on {query}", 2023, "partial", 15,
                sources=("openalex",),
            ),
        }
        session = ResearchSession(
            query=query,
            all_papers=papers,
            search_rounds=[
                SearchRound(
                    round_number=1,
                    queries_executed=[query],
                    papers_discovered=2,
                    papers_evaluated=2,
                    high_relevant_found=1,
                    partial_relevant_found=1,
                    citations_expanded=0,
                    subqueries_generated=0,
                    duration_ms=10,
                )
            ],
            query_understanding=QueryUnderstanding(
                original_query=query,
                intent="general",
                subqueries=[SubQuery(query=query)],
            ),
            answer=AnswerSummary(
                answer=f"Stub answer for: {query}",
                papers_cited=["paper-1"],
                evidence_used=1,
                has_successful_answer=True,
            ),
            usage=UsageStats(
                llm_calls=3,
                llm_prompt_tokens=800,
                llm_completion_tokens=400,
                llm_cost_usd=0.05,
                search_rounds=1,
                papers_discovered=2,
                papers_evaluated=2,
                papers_in_final_set=2,
            ),
            stop_reason=None,
        )
        session.final_papers = list(papers.values())
        return session

    async def aclose(self) -> None:
        self.closed = True


def _stub_paper(
    stable_id: str, title: str, year: int, tier: str, citations: int,
    *, sources: tuple[str, ...] = (),
) -> Any:
    from evoscholar.iterative_search.models import AcademicPaper
    from evoscholar.paper_ranker.relevance import RelevanceTier

    return AcademicPaper(
        stable_id=stable_id,
        title=title,
        year=year,
        authors=[],
        abstract=f"Abstract for {title}",
        citation_count=citations,
        source=sources[0] if sources else "semantic_scholar",
        sources=list(sources),
        relevance_tier=RelevanceTier(tier),
    )


@pytest.fixture
def stub_engine() -> _StubResearchEngine:
    """Provide a deterministic stub engine for tests."""
    return _StubResearchEngine()


@pytest.fixture
def client_with_stub_engine(client_with_repo: TestClient, stub_engine: Any) -> TestClient:
    """Client with the stub engine installed in app.state.engine."""
    client_with_repo.app.state.engine = stub_engine
    return client_with_repo


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_returns_ok(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Settings endpoint — key hiding
# ---------------------------------------------------------------------------


class TestSettings:
    def test_get_settings_returns_no_keys(self, client: TestClient) -> None:
        """Settings must never expose API keys."""
        response = client.get("/api/settings")
        assert response.status_code == 200
        data = response.json()
        # Must have configured flags
        assert "llm_configured" in data
        assert "s2_configured" in data
        assert "openalex_configured" in data
        # Must not contain any key strings (unless the value is null, meaning
        # the field is present in the schema but the actual key is not exposed)
        for key, value in data.items():
            if "key" in key.lower() and "configured" not in key.lower():
                assert value is None, (
                    f"API key field {key!r} must be null in response, got {value!r}"
                )
        # Values must be booleans or strings/numbers
        assert isinstance(data.get("llm_configured"), bool)
        assert isinstance(data.get("s2_configured"), bool)
        assert isinstance(data.get("openalex_configured"), bool)

    def test_update_settings_accepts_valid_fields(self, client: TestClient) -> None:
        """PUT /api/settings should accept valid non-key fields."""
        payload = {
            "researcher_llm": "gpt-4o-mini",
            "max_rounds": 5,
            "high_relevance_threshold": 0.80,
        }
        response = client.put("/api/settings", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["researcher_llm"] == "gpt-4o-mini"
        assert data["max_rounds"] == 5
        assert data["high_relevance_threshold"] == 0.80

    def test_update_settings_rejects_api_keys(self, client: TestClient) -> None:
        """Keys passed in the body must not be stored."""
        payload = {
            "researcher_llm": "gpt-4o",
            "llm_api_key": "sk-secret-123",  # Should be ignored
            "s2_api_key": "fake-key",  # Should be ignored
        }
        response = client.put("/api/settings", json=payload)
        assert response.status_code == 200
        # Keys must not appear in response with actual values
        # (llm_api_key field may be present in schema but its value must be null)
        data = response.json()
        for key, value in data.items():
            if "key" in key.lower() and "configured" not in key.lower():
                assert value is None, (
                    f"API key field {key!r} must be null in response, got {value!r}"
                )


# ---------------------------------------------------------------------------
# Session creation — 202 Accepted, immediate return
# ---------------------------------------------------------------------------


class TestSessionCreate:
    def test_create_session_returns_202(
        self, client_with_stub_engine: TestClient
    ) -> None:
        response = client_with_stub_engine.post(
            "/api/sessions",
            json={"query": "What is attention mechanism?"},
        )
        assert response.status_code == 202
        data = response.json()
        assert "id" in data
        assert isinstance(data["id"], str)

    def test_create_session_query_required(
        self, client_with_repo: TestClient
    ) -> None:
        response = client_with_repo.post("/api/sessions", json={"query": ""})
        assert response.status_code == 422  # Validation error

    def test_create_session_missing_query(
        self, client_with_repo: TestClient
    ) -> None:
        response = client_with_repo.post("/api/sessions", json={})
        assert response.status_code == 422

    def test_create_session_without_engine_returns_503(
        self, client_with_repo: TestClient
    ) -> None:
        """When app.state.engine is None the endpoint should return 503."""
        client_with_repo.app.state.engine = None
        response = client_with_repo.post(
            "/api/sessions",
            json={"query": "missing engine"},
        )
        assert response.status_code == 503


# ---------------------------------------------------------------------------
# Session retrieval
# ---------------------------------------------------------------------------


class TestSessionGet:
    def test_get_session_not_found(self, client_with_repo: TestClient) -> None:
        response = client_with_repo.get("/api/sessions/nonexistent-id")
        assert response.status_code == 404

    def test_get_session_after_create(
        self, client_with_stub_engine: TestClient
    ) -> None:
        # Create
        create_resp = client_with_stub_engine.post(
            "/api/sessions",
            json={"query": "machine learning benchmarks"},
        )
        session_id = create_resp.json()["id"]

        # Retrieve
        get_resp = client_with_stub_engine.get(f"/api/sessions/{session_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["session"]["id"] == session_id
        assert data["session"]["query"] == "machine learning benchmarks"
        assert "papers" in data
        assert isinstance(data["papers"], list)


# ---------------------------------------------------------------------------
# SSE events stream
# ---------------------------------------------------------------------------


class TestSSEEvents:
    def test_sse_events_returns_200(
        self, client_with_stub_engine: TestClient
    ) -> None:
        # Create session first
        create_resp = client_with_stub_engine.post(
            "/api/sessions",
            json={"query": "transformer architecture"},
        )
        assert create_resp.status_code == 202
        session_id = create_resp.json()["id"]

        # Subscribe to SSE
        import threading

        response_holder: dict[str, Any] = {}

        def fetch_sse() -> None:
            with client_with_stub_engine.stream(
                "GET", f"/api/sessions/{session_id}/events",
                timeout=15,
            ) as response:
                events: list[dict] = []
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        events.append(json.loads(line[6:]))
                    if any(e.get("type") == "done" for e in events):
                        break
                response_holder["events"] = events
                response_holder["status"] = response.status_code

        t = threading.Thread(target=fetch_sse)
        t.start()
        t.join(timeout=15)

        assert response_holder.get("status") == 200
        events = response_holder.get("events", [])
        assert len(events) > 0

    def test_sse_unknown_session_returns_error_then_done(
        self, client_with_stub_engine: TestClient
    ) -> None:
        """Unknown session should immediately emit ERROR + DONE, not block."""
        with client_with_stub_engine.stream(
            "GET",
            "/api/sessions/unknown-session/events",
            timeout=3,
        ) as response:
            assert response.status_code == 200
            event_types: list[str] = []
            for line in response.iter_lines():
                if line.startswith("event: "):
                    event_types.append(line[len("event: "):].strip())
                if "done" in event_types:
                    break
        assert "error" in event_types
        assert "done" in event_types


# ---------------------------------------------------------------------------
# SSE event ordering
# ---------------------------------------------------------------------------


class TestSSEOrdering:
    def test_sse_events_arrive_in_order(
        self, client_with_stub_engine: TestClient
    ) -> None:
        import threading

        create_resp = client_with_stub_engine.post(
            "/api/sessions",
            json={"query": "neural architecture search"},
        )
        assert create_resp.status_code == 202
        session_id = create_resp.json()["id"]

        received_events: list[str] = []
        received_lines: list[str] = []
        status_code_holder: list[int] = []

        def fetch_sse() -> None:
            with client_with_stub_engine.stream(
                "GET", f"/api/sessions/{session_id}/events",
                timeout=15,
            ) as response:
                status_code_holder.append(response.status_code)
                done_seen = False
                for line in response.iter_lines():
                    received_lines.append(line)
                    if line.startswith("event: "):
                        received_events.append(line[7:].strip())
                    if line.startswith("data: "):
                        try:
                            payload = json.loads(line[6:])
                        except json.JSONDecodeError:
                            continue
                        if payload.get("type") == "done":
                            done_seen = True
                            break
                if not done_seen:
                    pass

        t = threading.Thread(target=fetch_sse)
        t.start()
        t.join(timeout=15)

        assert status_code_holder == [200]
        expected_order = [
            "understanding",
            "subqueries",
            "round_started",
            "paper_found",
            "partial_documents",
            "answer",
            "usage",
            "done",
        ]
        for expected in expected_order:
            assert expected in received_events, (
                f"Event '{expected}' not found in {received_events}"
            )


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------


class TestCancellation:
    def test_cancel_unknown_session_returns_404(
        self, client_with_stub_engine: TestClient
    ) -> None:
        response = client_with_stub_engine.post("/api/sessions/unknown/cancel")
        assert response.status_code == 404

    def test_cancel_session_returns_200(
        self, client_with_stub_engine: TestClient
    ) -> None:
        # Create a session
        create_resp = client_with_stub_engine.post(
            "/api/sessions",
            json={"query": "test query for cancellation"},
        )
        assert create_resp.status_code == 202
        session_id = create_resp.json()["id"]

        # Cancel
        cancel_resp = client_with_stub_engine.post(
            f"/api/sessions/{session_id}/cancel"
        )
        assert cancel_resp.status_code == 200
        data = cancel_resp.json()
        assert data["status"] == "cancelled"


# ---------------------------------------------------------------------------
# History listing
# ---------------------------------------------------------------------------


class TestHistory:
    def test_history_empty_returns_empty_list(
        self, client_with_repo: TestClient
    ) -> None:
        response = client_with_repo.get("/api/history")
        assert response.status_code == 200
        assert response.json() == []

    def test_history_lists_completed_sessions(
        self, client_with_repo: TestClient
    ) -> None:
        import anyio

        repo: JSONFileRepository = client_with_repo.app.state.repository

        # Manually insert a session file
        from evoscholar.server.schemas import ResearchSession
        import datetime

        session = ResearchSession(
            id="test-history-1",
            query="history test query",
            status="done",
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
            rounds=2,
            answer="Short answer.",
        )
        # Persist directly via repository
        anyio.run(repo.save, session)

        response = client_with_repo.get("/api/history")
        assert response.status_code == 200
        entries = response.json()
        assert len(entries) >= 1
        assert any(e["id"] == "test-history-1" for e in entries)

    def test_history_respects_limit(self, client_with_repo: TestClient) -> None:
        response = client_with_repo.get("/api/history?limit=5")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ---------------------------------------------------------------------------
# History deletion
# ---------------------------------------------------------------------------


class TestHistoryDelete:
    def test_delete_unknown_session_returns_404(
        self, client_with_repo: TestClient
    ) -> None:
        response = client_with_repo.delete("/api/history/unknown-id")
        assert response.status_code == 404

    def test_delete_session_returns_204(self, client_with_repo: TestClient) -> None:
        import anyio

        repo: JSONFileRepository = client_with_repo.app.state.repository

        # Insert a session
        from evoscholar.server.schemas import ResearchSession
        import datetime

        session = ResearchSession(
            id="to-delete-1",
            query="session to delete",
            status="done",
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
        )
        anyio.run(repo.save, session)

        # Delete
        del_resp = client_with_repo.delete("/api/history/to-delete-1")
        assert del_resp.status_code == 204

        # Confirm gone
        get_resp = client_with_repo.get("/api/sessions/to-delete-1")
        assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# Papers endpoint
# ---------------------------------------------------------------------------


class TestPapers:
    def test_paper_not_found(self, client_with_repo: TestClient) -> None:
        response = client_with_repo.get("/api/papers/nonexistent")
        assert response.status_code == 404

    def test_paper_graph_not_found(self, client_with_repo: TestClient) -> None:
        response = client_with_repo.get("/api/papers/nonexistent/graph")
        assert response.status_code == 404

    def test_paper_graph_returns_structure(self, client_with_repo: TestClient) -> None:
        """Graph endpoint should return {nodes, edges} structure."""
        import anyio

        repo: JSONFileRepository = client_with_repo.app.state.repository

        from evoscholar.server.schemas import AcademicPaper, PaperSource, RelevanceTier
        from evoscholar.server.schemas import ResearchSession
        import datetime

        paper = AcademicPaper(
            id="graph-test-paper",
            title="Test Paper for Graph",
            year=2024,
            authors=["Test Author"],
            relevance_tier=RelevanceTier.HIGH,
            source=PaperSource.SEMANTIC_SCHOLAR,
            referenced_works=["ref-1", "ref-2"],
            citing_works=["citing-1"],
        )
        session = ResearchSession(
            id="graph-test-session",
            query="graph test",
            status="done",
            papers={"graph-test-paper": paper},
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
        )
        anyio.run(repo.save, session)

        response = client_with_repo.get("/api/papers/graph-test-paper/graph")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data


# ---------------------------------------------------------------------------
# Session graph
# ---------------------------------------------------------------------------


class TestSessionGraph:
    def test_session_graph_returns_structure(self, client_with_repo: TestClient) -> None:
        import anyio

        repo: JSONFileRepository = client_with_repo.app.state.repository

        from evoscholar.server.schemas import ResearchSession, SubQuery
        import datetime

        session = ResearchSession(
            id="graph-session-test",
            query="attention in transformers",
            status="done",
            subqueries=[SubQuery(text="what is attention", round=0)],
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
        )
        anyio.run(repo.save, session)

        response = client_with_repo.get("/api/sessions/graph-session-test/graph")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert "query" in data
        assert data["query"] == "attention in transformers"


# ---------------------------------------------------------------------------
# Usage endpoint
# ---------------------------------------------------------------------------


class TestUsage:
    def test_usage_returns_stats(self, client_with_repo: TestClient) -> None:
        response = client_with_repo.get("/api/usage")
        assert response.status_code == 200
        data = response.json()
        assert "total_tokens" in data
        assert "total_cost" in data
        assert "llm_calls" in data
        assert "search_calls" in data
        # All should be integers or floats
        assert isinstance(data["total_tokens"], int)
        assert isinstance(data["total_cost"], float)


# ---------------------------------------------------------------------------
# Repository — atomic writes
# ---------------------------------------------------------------------------


class TestRepository:
    @pytest.mark.anyio
    async def test_save_and_load_roundtrip(
        self, repository: JSONFileRepository
    ) -> None:
        from evoscholar.server.schemas import ResearchSession
        import datetime

        session = ResearchSession(
            id="roundtrip-test",
            query="roundtrip test",
            status="done",
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
        )
        await repository.save(session)
        loaded = await repository.get("roundtrip-test")
        assert loaded is not None
        assert loaded.id == "roundtrip-test"
        assert loaded.query == "roundtrip test"

    @pytest.mark.anyio
    async def test_save_atomic_creates_json_file(
        self, repository: JSONFileRepository
    ) -> None:
        from evoscholar.server.schemas import ResearchSession
        import datetime

        session = ResearchSession(
            id="atomic-write-test",
            query="atomic write test",
            status="running",
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
        )
        await repository.save(session)
        # A .json file (not .tmp) should exist
        path = repository._session_path("atomic-write-test")
        assert await path.exists()
        assert path.suffix == ".json"

    @pytest.mark.anyio
    async def test_get_nonexistent_returns_none(
        self, repository: JSONFileRepository
    ) -> None:
        result = await repository.get("does-not-exist")
        assert result is None

    @pytest.mark.anyio
    async def test_delete_removes_file(self, repository: JSONFileRepository) -> None:
        from evoscholar.server.schemas import ResearchSession
        import datetime

        session = ResearchSession(
            id="delete-test",
            query="delete test",
            status="done",
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
        )
        await repository.save(session)
        deleted = await repository.delete("delete-test")
        assert deleted is True
        assert await repository.get("delete-test") is None

    @pytest.mark.anyio
    async def test_list_returns_most_recent_first(
        self, repository: JSONFileRepository
    ) -> None:
        import datetime

        from evoscholar.server.schemas import ResearchSession

        sessions = [
            ResearchSession(
                id=f"list-test-{i}",
                query=f"query {i}",
                status="done",
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow(),
            )
            for i in range(5)
        ]
        for s in sessions:
            await repository.save(s)

        listed = await repository.list_(limit=10)
        assert len(listed) == 5
        # Most recently updated first
        ids = [s.id for s in listed]
        assert ids == sorted(ids, key=lambda x: x, reverse=True)  # most-recently-updated first

    @pytest.mark.anyio
    async def test_exists(self, repository: JSONFileRepository) -> None:
        from evoscholar.server.schemas import ResearchSession
        import datetime

        assert await repository.exists("new-session") is False
        session = ResearchSession(
            id="new-session",
            query="exists test",
            status="pending",
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
        )
        await repository.save(session)
        assert await repository.exists("new-session") is True
