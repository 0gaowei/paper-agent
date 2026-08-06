"""Tests for the ResearchEngine and supporting research modules."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import pytest
from lmi import LLMResult

from evoscholar.iterative_search.engine import ResearchEngine
from evoscholar.iterative_search.models import (
    AcademicPaper,
    SearchResult,
    StopReason,
)
from evoscholar.query_understanding.models import Domain, QueryIntent
from evoscholar.paper_ranker.relevance import RelevanceTier
from evoscholar.query_understanding.analyze import analyze_and_expand_query
from evoscholar.paper_ranker.ranker import (
    _lexical_relevance,
    score_papers,
)
from evoscholar.paper_ranker.mmr import rank_with_mmr
from evoscholar.literature_qa.settings import Settings


class FakeProvider:
    """Static provider that returns a configurable set of papers."""

    def __init__(
        self,
        papers: list[AcademicPaper] | None = None,
        *,
        references: list[str] | None = None,
        details: dict[str, AcademicPaper] | None = None,
        fail_search: bool = False,
    ) -> None:
        self.name = "fake"
        self._papers = list(papers or [])
        self._references = list(references or [])
        self._details = dict(details or {})
        self._fail_search = fail_search
        self.search_calls: list[str] = []
        self.reference_calls: list[str] = []
        self.detail_calls: list[str] = []

    async def search(self, query: str, top_k: int) -> SearchResult:
        self.search_calls.append(query)
        if self._fail_search:
            raise RuntimeError("fake provider search failed")
        return SearchResult(
            papers=self._papers[:top_k],
            provider=self.name,
            query=query,
            success=True,
            total_results=len(self._papers),
        )

    async def get_doc_details(self, doi_or_id: str) -> AcademicPaper | None:
        self.detail_calls.append(doi_or_id)
        return self._details.get(doi_or_id)

    async def get_references(self, paper_id: str) -> list[str]:
        self.reference_calls.append(paper_id)
        return list(self._references)


class FakeLLM:
    """Minimal LLM that returns a preconfigured JSON payload or raises."""

    def __init__(
        self,
        query_payload: dict[str, Any] | None = None,
        answer_payload: str | None = None,
        *,
        raise_on_query: bool = False,
    ) -> None:
        self.query_payload = query_payload or {}
        self.answer_payload = answer_payload or "Fake answer."
        self._raise_on_query = raise_on_query
        self.acomplete_calls = 0
        self.call_single_calls = 0

    async def acomplete(self, messages: list[Any]) -> dict[str, Any]:
        self.acomplete_calls += 1
        if self._raise_on_query:
            raise RuntimeError("LLM provider died")
        content = json_dumps(self.query_payload)
        return {"choices": [{"message": {"content": content}}]}

    async def call_single(self, messages: Any, **_: Any) -> LLMResult:
        self.call_single_calls += 1
        if self._raise_on_query:
            raise RuntimeError("LLM provider died")
        # First call drives query understanding (returns JSON), the rest answer
        # synthesis. The engine wraps llm_model in _TrackedLLMAdapter which only
        # exposes call_single, so the same FakeLLM must serve both stages here.
        if self.call_single_calls == 1:
            return LLMResult(
                model="fake",
                text=json_dumps(self.query_payload),
                prompt_count=10,
                completion_count=20,
                cost=0.01,
            )
        return LLMResult(
            model="fake",
            text=self.answer_payload,
            prompt_count=10,
            completion_count=20,
            cost=0.01,
        )


def json_dumps(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload)


def _make_paper(
    stable_id: str,
    title: str,
    abstract: str,
    *,
    year: int = 2024,
    citation_count: int = 50,
    fields: list[str] | None = None,
) -> AcademicPaper:
    return AcademicPaper(
        stable_id=stable_id,
        title=title,
        abstract=abstract,
        authors=["Author"],
        year=year,
        citation_count=citation_count,
        fields_of_study=fields or ["Computer Science"],
        source="fake",
        sources=["fake"],
    )


def _build_settings(
    *,
    max_rounds: int = 1,
    max_references_per_node: int = 0,
    max_candidates_per_round: int = 5,
    llm_budget_usd: float = 100.0,
    token_budget: int = 1_000_000,
    api_budget: int = 1_000,
    relevance_partial: float = 0.5,
    relevance_high: float = 0.75,
    max_high_relevant: int = 3,
) -> Settings:
    settings = Settings()
    settings.llm = "gpt-4o"
    settings.embedding = "sparse"
    settings.research.max_rounds = max_rounds
    settings.research.max_candidates_per_round = max_candidates_per_round
    settings.research.max_references_per_node = max_references_per_node
    settings.research.llm_budget_usd = llm_budget_usd
    settings.research.token_budget = token_budget
    settings.research.api_budget = api_budget
    settings.research.partial_threshold = relevance_partial
    settings.research.high_threshold = relevance_high
    settings.answer.evidence_retrieval = False
    settings.answer.evidence_skip_summary = True
    settings.answer.get_evidence_if_no_contexts = False
    return settings


@pytest.mark.asyncio
async def test_query_understanding_parses_llm_json() -> None:
    payload = {
        "intent": "survey",
        "domains": ["ml"],
        "entities": ["machine learning"],
        "suitable_sources": ["semantic_scholar"],
        "subqueries": [
            {
                "query": "machine learning survey",
                "purpose": "overview",
                "priority": 9,
            }
        ],
        "search_strategy": "survey",
    }
    llm = FakeLLM(query_payload=payload)
    settings = _build_settings()
    understanding = await analyze_and_expand_query(
        "machine learning", settings, llm
    )
    assert understanding.intent == QueryIntent.SURVEY
    assert understanding.domains == [Domain.ML]
    assert understanding.entities == ["machine learning"]
    assert understanding.subqueries[0].query == "machine learning survey"


@pytest.mark.asyncio
async def test_query_understanding_raises_on_llm_failure() -> None:
    """LLM failure must surface as an exception; no heuristic fallback."""
    llm = FakeLLM(raise_on_query=True)
    settings = _build_settings()
    with pytest.raises(RuntimeError, match="LLM provider died"):
        await analyze_and_expand_query(
            "Compare deep learning versus classical machine learning",
            settings,
            llm,
        )


def test_score_papers_assigns_tiers_and_factors() -> None:
    paper_high = _make_paper(
        "a",
        "Deep learning for NLP",
        "A deep learning survey on transformers and NLP.",
    )
    paper_low = _make_paper(
        "b",
        "Cooking recipe",
        "Boil water and add pasta.",
    )
    settings = _build_settings(relevance_partial=0.2, relevance_high=0.4)
    score_papers([paper_high, paper_low], "deep learning nlp", settings, None)
    assert paper_high.relevance_tier in (RelevanceTier.HIGH, RelevanceTier.PARTIAL)
    assert set(paper_high.ranking_factors) == {
        "relevance",
        "recency",
        "citation",
        "diversity",
        "combined",
    }
    assert 0.0 <= paper_high.ranking_factors["combined"] <= 1.0


def test_score_papers_respects_threshold_boundaries() -> None:
    """A paper with full lexical matches must land at HIGH, otherwise at LOW."""

    paper = _make_paper(
        "match",
        "Quantum computing qubits",
        "Quantum computing qubits and gates.",
    )
    settings = _build_settings(relevance_partial=0.4, relevance_high=0.7)
    score_papers([paper], "quantum computing", settings, None)
    assert paper.relevance_tier == RelevanceTier.HIGH

    empty = _make_paper("unrelated", "Cooking recipe", "Boil water.")
    score_papers([empty], "quantum computing", settings, None)
    assert empty.relevance_tier == RelevanceTier.LOW


def test_score_papers_uses_dense_embedding_when_available() -> None:
    class FakeEmbedding:
        def __init__(self) -> None:
            self.calls: list[list[str]] = []

        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            self.calls.append(list(texts))
            return [
                [1.0, 0.0],
                [1.0, 0.0],
                [0.0, 1.0],
            ]

    papers = [
        _make_paper("a", "Quantum computing", "Quantum computing review."),
        _make_paper("b", "Cooking recipe", "Boil water."),
    ]
    settings = _build_settings()
    embedding = FakeEmbedding()
    score_papers(papers, "quantum computing", settings, embedding)
    assert embedding.calls, "embedding model should have been called"
    assert papers[0].relevance_score == pytest.approx(1.0)
    assert papers[1].relevance_score == pytest.approx(0.0)


def test_score_papers_falls_back_to_lexical_on_embedding_error() -> None:
    """If an embedding model raises, the ranking falls back to lexical scoring."""

    class BrokenEmbedding:
        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            raise RuntimeError("embedding server down")

    papers = [
        _make_paper("a", "Quantum computing", "Quantum computing review."),
    ]
    settings = _build_settings()
    score_papers(papers, "quantum computing", settings, BrokenEmbedding())
    assert papers[0].relevance_score is not None
    assert papers[0].relevance_tier in {
        RelevanceTier.HIGH,
        RelevanceTier.PARTIAL,
    }


def test_rank_with_mmr_selects_diverse_papers() -> None:
    paper_a = _make_paper(
        "a",
        "Quantum computing",
        "Quantum",
        fields=["Physics"],
    )
    paper_b = _make_paper(
        "b",
        "Quantum algorithms",
        "Quantum",
        fields=["Physics"],
    )
    paper_c = _make_paper(
        "c",
        "Cooking recipe",
        "Boil",
        fields=["Chemistry"],
    )
    for paper in (paper_a, paper_b, paper_c):
        paper.ranking_factors = {"combined": 0.9, "relevance": 0.9}
        paper.relevance_score = 0.9
    selected = rank_with_mmr([paper_a, paper_b, paper_c], k=2, lambda_mult=0.5)
    # With identical combined scores, the sorted order picks c first (highest stable_id),
    # then b wins over a because both have equal MMR scores with same fields.
    assert len(selected) == 2
    assert paper_c in selected
    # The MMR picks a paper with a different field than the first selection.
    selected_fields = {next(iter(paper.fields_of_study)) for paper in selected}
    assert len(selected_fields) == 2


def test_rank_with_mmr_returns_empty_when_k_zero() -> None:
    paper = _make_paper("a", "Quantum", "Quantum computing")
    assert rank_with_mmr([paper], k=0) == []


def test_lexical_relevance_is_bounded() -> None:
    paper = _make_paper("a", "Quantum computing", "Quantum computing review.")
    score = _lexical_relevance("quantum computing", paper)
    assert 0.0 <= score <= 1.0


@pytest.mark.asyncio
async def test_research_engine_arun_no_new_papers_stops() -> None:
    provider = FakeProvider(papers=[])
    llm = FakeLLM(
        query_payload={
            "intent": "survey",
            "domains": ["ml"],
            "subqueries": [{"query": "machine learning", "priority": 10}],
        }
    )
    settings = _build_settings(max_rounds=3)
    engine = ResearchEngine(
        settings=settings,
        llm_model=llm,
        embedding_model=None,
        providers=provider,
    )
    session = await engine.arun("machine learning")
    assert session.stop_reason == StopReason.NO_NEW_PAPERS
    assert session.final_papers == []


@pytest.mark.asyncio
async def test_research_engine_arun_populates_usage_with_llm_calls() -> None:
    papers = [
        _make_paper(
            "p1",
            "Deep learning for NLP",
            "Survey of deep learning methods for NLP tasks.",
        )
    ]
    provider = FakeProvider(papers=papers)
    llm = FakeLLM(
        query_payload={
            "intent": "survey",
            "domains": ["ml"],
            "subqueries": [{"query": "deep learning", "priority": 10}],
        },
        answer_payload="answer text",
    )
    settings = _build_settings(max_rounds=1)
    engine = ResearchEngine(
        settings=settings,
        llm_model=llm,
        embedding_model=None,
        providers=provider,
    )
    session = await engine.arun("deep learning")
    assert session.usage.llm_calls >= 1
    assert session.usage.llm_prompt_tokens >= 10
    assert session.usage.llm_cost_usd >= 0.0
    assert "fake" in session.usage.api_calls_by_provider
    assert session.usage.api_calls_by_provider["fake"] >= 1


@pytest.mark.asyncio
async def test_research_engine_budget_exceeded_stops_early() -> None:
    papers = [
        _make_paper("p1", "Deep learning", "Deep learning review."),
    ]
    provider = FakeProvider(papers=papers)
    llm = FakeLLM(
        query_payload={
            "intent": "survey",
            "domains": ["ml"],
            "subqueries": [{"query": "deep learning", "priority": 10}],
        }
    )
    # Set LLM budget to 0 so the very first LLM call trips the budget check.
    settings = _build_settings(max_rounds=3, llm_budget_usd=0.0, token_budget=0)
    engine = ResearchEngine(
        settings=settings,
        llm_model=llm,
        embedding_model=None,
        providers=provider,
    )
    session = await engine.arun("deep learning")
    assert session.stop_reason == StopReason.BUDGET_EXCEEDED


@pytest.mark.asyncio
async def test_research_engine_stops_at_max_high_relevant() -> None:
    papers = [
        _make_paper("p1", "Quantum computing", "Quantum computing review."),
        _make_paper("p2", "Quantum algorithms", "Quantum algorithms review."),
        _make_paper("p3", "Quantum qubits", "Quantum qubits review."),
    ]
    provider = FakeProvider(papers=papers)
    llm = FakeLLM(
        query_payload={
            "intent": "survey",
            "domains": ["ml"],
            "subqueries": [{"query": "quantum computing", "priority": 10}],
        }
    )
    settings = _build_settings(
        max_rounds=3,
        relevance_partial=0.1,
        relevance_high=0.2,
        max_candidates_per_round=10,
    )
    engine = ResearchEngine(
        settings=settings,
        llm_model=llm,
        embedding_model=None,
        providers=provider,
    )
    session = await engine.arun("quantum computing", max_high_relevant=2)
    assert session.stop_reason == StopReason.MAX_HIGH_RELEVANT
    high = [paper for paper in session.final_papers if paper.relevance_tier == RelevanceTier.HIGH]
    assert len(high) >= 2


@pytest.mark.asyncio
async def test_research_engine_provider_failure_does_not_raise() -> None:
    failing = FakeProvider(fail_search=True)
    llm = FakeLLM(
        query_payload={
            "intent": "survey",
            "domains": ["ml"],
            "subqueries": [{"query": "x", "priority": 10}],
        }
    )
    settings = _build_settings(max_rounds=1)
    engine = ResearchEngine(
        settings=settings,
        llm_model=llm,
        embedding_model=None,
        providers=failing,
    )
    session = await engine.arun("x")
    assert session.stop_reason in (
        StopReason.NO_NEW_PAPERS,
        StopReason.QUEUE_EMPTY,
        StopReason.BUDGET_EXCEEDED,
    )


@pytest.mark.asyncio
async def test_research_engine_records_session_attributes() -> None:
    papers = [_make_paper("p1", "Deep learning", "Deep learning review.")]
    provider = FakeProvider(papers=papers)
    llm = FakeLLM(
        query_payload={
            "intent": "survey",
            "domains": ["ml"],
            "subqueries": [{"query": "deep learning", "priority": 10}],
        }
    )
    settings = _build_settings(max_rounds=2)
    engine = ResearchEngine(
        settings=settings,
        llm_model=llm,
        embedding_model=None,
        providers=provider,
    )
    session = await engine.arun("deep learning")
    assert session.query == "deep learning"
    assert session.query_understanding is not None
    assert session.usage.total_duration_ms is not None
    assert session.completed_at is not None
    assert isinstance(session.created_at, datetime)


@pytest.mark.asyncio
async def test_research_engine_llm_failure_skips_answer_stage() -> None:
    """When the summary LLM fails, the engine still returns a populated session."""

    papers = [_make_paper("p1", "Deep learning", "Deep learning review.")]

    class FailingAnswerLLM:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def acomplete(self, messages: list[Any]) -> dict[str, Any]:
            self.calls.append("query")
            content = json_dumps(
                {
                    "intent": "survey",
                    "domains": ["ml"],
                    "subqueries": [
                        {"query": "deep learning", "priority": 10}
                    ],
                }
            )
            return {"choices": [{"message": {"content": content}}]}

        async def call_single(self, messages: Any, **_: Any) -> LLMResult:
            self.calls.append("answer")
            # The engine wraps the LLM in _TrackedLLMAdapter which only exposes
            # call_single, so the first call here actually serves query
            # understanding (must succeed with JSON); only subsequent calls
            # drive answer synthesis and should fail.
            if self.calls.count("answer") == 1:
                return LLMResult(
                    model="fake",
                    text=json_dumps(
                        {
                            "intent": "survey",
                            "domains": ["ml"],
                            "subqueries": [
                                {"query": "deep learning", "priority": 10}
                            ],
                        }
                    ),
                    prompt_count=10,
                    completion_count=20,
                    cost=0.01,
                )
            raise RuntimeError("answer failed")

    provider = FakeProvider(papers=papers)
    llm = FailingAnswerLLM()
    settings = _build_settings(max_rounds=1)
    engine = ResearchEngine(
        settings=settings,
        llm_model=llm,
        embedding_model=None,
        providers=provider,
    )
    session = await engine.arun("deep learning")
    assert session.answer is not None
    assert session.answer.has_successful_answer is False
    assert session.evidence, "fallback should still populate evidence from abstracts"


@pytest.mark.asyncio
async def test_research_engine_expands_references_when_configured() -> None:
    seed = _make_paper("seed", "Quantum computing", "Quantum computing review.")
    reference_paper = _make_paper(
        "doi-ref", "Quantum bits", "Quantum bits review."
    )
    provider = FakeProvider(
        papers=[seed],
        references=["doi-ref"],
        details={"doi-ref": reference_paper},
    )
    llm = FakeLLM(
        query_payload={
            "intent": "survey",
            "domains": ["ml"],
            "subqueries": [{"query": "quantum", "priority": 10}],
        }
    )
    settings = _build_settings(
        max_rounds=1,
        max_references_per_node=2,
        relevance_partial=0.1,
        relevance_high=0.2,
    )
    engine = ResearchEngine(
        settings=settings,
        llm_model=llm,
        embedding_model=None,
        providers=provider,
    )
    session = await engine.arun("quantum computing", max_high_relevant=2)
    assert provider.reference_calls == ["seed"]
    assert {paper.stable_id for paper in session.all_papers.values()} >= {
        "seed",
        "doi-ref",
    }
    assert any(
        edge.target_id == "doi-ref" for edge in session.citation_graph
    )


@pytest.mark.asyncio
async def test_research_engine_emits_search_rounds() -> None:
    papers = [_make_paper("p1", "Deep learning", "Deep learning review.")]
    provider = FakeProvider(papers=papers)
    llm = FakeLLM(
        query_payload={
            "intent": "survey",
            "domains": ["ml"],
            "subqueries": [{"query": "deep learning", "priority": 10}],
        }
    )
    settings = _build_settings(max_rounds=2)
    engine = ResearchEngine(
        settings=settings,
        llm_model=llm,
        embedding_model=None,
        providers=provider,
    )
    session = await engine.arun("deep learning")
    assert session.search_rounds, "engine should record at least one search round"
    first = session.search_rounds[0]
    assert first.queries_executed == ["deep learning"]
    assert first.duration_ms is not None
    assert first.papers_evaluated >= 1


@pytest.mark.asyncio
async def test_research_engine_cancellation_is_propagated() -> None:
    """Cancelling the engine mid-flight should raise asyncio.CancelledError."""

    class SlowProvider:
        name = "slow"

        async def search(self, query: str, top_k: int) -> SearchResult:
            await asyncio.sleep(1)
            return SearchResult(papers=[], provider=self.name, query=query)

        async def get_doc_details(self, doi_or_id: str) -> AcademicPaper | None:
            return None

        async def get_references(self, paper_id: str) -> list[str]:
            return []

    llm = FakeLLM(
        query_payload={
            "intent": "survey",
            "domains": ["ml"],
            "subqueries": [{"query": "x", "priority": 10}],
        }
    )
    settings = _build_settings(max_rounds=1, max_candidates_per_round=2)
    engine = ResearchEngine(
        settings=settings,
        llm_model=llm,
        embedding_model=None,
        providers=SlowProvider(),
    )
    task = asyncio.create_task(engine.arun("x"))
    await asyncio.sleep(0.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_research_engine_deduplicates_papers_in_search() -> None:
    """Engine aggregates references and exposes the deduplicated paper set."""

    seed = _make_paper("seed", "Quantum computing", "Quantum computing review.")
    referenced = _make_paper("doi-1", "Quantum bits", "Quantum bits review.")

    provider = FakeProvider(
        papers=[seed],
        references=["doi-1"],
        details={"doi-1": referenced},
    )
    llm = FakeLLM(
        query_payload={
            "intent": "survey",
            "domains": ["ml"],
            "subqueries": [{"query": "quantum", "priority": 10}],
        }
    )
    settings = _build_settings(
        max_rounds=1,
        max_references_per_node=5,
        relevance_partial=0.1,
        relevance_high=0.2,
    )
    engine = ResearchEngine(
        settings=settings,
        llm_model=llm,
        embedding_model=None,
        providers=provider,
    )
    session = await engine.arun("quantum computing", max_high_relevant=2)
    assert "seed" in session.all_papers
    assert "doi-1" in session.all_papers
    # The reference appears as a citation edge in the citation graph.
    edges = [
        edge
        for edge in session.citation_graph
        if edge.source_id == "seed" and edge.target_id == "doi-1"
    ]
    assert edges


@pytest.mark.asyncio
async def test_research_engine_closes_internal_http_client() -> None:
    """An engine created without providers should manage an internal http client."""

    llm = FakeLLM(
        query_payload={
            "intent": "survey",
            "domains": ["ml"],
            "subqueries": [{"query": "x", "priority": 10}],
        }
    )
    settings = _build_settings(max_rounds=1)
    engine = ResearchEngine(
        settings=settings,
        llm_model=llm,
        embedding_model=None,
        providers=None,  # type: ignore[arg-type]
    )
    assert engine._http_client is not None
    assert engine._owns_http_client is True
    await engine.aclose()
    assert engine._owns_http_client is False


@pytest.mark.asyncio
async def test_research_engine_with_explicit_provider_skips_http_creation() -> None:
    """Passing a single provider should not create an internal http client."""

    llm = FakeLLM(
        query_payload={
            "intent": "survey",
            "domains": ["ml"],
            "subqueries": [{"query": "x", "priority": 10}],
        }
    )
    settings = _build_settings(max_rounds=1)
    provider = FakeProvider(papers=[])
    engine = ResearchEngine(
        settings=settings,
        llm_model=llm,
        embedding_model=None,
        providers=provider,
    )
    assert engine._http_client is None
    assert engine._owns_http_client is False
