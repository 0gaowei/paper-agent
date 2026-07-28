"""FastAPI dependency injection for shared application state.

This module provides dependency functions that inject shared state (repository,
publisher, engine, tasks) into route handlers without requiring them to import
the app module directly, thus avoiding circular imports.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from fastapi import Request

if TYPE_CHECKING:
    from paperqa.server.events import EventPublisher
    from paperqa.server.repository import JSONFileRepository


def get_repository(request: Request) -> "JSONFileRepository":
    """Inject the JSON file repository from app state."""
    return request.app.state.repository  # type: ignore[attr-defined,return-value]


def get_publisher(request: Request) -> "EventPublisher":
    """Inject the SSE event publisher from app state."""
    return request.app.state.publisher  # type: ignore[attr-defined,return-value]


def get_engine(request: Request):
    """Inject the ResearchEngine from app state (may be None if unavailable)."""
    return getattr(request.app.state, "engine", None)


def get_tasks(request: Request) -> dict[str, asyncio.Task[None]]:
    """Inject the background tasks dict from app state."""
    return getattr(request.app.state, "tasks", {})
