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
from ..lightning.types import PaperDetail
from .openalex import openalex_get_doc, openalex_referenced_works, openalex_search

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


def _stable_id(details: PaperDetail, provider: str) -> str:
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


def _doc_to_paper(details: PaperDetail, provider: str) -> AcademicPaper:
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


class _OpenAlexAcademicProvider:
    name = "openalex"

    def __init__(self, session: httpx.AsyncClient) -> None:
        self.session = session

    async def search(self, query: str, top_k: int) -> SearchResult:
        started = time.perf_counter()
        logger.debug(
            "OpenAlex.search start, query='%s', top_k=%d",
            query,
            top_k,
        )
        documents = await openalex_search(query, self.session, top_k, "*")
        papers = [_doc_to_paper(document, self.name) for document in documents]
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "OpenAlex.search done, query='%s', papers=%d, elapsed_ms=%d",
            query,
            len(papers),
            elapsed_ms,
        )
        return SearchResult(
            papers=papers,
            provider=self.name,
            query=query,
            elapsed_ms=elapsed_ms,
            total_results=len(papers),
        )

    async def get_doc_details(self, doi_or_id: str) -> AcademicPaper | None:
        logger.debug("OpenAlex.get_doc_details, id='%s'", doi_or_id)
        details = await openalex_get_doc(doi_or_id, self.session)
        if details:
            logger.debug(
                "OpenAlex.get_doc_details found, id='%s', title='%s'",
                doi_or_id,
                details.title[:40] if details.title else "N/A",
            )
        else:
            logger.debug(
                "OpenAlex.get_doc_details not found, id='%s'",
                doi_or_id,
            )
        return _doc_to_paper(details, self.name) if details else None

    async def get_references(self, paper_id: str) -> list[str]:
        logger.debug("OpenAlex.get_references, paper_id='%s'", paper_id)
        refs = await openalex_referenced_works(paper_id, self.session)
        logger.debug(
            "OpenAlex.get_references done, paper_id='%s', refs=%d",
            paper_id,
            len(refs),
        )
        return refs


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
        logger.info(
            "AcademicSearchClient initialized, providers=%s",
            [p.name for p in self.providers],
        )

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
        logger.debug(
            "AcademicSearchClient.search start, query='%s', top_k=%d, providers=%s",
            query,
            top_k,
            [p.name for p in self.providers],
        )

        async def run(provider: AcademicSearchProvider) -> SearchResult:
            self.call_counts[provider.name] += 1
            t0 = time.perf_counter()
            try:
                result = await self._call(lambda: provider.search(query, top_k))
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                if result.success:
                    logger.debug(
                        "AcademicSearchClient provider '%s' search success, papers=%d, elapsed_ms=%d",
                        provider.name,
                        len(result.papers),
                        elapsed_ms,
                    )
                else:
                    logger.warning(
                        "AcademicSearchClient provider '%s' search failed: %s",
                        provider.name,
                        result.error_message,
                    )
                return result
            except Exception as exc:
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                logger.error(
                    "AcademicSearchClient provider '%s' search exception: %s, elapsed_ms=%d",
                    provider.name,
                    exc,
                    elapsed_ms,
                    exc_info=True,
                )
                raise

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
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "AcademicSearchClient.search done, query='%s', papers=%d (merged from %d providers), "
            "successful=%d, errors=%s, elapsed_ms=%d",
            query,
            min(len(papers_by_id), top_k),
            successful_providers,
            successful_providers,
            errors,
            elapsed_ms,
        )
        return SearchResult(
            papers=list(papers_by_id.values())[:top_k],
            provider=self.name,
            query=query,
            elapsed_ms=elapsed_ms,
            success=successful_providers > 0,
            error_message="; ".join(errors) or None,
            total_results=len(papers_by_id),
        )

    async def get_doc_details(self, doi_or_id: str) -> AcademicPaper | None:
        logger.debug(
            "AcademicSearchClient.get_doc_details, id='%s', providers=%s",
            doi_or_id,
            [p.name for p in self.providers],
        )
        errors: list[str] = []
        for provider in self.providers:
            self.call_counts[provider.name] += 1
            try:
                if paper := await self._call(
                    lambda provider=provider: provider.get_doc_details(doi_or_id)
                ):
                    logger.debug(
                        "AcademicSearchClient.get_doc_details: provider '%s' found paper '%s'",
                        provider.name,
                        paper.title[:40] if paper.title else paper.stable_id,
                    )
                    return paper
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                errors.append(f"{provider.name}: {exc}")
                logger.warning("Academic provider %s failed: %s", provider.name, exc)
        self.last_errors = errors
        logger.debug("AcademicSearchClient.get_doc_details: not found for id='%s'", doi_or_id)
        return None

    async def get_references(self, paper_id: str) -> list[str]:
        logger.debug(
            "AcademicSearchClient.get_references, paper_id='%s', providers=%s",
            paper_id,
            [p.name for p in self.providers],
        )
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
        deduped = list(dict.fromkeys(outcomes))
        logger.debug(
            "AcademicSearchClient.get_references done, paper_id='%s', refs=%d (deduped=%d)",
            paper_id,
            len(outcomes),
            len(deduped),
        )
        return deduped
