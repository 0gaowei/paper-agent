"""Settings routes for reading/updating researcher configuration.

These routes are a **thin wrapper** over the aggregated ``Settings``
instance stored on ``app.state.settings``. The server no longer keeps
its own parallel dict of researcher overrides; instead it reads/writes
the canonical ``Settings`` and lets Pydantic validate the merge.

API keys are kept out of the wire format: ``Settings.llm_api_key`` is
declared with ``exclude=True`` in the underlying settings model, and
we also guard the server-side key storage so the value is never
serialized back to clients.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from evoscholar.configs import Settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["settings"])


# ---------------------------------------------------------------------------
# Wire schema (defined before router so decorators can use it unquoted)
# ---------------------------------------------------------------------------


class SettingsPayload(BaseModel):
    """Settings read/write via the API (never exposes API keys)."""

    researcher_llm: str | None = Field(
        default=None,
        description="LLM model used for research.",
    )
    researcher_llm_config: dict[str, Any] | None = Field(
        default=None,
        description="LLM configuration (no API keys).",
    )
    summary_llm: str | None = Field(
        default=None,
        description="LLM model used for summarization.",
    )
    # API configuration fields (stored server-side, returned without exposing secrets)
    llm_api_key: str | None = Field(
        default=None,
        description="LLM API key (stored server-side, never returned to client).",
    )
    llm_base_url: str | None = Field(
        default=None,
        description="LLM base URL for custom endpoints.",
    )
    llm_provider: str | None = Field(
        default=None,
        description="LLM provider (e.g., openai, anthropic).",
    )
    max_rounds: int | None = Field(
        default=None, ge=1, description="Maximum research rounds."
    )
    candidates_per_round: int | None = Field(
        default=None, ge=1, description="Candidates per round."
    )
    citation_expansion_limit: int | None = Field(
        default=None, ge=0, description="Max citation expansions per round."
    )
    high_relevance_threshold: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="High relevance threshold (0–1).",
    )
    partial_relevance_threshold: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="Partial relevance threshold (0–1).",
    )

    # Key configuration status — always read-only booleans, never keys
    llm_configured: bool = Field(
        default=False,
        description="Whether an LLM API key is configured.",
    )
    openalex_configured: bool = Field(
        default=False,
        description="Whether an OpenAlex API key is configured.",
    )


# ---------------------------------------------------------------------------
# Module state
# ---------------------------------------------------------------------------


# Server-side API key storage (never exposed to client)
_llm_api_key: str | None = None
_llm_base_url: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_key(env_var: str) -> bool:
    """Return True if the environment variable is set to a non-empty value."""
    val = os.environ.get(env_var, "")
    return bool(val)


def _infer_provider(llm: str) -> str:
    """Map an LLM string to a coarse provider label.

    Kept as a helper so the wire format remains stable for the
    settings page even when ``Settings.llm`` is free-form.
    """
    llm_lower = llm.lower()
    if llm_lower.startswith("gpt-") or llm_lower.startswith("openai"):
        return "openai"
    if llm_lower.startswith("claude") or llm_lower.startswith("anthropic"):
        return "anthropic"
    if llm_lower.startswith("gemini"):
        return "google"
    return "openai"  # safe default


def _sanitize_for_response(s: Settings) -> SettingsPayload:
    """Build a wire-format representation that hides secrets.

    Uses ``model_dump(exclude=...)`` to strip the API key, which is
    declared ``exclude=True`` on ``Settings.llm_api_key`` anyway.
    """
    return SettingsPayload(
        researcher_llm=s.llm,
        researcher_llm_config=s.llm_config,
        summary_llm=s.summary_llm,
        llm_api_key=None,  # never returned
        llm_base_url=s.llm_base_url,
        llm_provider=_infer_provider(s.llm),
        max_rounds=s.research.max_rounds,
        candidates_per_round=s.research.max_candidates_per_round,
        citation_expansion_limit=s.research.max_references_per_node,
        high_relevance_threshold=s.research.high_threshold,
        partial_relevance_threshold=s.research.partial_threshold,
        llm_configured=_check_key("OPENAI_API_KEY")
        or _check_key("ANTHROPIC_API_KEY")
        or _check_key("LITELLM_API_KEY")
        or _llm_api_key is not None,
        openalex_configured=_check_key("OPENTALEX_API_KEY"),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


def _get_or_init_settings(request: Request) -> Settings:
    """Return ``app.state.settings`` or lazily initialize it.

    The lifespan handler is responsible for initializing settings on
    startup. If it failed (e.g., the environment lacks the optional
    PDF parser packages), we still want the routes to respond with
    a sensible default rather than 500ing.
    """
    settings = getattr(request.app.state, "settings", None)
    if settings is not None:
        return settings
    try:
        settings = Settings()
        request.app.state.settings = settings  # type: ignore[attr-defined]
        logger.info("Lazy-initialized Settings on first request.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not initialize Settings: %s", exc)
        raise
    return settings


@router.get(
    "",
    response_model=SettingsPayload,
    summary="Get researcher settings",
)
async def get_settings(request: Request) -> SettingsPayload:
    """Return the current researcher settings with API key status flags.

    API keys are NEVER returned — only boolean ``configured`` flags.
    """
    settings: Settings = _get_or_init_settings(request)
    return _sanitize_for_response(settings)


@router.put(
    "",
    response_model=SettingsPayload,
    summary="Update researcher settings",
)
async def update_settings(
    payload: SettingsPayload,
    request: Request,
) -> SettingsPayload:
    """Update researcher settings including API key and base URL.

    This endpoint accepts API keys in the payload but stores them
    server-side and never returns them to the client.
    """
    global _llm_api_key, _llm_base_url

    current: Settings = _get_or_init_settings(request)
    updates: dict[str, object] = {}

    # Top-level LLM fields
    if payload.researcher_llm is not None:
        updates["llm"] = payload.researcher_llm
    if payload.summary_llm is not None:
        updates["summary_llm"] = payload.summary_llm
    if payload.researcher_llm_config is not None:
        updates["llm_config"] = payload.researcher_llm_config

    # ResearchSettings fields
    research_updates: dict[str, object] = {}
    if payload.max_rounds is not None:
        research_updates["max_rounds"] = payload.max_rounds
    if payload.candidates_per_round is not None:
        research_updates["max_candidates_per_round"] = payload.candidates_per_round
    if payload.citation_expansion_limit is not None:
        research_updates["max_references_per_node"] = payload.citation_expansion_limit
    if payload.high_relevance_threshold is not None:
        research_updates["high_threshold"] = payload.high_relevance_threshold
    if payload.partial_relevance_threshold is not None:
        research_updates["partial_threshold"] = payload.partial_relevance_threshold
    if research_updates:
        # Merge into current.research via model_copy(update=...)
        current_research = current.research.model_copy(update=research_updates)
        updates["research"] = current_research

    # Apply all updates atomically
    new_settings = current.model_copy(update=updates)
    request.app.state.settings = new_settings  # type: ignore[attr-defined]

    # Store API key and base URL server-side (not on Settings to avoid exposure)
    credentials_changed = False
    if payload.llm_api_key is not None:
        _llm_api_key = payload.llm_api_key
        os.environ["LLM_API_KEY"] = payload.llm_api_key
        credentials_changed = True
    if payload.llm_base_url is not None:
        _llm_base_url = payload.llm_base_url
        os.environ["LLM_BASE_URL"] = payload.llm_base_url
        # Also reflect into the live Settings
        new_settings = new_settings.model_copy(
            update={"llm_base_url": payload.llm_base_url}
        )
        request.app.state.settings = new_settings  # type: ignore[attr-defined]
        credentials_changed = True

    logger.info("Settings updated: %s", list(updates.keys()))
    if payload.llm_api_key:
        logger.info("API key updated (value hidden)")
    if payload.llm_base_url:
        logger.info("Base URL updated: %s", _llm_base_url)

    # Update the engine's LLM configuration if API credentials changed
    if credentials_changed:
        _update_engine_config(request.app)

    return _sanitize_for_response(new_settings)


def _update_engine_config(app) -> None:
    """Update the engine's LLM config with latest API credentials.

    Args:
        app: The FastAPI app instance with engine in state.
    """
    engine = getattr(app.state, "engine", None)
    if engine is not None and hasattr(engine, "settings"):
        settings: Settings = app.state.settings  # type: ignore[attr-defined]
        engine.settings.llm_api_key = _llm_api_key
        engine.settings.llm_base_url = _llm_base_url
        # Reinitialize the LLM model with new credentials
        engine.llm_model = engine.settings.get_llm()
        logger.info("Engine LLM config updated with latest API credentials")


def get_llm_credentials() -> tuple[str | None, str | None]:
    """Get the stored LLM API key and base URL for engine initialization."""
    return _llm_api_key, _llm_base_url