"""Evidence and answer building for synthesis.

This module contains the core logic for building evidence snippets from
papers and synthesizing final answers.
"""

from __future__ import annotations

import inspect
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, TypeVar

from lmi import LLMResult

from .models import AnswerSummary, EvidenceSnippet, UsageStats

if TYPE_CHECKING:
    from evoscholar.iterative_search.models import AcademicPaper
    from evoscholar.iterative_search.callbacks import ResearchProgressCallback


_T = TypeVar("_T")


def _response_text(response: Any) -> str:
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


def _usage_value(usage: Any, *names: str) -> int:
    for name in names:
        value = usage.get(name) if isinstance(usage, dict) else getattr(usage, name, None)
        if value is not None:
            return int(value)
    return 0


class _TrackedLLMAdapter:
    """Expose PaperQA's call_single API around either supported LLM interface."""

    def __init__(self, delegate: Any, usage: UsageStats) -> None:
        self.delegate = delegate
        self.usage = usage

    async def call_single(self, messages: Any, **kwargs: Any) -> LLMResult:
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

        raw_usage = (
            response.get("usage") if isinstance(response, dict) else getattr(response, "usage", None)
        )
        prompt_tokens = _usage_value(raw_usage, "prompt_tokens", "input_tokens")
        completion_tokens = _usage_value(
            raw_usage, "completion_tokens", "output_tokens"
        )
        hidden = getattr(response, "_hidden_params", {}) or {}
        cost = float(hidden.get("response_cost") or 0.0)
        self.usage.llm_prompt_tokens += prompt_tokens
        self.usage.llm_completion_tokens += completion_tokens
        self.usage.llm_cost_usd += cost
        return LLMResult(
            model=str(getattr(self.delegate, "name", "research-llm")),
            text=_response_text(response),
            prompt_count=prompt_tokens,
            completion_count=completion_tokens,
            cost=cost,
        )


class _EvidenceAdapter:
    """Inject paper abstracts into Docs without touching its file/PDF ingestion path."""

    def __init__(self, papers: Sequence["AcademicPaper"]) -> None:
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
    def _citation(paper: "AcademicPaper") -> str:
        authors = ", ".join(paper.authors[:3]) or "Unknown authors"
        year = str(paper.year) if paper.year else "n.d."
        return f"{authors}. {paper.title or paper.stable_id}. {year}."

    async def aget_evidence(self, *args: Any, **kwargs: Any) -> Any:
        return await self.docs.aget_evidence(*args, **kwargs)

    async def aquery(self, *args: Any, **kwargs: Any) -> Any:
        return await self.docs.aquery(*args, **kwargs)


async def build_evidence_and_answer(
    papers: list["AcademicPaper"],
    query: str,
    settings: Any,
    llm_model: Any,
    embedding_model: Any | None,
    session_id: str | None = None,
    progress_callback: "ResearchProgressCallback | None" = None,
) -> tuple[list[EvidenceSnippet], AnswerSummary | None]:
    """Build evidence snippets and synthesize answer from papers.

    Args:
        papers: List of papers to extract evidence from.
        query: The original research query.
        settings: Settings for evidence extraction.
        llm_model: LLM model for synthesis.
        embedding_model: Embedding model for relevance scoring.
        session_id: Optional session ID for callbacks.
        progress_callback: Optional progress callback.

    Returns:
        Tuple of (evidence snippets, answer summary).
    """
    if not papers:
        return [], None

    evidence_papers = [paper for paper in papers if paper.abstract]
    if not evidence_papers:
        return [], None

    adapter = _EvidenceAdapter(evidence_papers)
    evidence_settings = settings.model_copy(deep=True)
    evidence_settings.answer.evidence_retrieval = False
    evidence_settings.answer.evidence_skip_summary = True
    evidence_settings.answer.get_evidence_if_no_contexts = False
    usage = UsageStats()
    tracked_llm = _TrackedLLMAdapter(llm_model, usage)

    pqa_session = await adapter.aget_evidence(
        query,
        settings=evidence_settings,
        embedding_model=embedding_model,
        summary_llm_model=tracked_llm,
    )
    evidence = [
        EvidenceSnippet(
            paper_id=str(context.text.doc.dockey),
            paper_title=getattr(context.text.doc, "title", None),
            content=context.context,
            relevance_score=max(0.0, min(1.0, context.score / 10.0)),
            subquery_addressed=context.question,
            citation=context.text.doc.citation,
            provider=(
                adapter.paper_by_id.get(str(context.text.doc.dockey)).source
                if adapter.paper_by_id.get(str(context.text.doc.dockey))
                else "unknown"
            ),
        )
        for context in pqa_session.contexts
    ]
    if progress_callback:
        await progress_callback.on_evidence_extraction_done(
            session_id, len(evidence)
        )
        await progress_callback.on_answer_synthesis_start(
            session_id, "Synthesizing answer from evidence..."
        )
    answered = await adapter.aquery(
        pqa_session,
        settings=evidence_settings,
        llm_model=tracked_llm,
        summary_llm_model=tracked_llm,
        embedding_model=embedding_model,
    )
    cited_ids = list(
        dict.fromkeys(str(context.text.doc.dockey) for context in answered.contexts)
    )
    citations = list(
        dict.fromkeys(context.text.doc.citation for context in answered.contexts)
    )
    answer = AnswerSummary(
        answer=answered.answer or answered.raw_answer,
        subqueries_covered=[query],
        evidence_used=len(evidence),
        papers_cited=cited_ids,
        citations=citations,
        raw_answer=answered.raw_answer,
        has_successful_answer=answered.has_successful_answer,
    )
    if progress_callback:
        await progress_callback.on_answer_synthesis_done(
            session_id, len(answer.answer) if answer else 0
        )
    return evidence, answer
