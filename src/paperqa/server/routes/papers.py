"""Paper detail and graph routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from paperqa.server.schemas import AcademicPaper, PaperSource, RelevanceTier

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/papers", tags=["papers"])


# In-memory paper cache populated by session events (mirrors what the engine emits)
_paper_cache: dict[str, AcademicPaper] = {}


def register_paper(paper: AcademicPaper) -> None:
    """Register a paper in the in-memory cache (called by session event handlers)."""
    _paper_cache[paper.id] = paper


@router.get(
    "/{paper_id}",
    response_model=AcademicPaper,
    summary="Get paper details",
)
async def get_paper(paper_id: str) -> AcademicPaper:
    """Return details for a paper, looking it up in the session cache.

    If the paper is not in the cache, returns a 404.
    """
    if paper_id in _paper_cache:
        return _paper_cache[paper_id]

    # Fallback: try to construct a minimal response from stored sessions
    from paperqa.server.app import app

    repository = app.state.repository
    sessions = await repository.list_(limit=100)
    for session in sessions:
        if paper_id in session.papers:
            return session.papers[paper_id]

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Paper {paper_id!r} not found.",
    )


@router.get(
    "/{paper_id}/graph",
    response_model=dict,
    summary="Get paper citation graph",
)
async def get_paper_graph(paper_id: str) -> dict:
    """Return the citation graph for a specific paper.

    The graph includes the paper itself and its references/citations
    that were discovered during the session.
    """
    from paperqa.server.app import app

    repository = app.state.repository

    paper = None
    if paper_id in _paper_cache:
        paper = _paper_cache[paper_id]

    if paper is None:
        sessions = await repository.list_(limit=100)
        for session in sessions:
            if paper_id in session.papers:
                paper = session.papers[paper_id]
                break

    if paper is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper {paper_id!r} not found.",
        )

    # Build graph nodes and edges
    nodes = [
        {
            "id": paper.id,
            "title": paper.title,
            "year": paper.year,
            "relevance_tier": paper.relevance_tier.value,
            "is_root": True,
        }
    ]
    edges: list[dict] = []

    for ref_id in paper.referenced_works:
        nodes.append({
            "id": ref_id,
            "title": f"Referenced work: {ref_id}",
            "year": None,
            "relevance_tier": RelevanceTier.IRRELEVANT.value,
            "is_root": False,
        })
        edges.append({"source": paper.id, "target": ref_id, "type": "references"})

    for citing_id in paper.citing_works:
        nodes.append({
            "id": citing_id,
            "title": f"Citing work: {citing_id}",
            "year": None,
            "relevance_tier": RelevanceTier.IRRELEVANT.value,
            "is_root": False,
        })
        edges.append({"source": citing_id, "target": paper.id, "type": "cited_by"})

    return {"nodes": nodes, "edges": edges}
