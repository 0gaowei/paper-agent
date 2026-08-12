from __future__ import annotations

import logging
import os
from collections.abc import Collection
from datetime import datetime
from functools import cache
from typing import Any
from urllib.parse import quote

import httpx
from tenacity import (
    AsyncRetrying,
    before_sleep_log,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from evoscholar.lightning.types import PaperDetail
from evoscholar.utils import BIBTEX_MAPPING, mutate_acute_accents, strings_similarity

from .client_models import DOIOrTitleBasedProvider, DOIQuery, TitleAuthorQuery
from .exceptions import DOINotFoundError

OPENALEX_HOST = "api.openalex.org"
OPENALEX_BASE_URL = f"https://{OPENALEX_HOST}"
OPENALEX_API_REQUEST_TIMEOUT = float(
    os.environ.get("OPENALEX_API_REQUEST_TIMEOUT", "10.0")
)  # seconds

logger = logging.getLogger(__name__)


# author_name will be FamilyName, GivenName Middle initial. (if available)
# there is no standalone "FamilyName" or "GivenName" fields
# this manually constructs the name into the format the other clients use
def reformat_name(name: str) -> str:
    if "," not in name:
        return name
    family, given_names = (x.strip() for x in name.split(",", maxsplit=1))
    # Return the reformatted name
    return f"{given_names} {family}"


@cache
def get_openalex_mailto() -> str | None:
    """Get the OpenAlex mailto address, if available."""
    mailto_address = os.getenv("OPENALEX_MAILTO")
    if mailto_address is None:
        logger.warning(
            "OPENALEX_MAILTO environment variable not set."
            " your request may be deprioritized by OpenAlex."
        )
    return mailto_address


@cache
def get_openalex_api_key() -> str | None:
    """
    Get the OpenAlex API key from 'OPENALEX_API_KEY' if available, for premium features.

    SEE: https://github.com/ourresearch/openalex-api-tutorials/blob/main/notebooks/getting-started/premium.ipynb
    """
    return os.getenv("OPENALEX_API_KEY")


async def get_doc_details_from_openalex(  # noqa: PLR0912
    client: httpx.AsyncClient,
    doi: str | None = None,
    title: str | None = None,
    fields: Collection[str] | None = None,
    title_similarity_threshold: float = 0.75,
) -> PaperDetail | None:
    """Get paper details from OpenAlex given a DOI or paper title.

    Args:
        client: Async HTTP client for any requests.
        doi: The DOI of the paper.
        title: The title of the paper.
        fields: Specific fields to include in the request.
        title_similarity_threshold: The threshold for title similarity.

    Returns:
        The details of the document if found, otherwise None.

    Raises:
        ValueError: If neither DOI nor title is provided.
        DOINotFoundError: If the paper cannot be found.
    """
    mailto = get_openalex_mailto()
    params = {"mailto": mailto} if mailto else {}
    api_key = get_openalex_api_key()
    headers = {"api_key": api_key} if api_key else {}

    if doi is title is None:
        raise ValueError("Either a DOI or title must be provided.")

    url = f"{OPENALEX_BASE_URL}/works"
    if doi:
        # this looks wrong but it's now
        # will compile to a relative url similar to:
        # https://api.openalex.org/works/https://doi.org/10.7717/peerj.4375
        url += f"/https://doi.org/{quote(doi, safe='')}"
    elif title:
        params["filter"] = f"title.search:{title}"

    if fields:
        params["select"] = ",".join(fields)
    try:
        # Seen on 11/4/2025 with OpenAlex and both a client-level timeout of 15-sec
        # and API request timeout of 15-sec, we repeatedly saw httpx.ConnectTimeout
        # being thrown for DOIs 10.1046/j.1365-2699.2003.00795 and 10.2147/cia.s3785,
        # even with up to 3 retries
        async for attempt in AsyncRetrying(
            retry=retry_if_exception(
                lambda exc: (
                    isinstance(exc, httpx.ReadTimeout)
                    or (
                        isinstance(exc, httpx.HTTPStatusError)
                        and exc.response.status_code
                        == httpx.codes.INTERNAL_SERVER_ERROR
                    )
                )
            ),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            stop=stop_after_attempt(3),
        ):
            with attempt:
                response = await client.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=OPENALEX_API_REQUEST_TIMEOUT,
                )
                response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if response.status_code == httpx.codes.NOT_FOUND:
            raise DOINotFoundError(
                f"Could not find paper given DOI/title,"
                f" response text was {response.text!r}."
            ) from exc
        raise  # Can get 429'd by OpenAlex

    response_data = response.json()
    if response_data.get("status") == "failed":
        raise DOINotFoundError("OpenAlex API returned a failed status for the query.")

    results_data = response_data

    if params.get("filter") is not None:
        results_data = results_data["results"]
        if len(results_data) == 0:
            raise DOINotFoundError(
                "OpenAlex API did not return any items for the query."
            )
        results_data = results_data[0]

    # openalex keeps the DOI prefix on (we remove)
    if results_data.get("doi"):
        results_data["doi"] = results_data["doi"].removeprefix("https://doi.org/")

    if (
        doi is None
        and title
        and strings_similarity(results_data.get("title", ""), title)
        < title_similarity_threshold
    ):
        raise DOINotFoundError(f"OpenAlex results did not match for title {title!r}.")

    if doi and results_data.get("doi") != doi:
        raise DOINotFoundError(f"DOI {doi!r} not found in OpenAlex.")

    return parse_openalex_to_paper_detail(results_data)


