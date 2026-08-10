"""Lightning: 极简版答案合成器。

替代 paperqa 上游 `Docs.aget_evidence + Docs.aquery` 两步流程。
原流程是"向量检索 + LLM 重排 + 多 chunk 拼接"，对论文库场景非常合理，
但我们搜索场景仅有 abstract（无全文），向量化整个 abstract 反而是冗余。

Phase D 实现：
- `select_relevant_snippets`：每个 paper 由 LLM 直接判断是否相关 + 抽取相关片段
  （单次 LLM 调用 / paper，简单且高效）
- `synthesize_answer`：把所有相关 snippet 拼成 prompt，送给 LLM 写最终答案

设计原则：
- 仅依赖 `AcademicPaper`（iterative_search 模型），不依赖 lit_qa
- 提供 `LLMModel` 协议：`async def acomplete(messages) -> str` 即可（兼容 litellm）
- 进度通过 `progress_callback` 上报（可选）
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, Protocol, runtime_checkable

from ..iterative_search.models import AcademicPaper
from ..synthesis.models import AnswerSummary, EvidenceSnippet, UsageStats

logger = logging.getLogger(__name__)


@runtime_checkable
class LLMModel(Protocol):
    """Lightning 答案合成所需的最小 LLM 协议。

    只需 `acomplete(messages) -> str`（同步返回字符串结果），由调用方传
    `_TrackedLLMAdapter` 包装，自动累积 `UsageStats`。`acomplete` 可以是
    coroutine 也可以是同步 callable；本模块统一 `await` 等待。
    """

    name: str

    def acomplete(self, messages: Any, **kwargs: Any) -> Any: ...


ProgressFn = Callable[[str, dict[str, Any]], Awaitable[None] | None]


def _format_paper_for_snippet_extraction(paper: AcademicPaper) -> str:
    """把 paper 渲染成 LLM 友好的字符串（用于 snippet 抽取 prompt）。"""
    return (
        f"Title: {paper.title or paper.stable_id}\n"
        f"Authors: {', '.join(paper.authors) if paper.authors else 'Unknown'}\n"
        f"Year: {paper.year if paper.year else 'n.d.'}\n"
        f"DOI: {paper.doi or 'unknown'}\n"
        f"Abstract: {paper.abstract or '(no abstract available)'}\n"
    )


async def select_relevant_snippets(
    papers: Sequence[AcademicPaper],
    query: str,
    llm: LLMModel,
    *,
    progress_callback: ProgressFn | None = None,
) -> list[EvidenceSnippet]:
    """对每个 paper 调用一次 LLM，提取与 `query` 相关的 snippet。

    比 paperqa 上游的"向量检索 + LLM 重排"轻量得多 —— 因为：
    - 搜索场景只有 abstract，无全文，向量化 abstract 信息密度低
    - 单次 LLM 调用能同时判断相关性 + 抽取关键片段

    返回：仅包含 `relevance_score > 0` 的 snippet，按 score 降序。
    """
    snippets: list[EvidenceSnippet] = []
    for idx, paper in enumerate(papers):
        abstract = (paper.abstract or "").strip()
        if not abstract:
            continue

        if progress_callback:
            res = progress_callback(
                "evidence_extraction_progress",
                {"paper_index": idx, "paper_id": paper.stable_id, "total": len(papers)},
            )
            if res is not None:
                await res

        messages = [
            {
                "role": "system",
                "content": (
                    "You extract the most relevant evidence snippet from a paper's abstract"
                    " given a user query. Reply ONLY with a JSON object of the form:\n"
                    '  {"relevant": bool, "score": float in [0, 1],'
                    '   "snippet": str, "rationale": str}.\n'
                    "If the abstract is irrelevant, set relevant=false and score=0."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Query: {query}\n\n"
                    f"Paper:\n{_format_paper_for_snippet_extraction(paper)}"
                ),
            },
        ]
        try:
            raw = await llm.acomplete(messages)
        except Exception as exc:  # noqa: BLE001
            logger.warning("snippet extraction failed for %s: %s", paper.stable_id, exc)
            continue

        try:
            payload = json.loads(_extract_json(raw))
        except (ValueError, json.JSONDecodeError) as exc:
            logger.debug(
                "could not parse snippet JSON for %s: %s; raw=%r",
                paper.stable_id,
                exc,
                raw[:200],
            )
            continue

        if not payload.get("relevant"):
            continue

        snippet = EvidenceSnippet(
            paper_id=paper.stable_id,
            paper_title=paper.title,
            content=payload.get("snippet") or abstract,
            relevance_score=max(0.0, min(1.0, float(payload.get("score") or 0.0))),
            citation=_format_citation(paper),
            provider=paper.source,
        )
        if snippet.relevance_score > 0:
            snippets.append(snippet)

    snippets.sort(key=lambda s: s.relevance_score, reverse=True)
    return snippets


async def synthesize_answer(
    query: str,
    snippets: Sequence[EvidenceSnippet],
    llm: LLMModel,
    *,
    progress_callback: ProgressFn | None = None,
) -> AnswerSummary:
    """拼接 snippet → 喂给 LLM → 输出最终答案。

    自动收集所有 snippet 的 `paper_id` 作为 `papers_cited`，拼接
    `citation` 作为 `citations`。
    """
    if not snippets:
        return AnswerSummary(
            answer="I could not find any relevant evidence in the searched papers.",
            papers_cited=[],
            citations=[],
            evidence_used=0,
            has_successful_answer=False,
        )

    context_chunks: list[str] = []
    for idx, snippet in enumerate(snippets, start=1):
        citation = snippet.citation or f"[{snippet.paper_title or snippet.paper_id}]"
        context_chunks.append(
            f"[{idx}] {citation}\n{snippet.content.strip()}"
        )
    context = "\n\n".join(context_chunks)

    if progress_callback:
        res = progress_callback(
            "answer_synthesis_start",
            {"snippets": len(snippets)},
        )
        if res is not None:
            await res

    messages = [
        {
            "role": "system",
            "content": (
                "You are a research assistant. Given a query and a set of"
                " numbered evidence snippets, write a concise answer that synthesizes"
                " the evidence. Cite sources inline using [1], [2], etc., matching the"
                " numbering of the snippets. If the evidence is insufficient, say so."
            ),
        },
        {
            "role": "user",
            "content": f"Query: {query}\n\nEvidence:\n{context}",
        },
    ]
    try:
        answer_text = await llm.acomplete(messages)
    except Exception as exc:  # noqa: BLE001
        logger.error("answer synthesis failed: %s", exc, exc_info=True)
        return AnswerSummary(
            answer=f"Answer synthesis failed: {exc}",
            papers_cited=[],
            citations=[],
            evidence_used=len(snippets),
            has_successful_answer=False,
        )

    if progress_callback:
        res = progress_callback(
            "answer_synthesis_done",
            {"length": len(answer_text)},
        )
        if res is not None:
            await res

    cited_ids = list(dict.fromkeys(snippet.paper_id for snippet in snippets))
    citations = list(dict.fromkeys(snippet.citation or "" for snippet in snippets if snippet.citation))
    return AnswerSummary(
        answer=answer_text,
        subqueries_covered=[query],
        evidence_used=len(snippets),
        papers_cited=cited_ids,
        citations=citations,
        raw_answer=answer_text,
        has_successful_answer=True,
    )


def _format_citation(paper: AcademicPaper) -> str:
    authors = ", ".join(paper.authors[:3]) if paper.authors else "Unknown authors"
    year = str(paper.year) if paper.year else "n.d."
    return f"{authors}. {paper.title or paper.stable_id}. {year}."


def _extract_json(raw: str) -> str:
    """从 LLM raw 输出中抓取第一个 JSON 对象。"""
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"no JSON object found in: {raw!r}")
    return raw[start : end + 1]


__all__ = [
    "LLMModel",
    "ProgressFn",
    "select_relevant_snippets",
    "synthesize_answer",
    "UsageStats",
]
