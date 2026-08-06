"""Graph routes for session search tree and citation expansion visualization."""


from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from evoscholar.server.dependencies import get_repository
from evoscholar.server.schemas import RelevanceTier

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["graph"])


@router.get(
    "/{session_id}/graph",
    response_model=dict,
    summary="Get session search tree graph",
)
async def get_session_graph(
    session_id: str,
    repository=Depends(get_repository),
) -> dict:
    """Return the search tree graph for a session.

    The graph shows:
    - Root node: the original query
    - Sub-query nodes per round
    - Paper nodes discovered at each round
    - Citation expansion edges
    """
    session = await repository.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id!r} not found.",
        )

    nodes: list[dict] = []
    edges: list[dict] = []
    node_ids: set[str] = set()

    # Root: query
    root_id = f"query:{session.id}"
    nodes.append({
        "id": root_id,
        "label": session.query,
        "type": "query",
        "year": None,
        "relevance_tier": None,
        "is_root": True,
    })
    node_ids.add(root_id)

    # Sub-query nodes per round
    for sq in session.subqueries:
        sq_id = f"subquery:{sq.text[:40]}:r{sq.round}"
        if sq_id not in node_ids:
            nodes.append({
                "id": sq_id,
                "label": sq.text,
                "type": "subquery",
                "round": sq.round,
                "year": None,
                "relevance_tier": None,
                "is_root": False,
            })
            node_ids.add(sq_id)
        # Edge: query -> subquery
        edges.append({
            "source": root_id,
            "target": sq_id,
            "type": "spawned",
            "round": sq.round,
        })

    # Paper nodes
    for paper_id, paper in session.papers.items():
        if paper_id in node_ids:
            continue
        nodes.append({
            "id": paper_id,
            "label": paper.title,
            "type": "paper",
            "year": paper.year,
            "relevance_tier": paper.relevance_tier.value,
            "source": paper.source.value if paper.source else None,
            "is_root": False,
        })
        node_ids.add(paper_id)
        # Edge: subquery -> paper (best effort, attach to matching round)
        # Use paper.round (0-indexed) to find matching subquery
        paper_round = getattr(paper, 'round', None)
        if paper_round is not None:
            matching_sq = next(
                (sq for sq in reversed(session.subqueries) if sq.round == paper_round),
                None,
            )
            if matching_sq:
                sq_node = f"subquery:{matching_sq.text[:40]}:r{matching_sq.round}"
                if sq_node in node_ids:
                    edges.append({
                        "source": sq_node,
                        "target": paper_id,
                        "type": "found",
                        "round": matching_sq.round,
                    })

    # Citation expansion edges
    for paper_id, paper in session.papers.items():
        for ref_id in paper.referenced_works:
            if ref_id in session.papers or ref_id in node_ids:
                edges.append({
                    "source": paper_id,
                    "target": ref_id,
                    "type": "citation_expansion",
                })

    return {
        "nodes": nodes,
        "edges": edges,
        "query": session.query,
        "rounds": session.rounds,
    }
