"""Tests for the aggregated academic search client and providers."""

from __future__ import annotations

from collections import Counter

import pytest

from paperqa.clients.academic_search import (
    AcademicSearchClient,
    AcademicSearchProvider,
)
from paperqa.research.models import AcademicPaper, SearchResult


class FakeProvider:
    """In-memory AcademicSearchProvider used by tests."""

    def __init__(
        self,
        name: str,
        papers: list[AcademicPaper] | None = None,
        *,
        references: list[str] | None = None,
        detail: AcademicPaper | None = None,
        fail_on: tuple[str, ...] | None = None,
    ) -> None:
        self.name = name
        self._papers = list(papers or [])
        self._references = list(references or [])
        self._detail = detail
        self._fail_on = set(fail_on or ())
        self.calls: list[tuple[str, str]] = []

    def _should_fail(self, op: str) -> bool:
        return op in self._fail_on

    async def search(self, query: str, top_k: int) -> SearchResult:
        self.calls.append(("search", query))
        if self._should_fail("search"):
            raise RuntimeError(f"{self.name} search failed")
        return SearchResult(
            papers=self._papers[:top_k],
            provider=self.name,
            query=query,
            success=True,
            total_results=len(self._papers),
        )

    async def get_doc_details(self, doi_or_id: str) -> AcademicPaper | None:
        self.calls.append(("get_doc_details", doi_or_id))
        if self._should_fail("get_doc_details"):
            raise RuntimeError(f"{self.name} detail failed")
        return self._detail

    async def get_references(self, paper_id: str) -> list[str]:
        self.calls.append(("get_references", paper_id))
        if self._should_fail("get_references"):
            raise RuntimeError(f"{self.name} references failed")
        return list(self._references)


def _paper(stable_id: str, abstract: str = "Abstract") -> AcademicPaper:
    return AcademicPaper(
        stable_id=stable_id,
        title=f"Title {stable_id}",
        abstract=abstract,
        authors=["Author"],
        year=2024,
        citation_count=10,
        source="fake",
        sources=["fake"],
        fields_of_study=["Computer Science"],
    )


def test_academic_search_provider_protocol_is_satisfied() -> None:
    """A class implementing the protocol surface should be accepted by the client."""

    provider: AcademicSearchProvider = FakeProvider("fake", papers=[_paper("doi1")])
    assert isinstance(provider, AcademicSearchProvider)


@pytest.mark.asyncio
async def test_academic_search_client_aggregates_distinct_providers() -> None:
    first = FakeProvider("alpha", papers=[_paper("doi-a")])
    second = FakeProvider("beta", papers=[_paper("doi-b")])
    client = AcademicSearchClient.__new__(AcademicSearchClient)
    client.http_client = None  # type: ignore[attr-defined]
    client.providers = [first, second]
    client.retry = None
    client.call_counts = Counter()
    client.last_errors = []

    result = await client.search("x", 5)
    assert result.success
    assert {paper.stable_id for paper in result.papers} == {"doi-a", "doi-b"}
    assert client.call_counts == {"alpha": 1, "beta": 1}
    assert first.calls and second.calls


@pytest.mark.asyncio
async def test_academic_search_client_records_failures_without_raising() -> None:
    failing = FakeProvider(
        "alpha", papers=[_paper("doi-a")], fail_on=("search",)
    )
    healthy = FakeProvider("beta", papers=[_paper("doi-b")])
    client = AcademicSearchClient.__new__(AcademicSearchClient)
    client.http_client = None  # type: ignore[attr-defined]
    client.providers = [failing, healthy]
    client.retry = None
    client.call_counts = Counter()
    client.last_errors = []

    result = await client.search("x", 5)
    assert result.success
    assert "alpha" in (result.error_message or "")
    assert {paper.stable_id for paper in result.papers} == {"doi-b"}


@pytest.mark.asyncio
async def test_academic_search_client_get_doc_details_returns_first_success() -> None:
    failing = FakeProvider("alpha", fail_on=("get_doc_details",))
    target = _paper("doi-z")
    healthy = FakeProvider("beta", detail=target)
    client = AcademicSearchClient.__new__(AcademicSearchClient)
    client.http_client = None  # type: ignore[attr-defined]
    client.providers = [failing, healthy]
    client.retry = None
    client.call_counts = Counter()
    client.last_errors = []

    resolved = await client.get_doc_details("doi-z")
    assert resolved is not None
    assert resolved.stable_id == "doi-z"


