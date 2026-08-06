from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from collections import Counter
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, Protocol, runtime_checkable

import httpx
from tenacity import AsyncRetrying

from ..iterative_search.models import AcademicPaper, SearchResult
from ..types import DocDetails
from .openalex import openalex_get_doc, openalex_referenced_works, openalex_search
from .semantic_scholar import s2_get_doc_details, s2_paper_references, s2_topic_search

logger = logging.getLogger(__name__)


@runtime_checkable
class AcademicSearchProvider(Protocol):
    """Protocol implemented by multi-paper academic search providers."""

    name: str

    async def search(self, query: str, top_k: int) -> SearchResult: ...

    async def get_doc_details(self, doi_or_id: str) -> AcademicPaper | None: ...

    async def get_references(self, paper_id: str) -> list[str]: ...


def _normalized_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    return doi.removeprefix("https://doi.org/").removeprefix("http://dx.doi.org/").lower()


def _stable_id(details: DocDetails, provider: str) -> str:
    if doi := _normalized_doi(details.doi):
        return doi
    other = details.other or {}
    source_id = other.get("paperId") or other.get("id")
    if source_id:
        return str(source_id).rsplit("/", maxsplit=1)[-1]
    normalized_title = re.sub(r"\W+", " ", details.title or "untitled").strip().casefold()
    digest = hashlib.sha1(
        f"{normalized_title}|{details.year or ''}".encode(), usedforsecurity=False
    ).hexdigest()[:16]
    return f"{provider}:{digest}"


def _doc_to_paper(details: DocDetails, provider: str) -> AcademicPaper:
    other = details.other or {}
    fields = other.get("fieldsOfStudy") or [
        concept.get("display_name", "")
        for concept in other.get("concepts") or []
        if isinstance(concept, dict)
    ]
    referenced = other.get("referenced_works") or []
    return AcademicPaper(
        stable_id=_stable_id(details, provider),
        title=details.title,
        abstract=other.get("abstract"),
        authors=list(details.authors or []),
        year=details.year,
        publication_date=details.publication_date,
        journal=details.journal,
        doi=_normalized_doi(details.doi),
        citation_count=details.citation_count,
        pdf_url=details.pdf_url,
        url=details.url or other.get("url"),
        fields_of_study=[str(field) for field in fields if field],
        source=provider,
        sources=[provider],
        citation_ids=[str(identifier) for identifier in referenced],
    )


class _SemanticScholarAcademicProvider:
    name = "semantic_scholar"

    def __init__(self, session: httpx.AsyncClient) -> None:
        self.session = session

    async def search(self, query: str, top_k: int) -> SearchResult:
        started = time.perf_counter()
        documents = await s2_topic_search(query, top_k, 0, self.session)
        papers = [_doc_to_paper(document, self.name) for document in documents]
        return SearchResult(
            papers=papers,
            provider=self.name,
            query=query,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
            total_results=len(papers),
        )

    async def get_doc_details(self, doi_or_id: str) -> AcademicPaper | None:
        details = await s2_get_doc_details(doi_or_id, self.session)
        return _doc_to_paper(details, self.name) if details else None

    async def get_references(self, paper_id: str) -> list[str]:
        return await s2_paper_references(paper_id, self.session)


class _OpenAlexAcademicProvider:
    name = "openalex"

    def __init__(self, session: httpx.AsyncClient) -> None:
        self.session = session

    async def search(self, query: str, top_k: int) -> SearchResult:
        started = time.perf_counter()
        documents = await openalex_search(query, self.session, top_k, "*")
        papers = [_doc_to_paper(document, self.name) for document in documents]
        return SearchResult(
            papers=papers,
            provider=self.name,
            query=query,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
            total_results=len(papers),
        )

    async def get_doc_details(self, doi_or_id: str) -> AcademicPaper | None:
        details = await openalex_get_doc(doi_or_id, self.session)
        return _doc_to_paper(details, self.name) if details else None

    async def get_references(self, paper_id: str) -> list[str]:
        return await openalex_referenced_works(paper_id, self.session)


