"""证据抽取 + 答案合成（搜索场景极简版）。

Phase D 重构后，本模块仅承载对 `lightning.answer_builder` 的薄包装。
原 `paperqa.Docs.aget_evidence + Docs.aquery` 的"向量检索 + LLM 重排 + 多
chunk 拼接"全套被 `select_relevant_snippets + synthesize_answer` 替代。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import TYPE_CHECKING, Any

from lmi import LLMResult

from ..lightning.answer_builder import (
    ProgressFn,
    select_relevant_snippets,
    synthesize_answer,
)
from .models import AnswerSummary, EvidenceSnippet, UsageStats

if TYPE_CHECKING:
    from ..iterative_search.models import AcademicPaper
    from ..iterative_search.callbacks import ResearchProgressCallback


def _normalize_messages(messages: Any) -> Any:
    """Convert raw dict messages into ``aviary.Message`` instances.

    LMI's ``acompletion`` path calls ``m.model_dump(by_alias=True)`` on each
    message, so plain ``{"role": ..., "content": ...}`` dicts raise
    ``AttributeError: 'dict' object has no attribute 'model_dump'``. Mirrors
    the conversion done in ``query_understanding.analyze._call_llm``.
    """
    from aviary.core import Message

    if not isinstance(messages, (list, tuple)):
        return messages
    normalized: list[Any] = []
    needs_wrap = False
    for message in messages:
        if isinstance(message, dict):
            needs_wrap = True
            normalized.append(
                Message(
                    role=message.get("role", "user"),
                    content=message.get("content", ""),
                )
            )
        else:
            normalized.append(message)
    return normalized if needs_wrap else messages


def _tracked_llm(
    delegate: Any, usage: UsageStats
) -> Any:
    """Wrap an LLM so each `acomplete` call increments `UsageStats`.

    Mirrors the original `_TrackedLLMAdapter` semantics but keeps things
    simple: we only forward kwargs and extract token counts from
    `LLMResult` / dict responses.
    """

    class _Adapter:
        __slots__ = ("delegate", "usage")

        def __init__(self) -> None:
            self.delegate = delegate
            self.usage = usage

        async def acomplete(self, messages: Any, **kwargs: Any) -> Any:
            import inspect

            from lmi import LLMResult

            normalized = _normalize_messages(messages)

            if hasattr(self.delegate, "acomplete"):
                response = self.delegate.acomplete(normalized, **kwargs)
                response = (
                    await response if inspect.isawaitable(response) else response
                )
            elif hasattr(self.delegate, "call_single"):
                response = self.delegate.call_single(messages=normalized, **kwargs)
                response = (
                    await response if inspect.isawaitable(response) else response
                )
            else:
                raise TypeError("LLM model must provide acomplete() or call_single()")

            self.usage.llm_calls += 1
            if isinstance(response, LLMResult):
                self.usage.llm_prompt_tokens += response.prompt_count or 0
                self.usage.llm_completion_tokens += response.completion_count or 0
                self.usage.llm_cost_usd += response.cost
            elif isinstance(response, dict):
                raw_usage = response.get("usage") or {}
                if isinstance(raw_usage, dict):
                    self.usage.llm_prompt_tokens += int(
                        raw_usage.get("prompt_tokens")
                        or raw_usage.get("input_tokens")
                        or 0
                    )
                    self.usage.llm_completion_tokens += int(
                        raw_usage.get("completion_tokens")
                        or raw_usage.get("output_tokens")
                        or 0
                    )
                hidden = response.get("_hidden_params") or {}
                self.usage.llm_cost_usd += float(hidden.get("response_cost") or 0.0)
            return self._extract_text(response)

        def _extract_text(self, response: Any) -> str:
            if isinstance(response, str):
                return response
            if isinstance(response, LLMResult):
                return response.text or ""
            if isinstance(response, dict):
                content = response.get("content")
                if isinstance(content, str):
                    return content
                choices = response.get("choices") or []
                if choices:
                    message = choices[0].get("message") or {}
                    if isinstance(message, dict):
                        c = message.get("content")
                        if isinstance(c, str):
                            return c
            text = getattr(response, "text", None)
            if isinstance(text, str):
                return text
            choices = getattr(response, "choices", None) or []
            if choices:
                c = getattr(getattr(choices[0], "message", None), "content", None)
                if isinstance(c, str):
                    return c
            return str(response)

    return _Adapter()


def _to_progress_callback(
    cb: "ResearchProgressCallback | None", session_id: str | None
) -> ProgressFn | None:
    if cb is None:
        return None

    async def _emit(stage: str, payload: dict[str, Any]) -> None:
        if stage == "evidence_extraction_progress":
            await cb.on_evidence_extraction_start(session_id, payload.get("total", 0))
        elif stage == "answer_synthesis_start":
            await cb.on_answer_synthesis_start(session_id, "Synthesizing answer...")
        elif stage == "answer_synthesis_done":
            await cb.on_answer_synthesis_done(session_id, payload.get("length", 0))

    return _emit


async def build_evidence_and_answer(
    papers: list["AcademicPaper"],
    query: str,
    settings: Any,
    llm_model: Any,
    embedding_model: Any | None,
    session_id: str | None = None,
    progress_callback: "ResearchProgressCallback | None" = None,
    usage: UsageStats | None = None,
) -> tuple[list[EvidenceSnippet], AnswerSummary | None]:
    """Build evidence snippets and synthesize answer from papers.

    Args:
        papers: List of papers to extract evidence from.
        query: The original research query.
        settings: Settings (kept for ABI compatibility; ignored in lightning path).
        llm_model: LLM model for synthesis.
        embedding_model: Embedding model (ignored — kept for ABI compatibility).
        session_id: Optional session ID for progress callbacks.
        progress_callback: Optional progress callback.
        usage: Optional UsageStats instance. When provided (e.g. session.usage),
            token counts and costs from evidence extraction and answer synthesis
            are accumulated into it so they are preserved after the call returns.

    Returns:
        Tuple of (evidence snippets, answer summary).
    """
    del embedding_model  # unused in lightning path; ABZ compat only

    if not papers:
        return [], None

    evidence_papers = [paper for paper in papers if paper.abstract]
    if not evidence_papers:
        return [], None

    _usage = usage if usage is not None else UsageStats()
    tracked_llm = _tracked_llm(llm_model, _usage)
    progress_fn = _to_progress_callback(progress_callback, session_id)

    evidence = await select_relevant_snippets(
        evidence_papers,
        query,
        tracked_llm,
        progress_callback=progress_fn,
    )
    if not evidence:
        return [], None

    if progress_callback is not None:
        await progress_callback.on_evidence_extraction_done(session_id, len(evidence))
        await progress_callback.on_answer_synthesis_start(
            session_id, "Synthesizing answer..."
        )

    answer = await synthesize_answer(
        query,
        evidence,
        tracked_llm,
        progress_callback=progress_fn,
    )

    if progress_callback is not None:
        await progress_callback.on_answer_synthesis_done(
            session_id, len(answer.answer)
        )
    return evidence, answer
