from __future__ import annotations

import asyncio
import time
from collections import Counter
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import httpx
from lmi import embedding_model_factory

from evoscholar.query_understanding import analyze_and_expand_query
from evoscholar.paper_ranker.relevance import RelevanceTier
from evoscholar.paper_ranker import ascore_papers, rank_with_mmr, score_papers

from .callbacks import NoOpProgressCallback, ResearchProgressCallback
from .models import (
    AcademicPaper,
    CitationEdge,
    ResearchSession,
    SearchResult,
    SearchRound,
    StopReason,
    UsageStats,
)

if TYPE_CHECKING:
    from evoscholar.synthesis.builder import build_evidence_and_answer
    from evoscholar.synthesis.models import AnswerSummary, EvidenceSnippet
    from ..metadata_clients.academic_search import AcademicSearchProvider


class _TrackedLLMAdapter:
    """Expose PaperQA's call_single API around either supported LLM interface.

    This adapter is used in query understanding (before synthesis) to track
    LLM usage. The usage is accumulated into the session's UsageStats.
    """

    def __init__(self, delegate: Any, usage: UsageStats) -> None:
        import inspect
        from lmi import LLMResult

        self.delegate = delegate
        self.usage = usage

    async def call_single(self, messages: Any, **kwargs: Any) -> Any:
        import inspect
        from lmi import LLMResult

        if hasattr(self.delegate, "call_single"):
            response = self.delegate.call_single(messages=messages, **kwargs)
        elif hasattr(self.delegate, "acomplete"):
            serialized = [
                {
                    "role": getattr(message, "role", None) or "user",
                    "content": getattr(message, "content", None) or str(message),
                }
                for message in messages
            ]
            response = self.delegate.acomplete(serialized)
        else:
            raise TypeError("LLM model must provide call_single() or acomplete()")
        response = await response if inspect.isawaitable(response) else response
        self.usage.llm_calls += 1

        if isinstance(response, LLMResult):
            self.usage.llm_prompt_tokens += response.prompt_count or 0
            self.usage.llm_completion_tokens += response.completion_count or 0
            self.usage.llm_cost_usd += response.cost
            return response

        def _usage_value_inner(usage: Any, *names: str) -> int:
            for name in names:
                value = usage.get(name) if isinstance(usage, dict) else getattr(usage, name, None)
                if value is not None:
                    return int(value)
            return 0

        raw_usage = (
            response.get("usage") if isinstance(response, dict) else getattr(response, "usage", None)
        )
        prompt_tokens = _usage_value_inner(raw_usage, "prompt_tokens", "input_tokens")
        completion_tokens = _usage_value_inner(raw_usage, "completion_tokens", "output_tokens")
        hidden = getattr(response, "_hidden_params", {}) or {}
        cost = float(hidden.get("response_cost") or 0.0)
        self.usage.llm_prompt_tokens += prompt_tokens
        self.usage.llm_completion_tokens += completion_tokens
        self.usage.llm_cost_usd += cost
        return LLMResult(
            model=str(getattr(self.delegate, "name", "research-llm")),
            text=self._response_text(response),
            prompt_count=prompt_tokens,
            completion_count=completion_tokens,
            cost=cost,
        )

    def _response_text(self, response: Any) -> str:
        if isinstance(response, str):
            return response
        if isinstance(response, LLMResult):
            return response.text or ""
        if isinstance(response, dict):
            if isinstance(response.get("content"), str):
                return response["content"]
            choices = response.get("choices") or []
            if choices:
                return str((choices[0].get("message") or {}).get("content") or "")
        if isinstance(getattr(response, "text", None), str):
            return response.text
        choices = getattr(response, "choices", None) or []
        if choices:
            return str(getattr(getattr(choices[0], "message", None), "content", "") or "")
        return str(response)