def parse_openalex_to_paper_detail(message: dict[str, Any]) -> PaperDetail:
    """Parse an OpenAlex work payload into a `PaperDetail`.

    与上游 `parse_openalex_to_doc_details` 的关键差异：
    - 论文库字段（bibtex / key / issue / publisher / issn / license /
      volume / pages / url）全部进 `other` 字典
    - 不返回 `DocDetails`，仅返回我们搜索场景需要的最小模型
    """
    raw_author_names = [
        authorship.get("raw_author_name", "")
        for authorship in message.get("authorships") or []  # Handle None authorships
        if authorship
    ]
    sanitized_authors = [
        mutate_acute_accents(text=reformat_name(author), replace=True)
        for author in raw_author_names
    ]

    primary_location = message.get("primary_location") or {}
    source = primary_location.get("source") or {}

    publisher = source.get("host_organization_name", None)
    journal = source.get("display_name", None)
    issn = source.get("issn_l", None)
    volume = message.get("biblio", {}).get("volume", None)
    issue = message.get("biblio", {}).get("issue", None)
    pages = message.get("biblio", {}).get("last_page", None)
    doi = message.get("doi")
    title = message.get("title")
    citation_count = message.get("cited_by_count")
    publication_year = message.get("publication_year")

    best_oa_location = message.get("best_oa_location") or {}
    pdf_url = best_oa_location.get("pdf_url", None)
    oa_license = best_oa_location.get("license", None)

    publication_date_str = message.get("publication_date", "")
    try:
        publication_date = (
            datetime.fromisoformat(publication_date_str)
            if publication_date_str
            else None
        )
    except ValueError:
        publication_date = None

    bibtex_type = BIBTEX_MAPPING.get(message.get("type") or "other", "misc")

    abstract = _restore_openalex_abstract(message.get("abstract_inverted_index"))

    paper = PaperDetail(
        docname=doi or message.get("id", ""),
        title=title or "",
        authors=sanitized_authors,
        year=publication_year,
        doi=doi,
        publication_date=publication_date,
        abstract=abstract,
        journal=journal,
        citation_count=citation_count,
        pdf_url=pdf_url,
        url=doi,
        other={},
    )

    # 论文库特有字段（volume/issue/pages 等）+ OpenAlex 原始 payload 全存 `other`
    paper.other = {
        "publisher": publisher,
        "issn": issn,
        "volume": volume,
        "issue": issue,
        "pages": pages,
        "license": oa_license,
        "bibtex_type": bibtex_type,
        "client_source": ["openalex"],
        **message,
    }
    return paper


