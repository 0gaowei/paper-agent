from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from evoscholar.research.models import AcademicPaper

_TOKEN_PATTERN = re.compile(r"[\w]+", flags=re.UNICODE)


def _tokens(text: str) -> list[str]:
    return [token.casefold() for token in _TOKEN_PATTERN.findall(text) if len(token) > 1]


def _paper_similarity(left: AcademicPaper, right: AcademicPaper) -> float:
    """Calculate similarity between two papers based on fields and title."""
    left_fields = {field.casefold() for field in left.fields_of_study}
    right_fields = {field.casefold() for field in right.fields_of_study}
    field_similarity = (
        len(left_fields & right_fields) / len(left_fields | right_fields)
        if left_fields or right_fields
        else 0.0
    )
    left_tokens = set(_tokens(left.title or ""))
    right_tokens = set(_tokens(right.title or ""))
    title_similarity = (
        len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
        if left_tokens or right_tokens
        else 0.0
    )
    return max(field_similarity, title_similarity)


def rank_with_mmr(
    papers: list[AcademicPaper], k: int, lambda_mult: float = 0.5
) -> list[AcademicPaper]:
    """Select high-scoring papers while penalizing topical redundancy."""
    if k <= 0 or not papers:
        return []
    lambda_mult = max(0.0, min(1.0, lambda_mult))
    candidates = sorted(
        papers,
        key=lambda paper: (
            paper.ranking_factors.get("combined", paper.relevance_score or 0.0),
            paper.relevance_score or 0.0,
            paper.stable_id,
        ),
        reverse=True,
    )
    selected: list[AcademicPaper] = []
    while candidates and len(selected) < min(k, len(papers)):
        if not selected:
            selected.append(candidates.pop(0))
            continue
        best = max(
            candidates,
            key=lambda paper: (
                lambda_mult
                * paper.ranking_factors.get("combined", paper.relevance_score or 0.0)
                - (1.0 - lambda_mult)
                * max(_paper_similarity(paper, chosen) for chosen in selected),
                paper.relevance_score or 0.0,
                paper.stable_id,
            ),
        )
        selected.append(best)
        candidates.remove(best)
    return selected