class _EvidenceAdapter:
    """Inject paper abstracts into Docs without touching its file/PDF ingestion path.

    This adapter is used in the fallback path (when synthesis fails) to build
    evidence from paper abstracts.
    """

    def __init__(self, papers: Sequence[AcademicPaper]) -> None:
        from evoscholar.literature_qa.docs import Docs
        from evoscholar.literature_qa.core import DocDetails, Text

        self.docs = Docs()
        self.paper_by_id = {paper.stable_id: paper for paper in papers}
        for paper in papers:
            if not (paper.abstract or "").strip():
                continue
            citation = self._citation(paper)
            details = DocDetails(
                docname=paper.stable_id,
                dockey=paper.stable_id,
                citation=citation,
                title=paper.title,
                authors=paper.authors,
                year=paper.year,
                publication_date=paper.publication_date,
                journal=paper.journal,
                doi=paper.doi,
                citation_count=paper.citation_count,
                pdf_url=paper.pdf_url,
                url=paper.url,
                other={"client_source": paper.sources or [paper.source]},
            )
            text = Text(name=paper.stable_id, text=paper.abstract or "", doc=details)
            self.docs.docs[details.dockey] = details
            self.docs.texts.append(text)
            self.docs.docnames.add(details.docname)

    @staticmethod
    def _citation(paper: AcademicPaper) -> str:
        authors = ", ".join(paper.authors[:3]) or "Unknown authors"
        year = str(paper.year) if paper.year else "n.d."
        return f"{authors}. {paper.title or paper.stable_id}. {year}."

    async def aget_evidence(self, *args: Any, **kwargs: Any) -> Any:
        return await self.docs.aget_evidence(*args, **kwargs)

    async def aquery(self, *args: Any, **kwargs: Any) -> Any:
        return await self.docs.aquery(*args, **kwargs)