class OpenAlexProvider(DOIOrTitleBasedProvider):
    """An open source provider of scholarly documents.

    Includes information on work, researchers, institutions, journals,
    and research topics.
    """

    async def get_doc_details(
        self, doi: str, client: httpx.AsyncClient, fields: Collection[str] | None = None
    ) -> PaperDetail | None:
        """Get document details by DOI.

        Args:
            doi: The DOI of the document.
            client: Async HTTP client for any requests.
            fields: Specific fields to include in the request.

        Returns:
            The document details if found, otherwise None.
        """
        return await get_doc_details_from_openalex(
            doi=doi, client=client, fields=fields
        )

    async def search_by_title(
        self,
        query: str,
        client: httpx.AsyncClient,
        title_similarity_threshold: float = 0.75,
        fields: Collection[str] | None = None,
    ) -> PaperDetail | None:
        """Search for document details by title.

        Args:
            query: The title query for the document.
            client: Async HTTP client for any requests.
            title_similarity_threshold: Threshold for title similarity.
            fields: Specific fields to include in the request.

        Returns:
            The document details if found, otherwise None.
        """
        return await get_doc_details_from_openalex(
            title=query,
            client=client,
            title_similarity_threshold=title_similarity_threshold,
            fields=fields,
        )

    async def _query(self, query: TitleAuthorQuery | DOIQuery) -> PaperDetail | None:
        """Query the OpenAlex API via the provided DOI or title.

        Args:
            query: The query containing either a DOI or title.
                    DOI is prioritized over title.

        Returns:
            The document details if found, otherwise None.
        """
        if isinstance(query, DOIQuery):
            return await self.get_doc_details(
                doi=query.doi, client=query.client, fields=query.fields
            )
        return await self.search_by_title(
            query=query.title,
            client=query.client,
            title_similarity_threshold=query.title_similarity_threshold,
            fields=query.fields,
        )


def _restore_openalex_abstract(inverted_index: Any) -> str | None:
    if not isinstance(inverted_index, dict) or not inverted_index:
        return None
    indexed_words: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        if not isinstance(positions, list):
            continue
        indexed_words.extend((int(position), str(word)) for position in positions)
    return " ".join(word for _, word in sorted(indexed_words)) or None


def _prepare_openalex_work(message: dict[str, Any]) -> dict[str, Any]:
    work = dict(message)
    if work.get("doi"):
        work["doi"] = str(work["doi"]).removeprefix("https://doi.org/")
    work["abstract"] = _restore_openalex_abstract(work.get("abstract_inverted_index"))
    return work


async def _openalex_get(
    url: str, session: httpx.AsyncClient, *, params: dict[str, Any] | None = None
) -> dict[str, Any]:
    request_params = dict(params or {})
    if mailto := get_openalex_mailto():
        request_params.setdefault("mailto", mailto)
    headers = {"api_key": key} if (key := get_openalex_api_key()) else {}
    async for attempt in AsyncRetrying(
        retry=retry_if_exception(
            lambda exc: isinstance(exc, (httpx.ReadTimeout, httpx.ConnectTimeout))
            or (
                isinstance(exc, httpx.HTTPStatusError)
                and exc.response.status_code
                in (
                    httpx.codes.TOO_MANY_REQUESTS,
                    httpx.codes.INTERNAL_SERVER_ERROR,
                    httpx.codes.BAD_GATEWAY,
                    httpx.codes.SERVICE_UNAVAILABLE,
                    httpx.codes.GATEWAY_TIMEOUT,
                )
            )
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        stop=stop_after_attempt(5),
        wait=wait_exponential_jitter(initial=1, max=30),
    ):
        with attempt:
            response = await session.get(
                url,
                params=request_params,
                headers=headers,
                timeout=OPENALEX_API_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
    raise RuntimeError("OpenAlex request retry loop exited unexpectedly")


async def openalex_search(
    query: str,
    session: httpx.AsyncClient,
    per_page: int,
    cursor: str = "*",
) -> list[PaperDetail]:
    """Search OpenAlex works and restore its inverted-index abstracts."""
    data = await _openalex_get(
        f"{OPENALEX_BASE_URL}/works",
        session,
        params={"search": query, "per-page": per_page, "cursor": cursor},
    )
    return [
        parse_openalex_to_paper_detail(_prepare_openalex_work(message))
        for message in data.get("results", [])
    ]


async def openalex_referenced_works(
    paper_id: str, session: httpx.AsyncClient
) -> list[str]:
    """Return works referenced by an OpenAlex paper."""
    data = await _openalex_get(
        f"{OPENALEX_BASE_URL}/works/{quote(paper_id, safe=':/')}", session
    )
    return [str(identifier) for identifier in data.get("referenced_works") or []]


async def openalex_get_doc(
    paper_id: str, session: httpx.AsyncClient
) -> PaperDetail | None:
    """Fetch one OpenAlex work by OpenAlex ID or DOI."""
    identifier = paper_id
    if paper_id.lower().startswith("10."):
        identifier = f"https://doi.org/{paper_id}"
    try:
        data = await _openalex_get(
            f"{OPENALEX_BASE_URL}/works/{quote(identifier, safe=':/')}", session
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == httpx.codes.NOT_FOUND:
            return None
        raise
    return parse_openalex_to_paper_detail(_prepare_openalex_work(data))