@pytest.mark.asyncio
async def test_academic_search_client_get_references_dedupes() -> None:
    first = FakeProvider("alpha", references=["doi-1", "doi-2"])
    second = FakeProvider("beta", references=["doi-2", "doi-3"])
    client = AcademicSearchClient.__new__(AcademicSearchClient)
    client.http_client = None  # type: ignore[attr-defined]
    client.providers = [first, second]
    client.retry = None
    client.call_counts = Counter()
    client.last_errors = []

    references = await client.get_references("seed-id")
    assert references == ["doi-1", "doi-2", "doi-3"]


@pytest.mark.asyncio
async def test_academic_search_client_constructor_takes_provider_names() -> None:
    """Construction must accept a provider_names sequence for default providers."""

    # When callers only pass provider_names, the built-in providers are filtered.
    client = AcademicSearchClient(
        http_client=None,  # type: ignore[arg-type]
        provider_names=["semantic_scholar"],
    )
    assert [provider.name for provider in client.providers] == ["semantic_scholar"]


@pytest.mark.asyncio
async def test_academic_search_client_constructor_uses_explicit_providers() -> None:
    """Explicit providers always win over provider_names."""

    alpha = FakeProvider("alpha", papers=[_paper("doi-a")])
    beta = FakeProvider("beta", papers=[_paper("doi-b")])
    client = AcademicSearchClient(
        http_client=None,  # type: ignore[arg-type]
        providers=[alpha],
        provider_names=["beta"],
    )
    assert [provider.name for provider in client.providers] == ["alpha"]


@pytest.mark.asyncio
async def test_academic_search_client_constructs_default_providers() -> None:
    """Default construction wires up the two built-in providers."""

    client = AcademicSearchClient(
        http_client=None,  # type: ignore[arg-type]
    )
    names = [provider.name for provider in client.providers]
    assert set(names) == {"semantic_scholar", "openalex"}


def test_academic_search_client_rejects_empty_providers() -> None:
    with pytest.raises(ValueError, match="At least one"):
        AcademicSearchClient(
            http_client=None,  # type: ignore[arg-type]
            providers=[],
        )


@pytest.mark.asyncio
async def test_academic_search_provider_protocol_generic_callable() -> None:
    """The Protocol is structurally typed; any matching class works."""

    class MinimalProvider:
        name = "minimal"

        def __init__(self) -> None:
            self.calls: list[str] = []

        async def search(self, query: str, top_k: int) -> SearchResult:
            self.calls.append(query)
            return SearchResult(
                papers=[_paper("doi-m")], provider=self.name, query=query
            )

        async def get_doc_details(self, doi_or_id: str) -> AcademicPaper | None:
            return _paper(doi_or_id)

        async def get_references(self, paper_id: str) -> list[str]:
            return [f"ref-{paper_id}"]

    provider: AcademicSearchProvider = MinimalProvider()
    result = await provider.search("x", 1)
    assert result.papers[0].stable_id == "doi-m"


@pytest.mark.asyncio
async def test_academic_search_provider_retry_decorator_can_wrap() -> None:
    """The optional retry parameter is respected when supplied."""

    from tenacity import AsyncRetrying, stop_after_attempt

    attempts: list[int] = []

    class FlakyProvider:
        name = "flaky"

        async def search(self, query: str, top_k: int) -> SearchResult:
            attempts.append(1)
            if len(attempts) == 1:
                raise RuntimeError("boom")
            return SearchResult(papers=[_paper("recovered")], provider=self.name, query=query)

        async def get_doc_details(self, doi_or_id: str) -> AcademicPaper | None:
            return None

        async def get_references(self, paper_id: str) -> list[str]:
            return []

    client = AcademicSearchClient(
        http_client=None,  # type: ignore[arg-type]
        providers=[FlakyProvider()],
        retry=AsyncRetrying(stop=stop_after_attempt(2)),
    )
    result = await client.search("x", 1)
    assert result.success
    assert len(attempts) == 2