class ResearchEngine:
    """Run query understanding, bounded BFS retrieval, evidence, and answer synthesis."""

    def __init__(
        self,
        settings: Any,
        llm_model: Any = None,
        embedding_model: Any = None,
        providers: AcademicSearchProvider | Sequence[AcademicSearchProvider] | None = None,
    ) -> None:
        self.settings = settings
        self.llm_model = llm_model or settings.get_llm()
        if embedding_model is None:
            embedding_name = settings.research.embedding_model or settings.embedding
            try:
                embedding_model = embedding_model_factory(
                    embedding_name, **(settings.embedding_config or {})
                )
            except Exception:
                embedding_model = None
        self.embedding_model = embedding_model
        self._http_client: httpx.AsyncClient | None = None
        self._owns_http_client = False

        if providers is None:
            from ..metadata_clients.academic_search import AcademicSearchClient

            self._http_client = httpx.AsyncClient()
            self._owns_http_client = True
            self.provider: AcademicSearchProvider = AcademicSearchClient(
                self._http_client, provider_names=settings.research.providers
            )
        elif isinstance(providers, Sequence) and not isinstance(providers, (str, bytes)):
            from ..metadata_clients.academic_search import AcademicSearchClient

            self._http_client = httpx.AsyncClient()
            self._owns_http_client = True
            self.provider = AcademicSearchClient(
                self._http_client, providers=list(providers)
            )
        else:
            self.provider = providers

    async def aclose(self) -> None:
        """Close the internally owned HTTP client, if one was created."""
        if self._owns_http_client and self._http_client is not None:
            await self._http_client.aclose()
            self._owns_http_client = False

    async def __aenter__(self) -> ResearchEngine:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()

    @staticmethod
    def _merge_paper(existing: AcademicPaper, incoming: AcademicPaper) -> None:
        existing.sources = list(
            dict.fromkeys([*existing.sources, incoming.source, *incoming.sources])
        )
        existing.citation_ids = list(
            dict.fromkeys([*existing.citation_ids, *incoming.citation_ids])
        )
        existing.cited_by_ids = list(
            dict.fromkeys([*existing.cited_by_ids, *incoming.cited_by_ids])
        )
        for field in (
            "title",
            "abstract",
            "year",
            "publication_date",
            "journal",
            "doi",
            "citation_count",
            "pdf_url",
            "url",
        ):
            if getattr(existing, field) in (None, "", []) and getattr(incoming, field) not in (
                None,
                "",
                [],
            ):
                setattr(existing, field, getattr(incoming, field))
        if not existing.authors:
            existing.authors = incoming.authors
        existing.fields_of_study = list(
            dict.fromkeys([*existing.fields_of_study, *incoming.fields_of_study])
        )

    def _budget_exceeded(self, session: ResearchSession) -> bool:
        config = self.settings.research
        total_tokens = (
            session.usage.llm_prompt_tokens + session.usage.llm_completion_tokens
        )
        total_api_calls = sum(session.usage.api_calls_by_provider.values())
        return (
            total_tokens >= config.token_budget
            or session.usage.llm_cost_usd >= config.llm_budget_usd
            or total_api_calls >= config.api_budget
        )

    @staticmethod
    def _provider_counts(provider: AcademicSearchProvider) -> Counter[str]:
        values = getattr(provider, "call_counts", {})
        return Counter({str(key): int(value) for key, value in values.items()})

    def _sync_api_usage(
        self, session: ResearchSession, baseline: Counter[str]
    ) -> None:
        current = self._provider_counts(self.provider)
        if current:
            session.usage.api_calls_by_provider = {
                name: max(0, count - baseline.get(name, 0))
                for name, count in current.items()
                if count - baseline.get(name, 0) > 0
            }

    async def _call_provider(
        self,
        operation: Callable[[], Awaitable[Any]],
        session: ResearchSession,
        baseline: Counter[str],
    ) -> Any:
        has_internal_counts = bool(getattr(self.provider, "call_counts", None) is not None)
        if not has_internal_counts:
            name = str(getattr(self.provider, "name", type(self.provider).__name__))
            session.usage.api_calls_by_provider[name] = (
                session.usage.api_calls_by_provider.get(name, 0) + 1
            )
        try:
            return await operation()
        finally:
            self._sync_api_usage(session, baseline)

    async def _run_searches(
        self,
        queries: list[str],
        session: ResearchSession,
        baseline: Counter[str],
    ) -> list[SearchResult | BaseException]:
        semaphore = asyncio.Semaphore(self.settings.research.concurrency)
        top_k = max(
            1, self.settings.research.max_candidates_per_round // max(1, len(queries))
        )

        async def run(query: str) -> SearchResult:
            async with semaphore:
                return await self._call_provider(
                    lambda: self.provider.search(query, top_k), session, baseline
                )

        return await asyncio.gather(
            *(run(query) for query in queries), return_exceptions=True
        )

    async def _expand_references(
        self,
        papers: Sequence[AcademicPaper],
        session: ResearchSession,
        baseline: Counter[str],
    ) -> list[AcademicPaper]:
        config = self.settings.research
        if config.max_references_per_node <= 0:
            return []
        semaphore = asyncio.Semaphore(config.concurrency)

        async def references_for(paper: AcademicPaper) -> tuple[AcademicPaper, list[str]]:
            async with semaphore:
                references = await self._call_provider(
                    lambda: self.provider.get_references(paper.stable_id),
                    session,
                    baseline,
                )
                return paper, references[: config.max_references_per_node]

        reference_results = await asyncio.gather(
            *(references_for(paper) for paper in papers), return_exceptions=True
        )
        pending_details: list[tuple[AcademicPaper, str]] = []
        for outcome in reference_results:
            if isinstance(outcome, asyncio.CancelledError):
                raise outcome
            if isinstance(outcome, BaseException):
                continue
            paper, reference_ids = outcome
            for reference_id in reference_ids:
                session.citation_graph.append(
                    CitationEdge(
                        source_id=paper.stable_id,
                        target_id=reference_id,
                        provider=paper.source,
                    )
                )
                if reference_id not in session.all_papers:
                    pending_details.append((paper, reference_id))

        remaining = max(0, config.max_candidates_per_round)
        pending_details = pending_details[:remaining]

        async def fetch_detail(reference_id: str) -> AcademicPaper | None:
            async with semaphore:
                return await self._call_provider(
                    lambda: self.provider.get_doc_details(reference_id), session, baseline
                )

        detail_results = await asyncio.gather(
            *(fetch_detail(reference_id) for _, reference_id in pending_details),
            return_exceptions=True,
        )
        discovered: list[AcademicPaper] = []
        for (source_paper, reference_id), outcome in zip(
            pending_details, detail_results, strict=True
        ):
            if isinstance(outcome, asyncio.CancelledError):
                raise outcome
            if isinstance(outcome, BaseException) or outcome is None:
                continue
            discovered.append(outcome)
            for edge in reversed(session.citation_graph):
                if edge.source_id == source_paper.stable_id and edge.target_id == reference_id:
                    edge.target_id = outcome.stable_id
                    break
        return discovered

    async def _build_evidence_and_answer(
        self,
        session: ResearchSession,
        progress_callback: ResearchProgressCallback | None = None,
        session_id: str | None = None,
    ) -> None:
        """Build evidence and answer by delegating to synthesis.builder."""
        evidence, answer = await build_evidence_and_answer(
            papers=session.final_papers,
            query=session.query,
            settings=self.settings,
            llm_model=self.llm_model,
            embedding_model=self.embedding_model,
            session_id=session_id,
            progress_callback=progress_callback,
        )
        session.evidence = evidence
        session.answer = answer

    async def arun(
        self,
        query: str,
        *,
        max_high_relevant: int | None = None,
        precomputed_understanding: Any | None = None,
        progress_callback: ResearchProgressCallback | None = None,
        session_id: str | None = None,
    ) -> ResearchSession:
        """Execute the complete research loop for one query."""
        started = time.perf_counter()
        session = ResearchSession(query=query)
        api_baseline = self._provider_counts(self.provider)
        target_high = 3 if max_high_relevant is None else max(0, max_high_relevant)
        tracked_llm = _TrackedLLMAdapter(self.llm_model, session.usage)

        try:
            session.query_understanding = precomputed_understanding or (
                await analyze_and_expand_query(query, self.settings, tracked_llm)
            )
            if self._budget_exceeded(session):
                session.stop_reason = StopReason.BUDGET_EXCEEDED
            elif target_high == 0:
                session.stop_reason = StopReason.MAX_HIGH_RELEVANT
            else:
                queue: asyncio.Queue[str] = asyncio.Queue()
                seen_queries: set[str] = set()
                for subquery in sorted(
                    session.query_understanding.subqueries,
                    key=lambda item: item.priority,
                    reverse=True,
                ):
                    if subquery.query not in seen_queries:
                        queue.put_nowait(subquery.query)
                        seen_queries.add(subquery.query)

                for round_number in range(1, self.settings.research.max_rounds + 1):
                    if self._budget_exceeded(session):
                        session.stop_reason = StopReason.BUDGET_EXCEEDED
                        break
                    if queue.empty():
                        session.stop_reason = StopReason.QUEUE_EMPTY
                        break

                    round_started = time.perf_counter()
                    round_queries: list[str] = []
                    while not queue.empty():
                        round_queries.append(queue.get_nowait())
                    outcomes = await self._run_searches(
                        round_queries, session, api_baseline
                    )
                    candidates: list[AcademicPaper] = []
                    for outcome in outcomes:
                        if isinstance(outcome, asyncio.CancelledError):
                            raise outcome
                        if isinstance(outcome, BaseException) or not outcome.success:
                            continue
                        candidates.extend(outcome.papers)
                    candidates = candidates[
                        : self.settings.research.max_candidates_per_round
                    ]

                    new_papers: list[AcademicPaper] = []
                    for paper in candidates:
                        if existing := session.all_papers.get(paper.stable_id):
                            self._merge_paper(existing, paper)
                        else:
                            session.all_papers[paper.stable_id] = paper
                            new_papers.append(paper)

                    if session.all_papers:
                        session.usage.embedding_calls += int(
                            self.embedding_model is not None
                        )
                        await ascore_papers(
                            list(session.all_papers.values()),
                            query,
                            self.settings,
                            self.embedding_model,
                        )

                    high_new = [
                        paper
                        for paper in new_papers
                        if paper.relevance_tier == RelevanceTier.HIGH
                    ]
                    expanded = (
                        []
                        if self._budget_exceeded(session)
                        else await self._expand_references(
                            high_new, session, api_baseline
                        )
                    )
                    for paper in expanded:
                        if existing := session.all_papers.get(paper.stable_id):
                            self._merge_paper(existing, paper)
                        else:
                            session.all_papers[paper.stable_id] = paper
                            new_papers.append(paper)
                    if expanded:
                        session.usage.embedding_calls += int(
                            self.embedding_model is not None
                        )
                        await ascore_papers(
                            list(session.all_papers.values()),
                            query,
                            self.settings,
                            self.embedding_model,
                        )

                    ranked = rank_with_mmr(
                        list(session.all_papers.values()),
                        k=len(session.all_papers),
                    )
                    high_count = sum(
                        paper.relevance_tier == RelevanceTier.HIGH
                        for paper in ranked
                    )
                    partial_count = sum(
                        paper.relevance_tier == RelevanceTier.PARTIAL
                        for paper in ranked
                    )
                    followups = 0
                    if round_number < self.settings.research.max_rounds:
                        for paper in ranked[:2]:
                            if (
                                paper.relevance_tier != RelevanceTier.LOW
                                and paper.title
                            ):
                                followup = f"{query} {paper.title}"
                                if followup not in seen_queries:
                                    queue.put_nowait(followup)
                                    seen_queries.add(followup)
                                    followups += 1

                    session.search_rounds.append(
                        SearchRound(
                            round_number=round_number,
                            queries_executed=round_queries,
                            papers_discovered=len(new_papers),
                            papers_evaluated=len(session.all_papers),
                            high_relevant_found=high_count,
                            partial_relevant_found=partial_count,
                            citations_expanded=len(expanded),
                            subqueries_generated=followups,
                            duration_ms=int(
                                (time.perf_counter() - round_started) * 1000
                            ),
                        )
                    )
                    session.usage.search_rounds = len(session.search_rounds)

                    if self._budget_exceeded(session):
                        session.stop_reason = StopReason.BUDGET_EXCEEDED
                        break
                    if high_count >= target_high:
                        session.stop_reason = StopReason.MAX_HIGH_RELEVANT
                        break
                    if not new_papers:
                        session.stop_reason = StopReason.NO_NEW_PAPERS
                        break
                    if queue.empty():
                        session.stop_reason = StopReason.QUEUE_EMPTY
                        break
                else:
                    session.stop_reason = StopReason.MAX_ROUNDS_REACHED

            final_candidates = rank_with_mmr(
                list(session.all_papers.values()),
                k=min(
                    len(session.all_papers),
                    self.settings.research.max_candidates_per_round,
                ),
            )
            relevant = [
                paper
                for paper in final_candidates
                if paper.relevance_tier != RelevanceTier.LOW
            ]
            session.final_papers = relevant or final_candidates
            session.usage.papers_discovered = len(session.all_papers)
            session.usage.papers_evaluated = sum(
                search_round.papers_evaluated for search_round in session.search_rounds
            )
            session.usage.papers_in_final_set = len(session.final_papers)

            if session.final_papers and session.stop_reason != StopReason.BUDGET_EXCEEDED:
                try:
                    if progress_callback:
                        await progress_callback.on_evidence_extraction_start(session_id)
                    await self._build_evidence_and_answer(session, progress_callback, session_id)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # Evidence/answer stage failure → fallback to abstracts
                    session.error = f"Evidence/answer stage failed: {exc}"
                    snippets = [
                        EvidenceSnippet(
                            paper_id=paper.stable_id,
                            paper_title=paper.title,
                            content=paper.abstract or "",
                            relevance_score=paper.relevance_score or 0.0,
                            citation=_EvidenceAdapter._citation(paper),
                            provider=paper.source,
                        )
                        for paper in session.final_papers
                        if paper.abstract
                    ]
                    session.evidence = snippets
                    session.answer = AnswerSummary(
                        answer="\n\n".join(
                            snippet.content for snippet in snippets[:3]
                        ),
                        evidence_used=len(snippets),
                        papers_cited=[snippet.paper_id for snippet in snippets],
                        citations=[
                            snippet.citation
                            for snippet in snippets
                            if snippet.citation is not None
                        ],
                        has_successful_answer=False,
                    )
                    if progress_callback:
                        await progress_callback.on_answer_synthesis_done(
                            session_id,
                            len(session.answer.answer) if session.answer else 0
                        )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            session.stop_reason = StopReason.ERROR
            session.error = str(exc)
        finally:
            self._sync_api_usage(session, api_baseline)
            session.completed_at = datetime.now(UTC)
            session.usage.total_duration_ms = int(
                (time.perf_counter() - started) * 1000
            )
        return session
