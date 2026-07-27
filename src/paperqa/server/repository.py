"""JSON file-based repository for research sessions.

Sessions are stored atomically under PQA_HOME/research/sessions/{id}.json
using a write-to-temp + rename pattern for crash-recovery safety.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import anyio

if TYPE_CHECKING:
    from paperqa.server.schemas import ResearchSession

logger = logging.getLogger(__name__)


def _default_sessions_dir() -> anyio.Path:
    """Return the default sessions directory under PQA_HOME."""
    from paperqa.utils import pqa_directory

    return anyio.Path(pqa_directory("sessions"))


class JSONFileRepository:
    """Atomic JSON file storage for research sessions.

    Guarantees crash-recovery safety via:
    1. Write to a temporary `.tmp` file in the same directory
    2. Rename the temp file over the target (atomic on POSIX)
    3. On any error, clean up the temp file
    """

    def __init__(self, sessions_dir: anyio.Path | str | None = None) -> None:
        """Initialize the repository.

        Args:
            sessions_dir: Directory for session JSON files.
                Defaults to PQA_HOME/research/sessions.
        """
        self._sessions_dir = (
            anyio.Path(sessions_dir) if sessions_dir is not None else _default_sessions_dir()
        )

    async def _ensure_dir(self) -> None:
        """Create the sessions directory if it does not exist."""
        if not await self._sessions_dir.exists():
            await self._sessions_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> anyio.Path:
        """Return the path for a session file."""
        return self._sessions_dir / f"{session_id}.json"

    async def save(self, session: "ResearchSession") -> None:
        """Atomically write a session to disk.

        Args:
            session: The research session to persist.
        """
        await self._ensure_dir()
        target = self._session_path(session.id)
        tmp = target.with_suffix(".tmp")

        try:
            # Serialize with UTC-aware ISO format for timestamps
            content = session.model_dump_json()
            await tmp.write_text(content, encoding="utf-8")
            await tmp.replace(target)
        except Exception:
            # Clean up temp file on failure
            if await tmp.exists():
                await tmp.unlink(missing_ok=True)
            raise

    async def get(self, session_id: str) -> "ResearchSession | None":
        """Load a session from disk.

        Args:
            session_id: The session ID.

        Returns:
            The session if found, None otherwise.
        """
        from paperqa.server.schemas import ResearchSession

        path = self._session_path(session_id)
        if not await path.exists():
            return None
        try:
            content = await path.read_text(encoding="utf-8")
            return ResearchSession.model_validate_json(content)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load session %s: %s", session_id, exc)
            return None

    async def delete(self, session_id: str) -> bool:
        """Delete a session file.

        Args:
            session_id: The session ID.

        Returns:
            True if the file was deleted, False if it did not exist.
        """
        path = self._session_path(session_id)
        if await path.exists():
            await path.unlink()
            return True
        return False

    async def list_(self, limit: int = 100) -> list["ResearchSession"]:
        """List sessions, most recently updated first.

        Args:
            limit: Maximum number of sessions to return.

        Returns:
            List of sessions, ordered by updated_at descending.
        """
        from paperqa.server.schemas import ResearchSession

        await self._ensure_dir()
        sessions: list[ResearchSession] = []

        try:
            async for path in self._sessions_dir.iterdir():
                if path.suffix != ".json":
                    continue
                try:
                    content = await path.read_text(encoding="utf-8")
                    session = ResearchSession.model_validate_json(content)
                    sessions.append(session)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Skipping corrupted session file %s: %s", path, exc)
        except FileNotFoundError:
            pass  # Directory does not exist yet

        def _sort_key(s: "ResearchSession") -> datetime:
            ts = s.updated_at
            if ts.tzinfo is None:
                return ts.replace(tzinfo=UTC)
            return ts

        sessions.sort(key=_sort_key, reverse=True)
        return sessions[:limit]

    async def exists(self, session_id: str) -> bool:
        """Check if a session exists on disk."""
        return await self._session_path(session_id).exists()
