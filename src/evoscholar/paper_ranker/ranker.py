from __future__ import annotations

import logging
import math
import re
from collections import Counter
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Iterable

from .relevance import RelevanceTier

if TYPE_CHECKING:
    from evoscholar.iterative_search.models import AcademicPaper

logger = logging.getLogger(__name__)

_TOKEN_PATTERN = re.compile(r"[\w]+", flags=re.UNICODE)
_FACTOR_KEYS = ("relevance", "recency", "citation", "diversity", "combined")
_DEFAULT_WEIGHTS = {
    "relevance": 0.55,
    "recency": 0.15,
    "citation": 0.15,
    "diversity": 0.15,
}


def _tokens(text: str) -> list[str]:
    return [token.casefold() for token in _TOKEN_PATTERN.findall(text) if len(token) > 1]


def _lexical_relevance(query: str, paper: AcademicPaper) -> float:
    query_counts = Counter(_tokens(query))
    if not query_counts:
        return 0.0
    document_counts = Counter(_tokens(f"{paper.title or ''} {paper.abstract or ''}"))
    matched = sum(1 for token in query_counts if document_counts[token])
    coverage = matched / len(query_counts)
    saturation = sum(
        document_counts[token] / (document_counts[token] + 1.0)
        for token in query_counts
        if document_counts[token]
    ) / len(query_counts)
    return min(1.0, 0.75 * coverage + 0.25 * saturation)


def _cosine(left: Iterable[float], right: Iterable[float]) -> float:
    left_values = [float(value) for value in left]
    right_values = [float(value) for value in right]
    if len(left_values) != len(right_values) or not left_values:
        raise ValueError("embedding vectors must have equal non-zero dimensions")
    dot = sum(a * b for a, b in zip(left_values, right_values, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left_values))
    right_norm = math.sqrt(sum(value * value for value in right_values))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (left_norm * right_norm)))


def _research_settings(settings: Any) -> Any:
    return getattr(settings, "research", settings)


def _assign_scores(
    papers: list[AcademicPaper],
    relevance_scores: list[float],
    config: Any,
) -> None:
    partial_threshold = float(getattr(config, "partial_threshold", 0.5))
    high_threshold = float(getattr(config, "high_threshold", 0.75))
    weights = _DEFAULT_WEIGHTS | dict(getattr(config, "ranking_weights", {}) or {})
    current_year = datetime.now(UTC).year
    maximum_citations = max((paper.citation_count or 0 for paper in papers), default=0)
    field_counts = Counter(
        field.casefold() for paper in papers for field in paper.fields_of_study
    )

    for paper, relevance in zip(papers, relevance_scores, strict=True):
        recency = (
            0.0
            if paper.year is None
            else max(0.0, min(1.0, 1.0 - max(0, current_year - paper.year) / 20.0))
        )
        citation = (
            math.log1p(max(0, paper.citation_count or 0)) / math.log1p(maximum_citations)
            if maximum_citations > 0
            else 0.0
        )
        diversity = (
            sum(1.0 / field_counts[field.casefold()] for field in paper.fields_of_study)
            / len(paper.fields_of_study)
            if paper.fields_of_study
            else 0.0
        )
        factor_values = {
            "relevance": relevance,
            "recency": recency,
            "citation": citation,
            "diversity": diversity,
        }
        combined = sum(
            weights.get(name, 0.0) * value
            for name, value in factor_values.items()
        )
        weight_total = sum(
            max(0.0, weights.get(name, 0.0)) for name in _DEFAULT_WEIGHTS
        )
        combined = combined / weight_total if weight_total else relevance

        paper.relevance_score = float(relevance)
        paper.relevance_tier = (
            RelevanceTier.HIGH
            if relevance >= high_threshold
            else RelevanceTier.PARTIAL
            if relevance >= partial_threshold
            else RelevanceTier.LOW
        )
        paper.ranking_factors = {
            key: float(value)
            for key, value in {
                **factor_values,
                "combined": max(0.0, min(1.0, combined)),
            }.items()
        }


def score_papers(
    papers: list[AcademicPaper],
    query: str,
    settings: Any,
    embedding_model: Any,
) -> None:
    """Populate relevance tiers and ranking factors in-place.

    This synchronous entry point uses an embedding model when it exposes a
    synchronous batch method; asynchronous models are handled by the engine's
    ``ascore_papers`` helper, while this function remains offline-safe.
    """
    from .embedder import embed_texts_sync

    if not papers:
        return
    config = _research_settings(settings)
    try:
        if embedding_model is None:
            raise TypeError("no embedding model")
        document_texts = [
            f"{paper.title or ''}\n{paper.abstract or ''}" for paper in papers
        ]
        logger.debug("score_papers: embedding %d documents", len(document_texts))
        vectors = embed_texts_sync(embedding_model, [query, *document_texts])
        relevance_scores = [_cosine(vectors[0], vector) for vector in vectors[1:]]
        logger.info(
            "score_papers: done (embedding), papers=%d, method=embedding",
            len(papers),
        )
    except Exception as exc:
        logger.warning(
            "score_papers: embedding failed (%s), falling back to lexical scoring",
            exc,
        )
        relevance_scores = [_lexical_relevance(query, paper) for paper in papers]
        logger.info(
            "score_papers: done (lexical fallback), papers=%d",
            len(papers),
        )
    _assign_scores(papers, relevance_scores, config)


async def ascore_papers(
    papers: list[AcademicPaper],
    query: str,
    settings: Any,
    embedding_model: Any,
) -> None:
    """Async counterpart used when the configured embedding model is awaitable."""
    from .embedder import embed_texts_async

    if not papers:
        return
    config = _research_settings(settings)
    try:
        if embedding_model is None:
            raise TypeError("no embedding model")
        document_texts = [
            f"{paper.title or ''}\n{paper.abstract or ''}" for paper in papers
        ]
        logger.debug("ascore_papers: embedding %d documents", len(document_texts))
        vectors = await embed_texts_async(embedding_model, [query, *document_texts])
        relevance_scores = [_cosine(vectors[0], vector) for vector in vectors[1:]]
        logger.info(
            "ascore_papers: done (embedding), papers=%d, method=embedding",
            len(papers),
        )
    except Exception as exc:
        logger.warning(
            "ascore_papers: embedding failed (%s), falling back to lexical scoring",
            exc,
        )
        relevance_scores = [_lexical_relevance(query, paper) for paper in papers]
        logger.info(
            "ascore_papers: done (lexical fallback), papers=%d",
            len(papers),
        )
    _assign_scores(papers, relevance_scores, config)