class AcademicSearchClient:
    """Aggregate academic providers while preserving partial successes."""

    name = "academic_search"

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        providers: Sequence[AcademicSearchProvider] | None = None,
        retry: AsyncRetrying | None = None,
        provider_names: Sequence[str] | None = None,
    ) -> None:
        self.http_client = http_client
        built_in_providers: dict[str, AcademicSearchProvider] = {
            "semantic_scholar": _SemanticScholarAcademicProvider(http_client),
            "openalex": _OpenAlexAcademicProvider(http_client),
        }
        selected_names = list(provider_names or built_in_providers)
        self.providers = (
            list(providers)
            if providers is not None
            else [
                built_in_providers[name]
                for name in selected_names
                if name in built_in_providers
            ]
        )
        if not self.providers:
            raise ValueError("At least one academic search provider must be configured")
        self.retry = retry
        self.call_counts: Counter[str] = Counter()
        self.last_errors: list[str] = []

    async def _call(self, operation: Callable[[], Awaitable[Any]]) -> Any:
        if self.retry is None:
            return await operation()
        retrying = self.retry.copy()
        async for attempt in retrying:
            with attempt:
                return await operation()
        raise RuntimeError("provider retry loop exited unexpectedly")

    async def search(self, query: str, top_k: int) -> SearchResult:
        started = time.perf_counter()

        async def run(provider: AcademicSearchProvider) -> SearchResult:
            self.call_counts[provider.name] += 1
            return await self._call(lambda: provider.search(query, top_k))

        outcomes = await asyncio.gather(
            *(run(provider) for provider in self.providers), return_exceptions=True
        )
        papers_by_id: dict[str, AcademicPaper] = {}
        errors: list[str] = []
        successful_providers = 0
        for provider, outcome in zip(self.providers, outcomes, strict=True):
            if isinstance(outcome, asyncio.CancelledError):
                raise outcome
            if isinstance(outcome, BaseException):
                errors.append(f"{provider.name}: {outcome}")
                logger.warning("Academic provider %s failed: %s", provider.name, outcome)
                continue
            if not outcome.success:
                errors.append(f"{provider.name}: {outcome.error_message or 'search failed'}")
                continue
            successful_providers += 1
            for paper in outcome.papers:
                existing = papers_by_id.get(paper.stable_id)
                if existing is None:
                    papers_by_id[paper.stable_id] = paper
                    continue
                existing.sources = list(
                    dict.fromkeys([*existing.sources, *paper.sources, paper.source])
                )
                if not existing.abstract and paper.abstract:
                    existing.abstract = paper.abstract
                if not existing.fields_of_study and paper.fields_of_study:
                    existing.fields_of_study = paper.fields_of_study
                existing.citation_ids = list(
                    dict.fromkeys([*existing.citation_ids, *paper.citation_ids])
                )
        self.last_errors = errors
        return SearchResult(
            papers=list(papers_by_id.values())[:top_k],
            provider=self.name,
            query=query,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
            success=successful_providers > 0,
            error_message="; ".join(errors) or None,
            total_results=len(papers_by_id),
        )

    async def get_doc_details(self, doi_or_id: str) -> AcademicPaper | None:
        errors: list[str] = []
        for provider in self.providers:
            self.call_counts[provider.name] += 1
            try:
                if paper := await self._call(
                    lambda provider=provider: provider.get_doc_details(doi_or_id)
                ):
                    return paper
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                errors.append(f"{provider.name}: {exc}")
                logger.warning("Academic provider %s failed: %s", provider.name, exc)
        self.last_errors = errors
        return None

    async def get_references(self, paper_id: str) -> list[str]:
        outcomes: list[str] = []
        errors: list[str] = []
        for provider in self.providers:
            self.call_counts[provider.name] += 1
            try:
                outcomes.extend(
                    await self._call(
                        lambda provider=provider: provider.get_references(paper_id)
                    )
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                errors.append(f"{provider.name}: {exc}")
                logger.warning("Academic provider %s failed: %s", provider.name, exc)
        self.last_errors = errors
        return list(dict.fromkeys(outcomes))
