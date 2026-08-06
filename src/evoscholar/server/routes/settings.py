"""Settings routes for reading/updating researcher configuration."""


from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Request

from evoscholar.server.schemas import SettingsPayload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["settings"])

# Sensible defaults for settings that mirror the Settings class
_SETTINGS_DEFAULTS: dict[str, object] = {
    "researcher_llm": "gpt-4o",
    "summary_llm": "gpt-4o",
    "max_rounds": 3,
    "candidates_per_round": 10,
    "citation_expansion_limit": 5,
    "high_relevance_threshold": 0.75,
    "partial_relevance_threshold": 0.50,
    "llm_api_key": None,
    "llm_base_url": None,
    "llm_provider": "openai",
}

# In-memory mutable settings (non-API-key fields)
_current_settings: dict[str, object] = dict(_SETTINGS_DEFAULTS)

# Server-side API key storage (never exposed to client)
_llm_api_key: str | None = None
_llm_base_url: str | None = None


def _check_key(env_var: str) -> bool:
    """Return True if the environment variable is set to a non-empty value."""
    val = os.environ.get(env_var, "")
    return bool(val)


@router.get(
    "",
    response_model=SettingsPayload,
    summary="Get researcher settings",
)
async def get_settings() -> SettingsPayload:
    """Return the current researcher settings with API key status flags.

    API keys are NEVER returned — only boolean `configured` flags.
    """
    return SettingsPayload(
        researcher_llm=_current_settings.get("researcher_llm"),
        summary_llm=_current_settings.get("summary_llm"),
        max_rounds=_current_settings.get("max_rounds"),
        candidates_per_round=_current_settings.get("candidates_per_round"),
        citation_expansion_limit=_current_settings.get("citation_expansion_limit"),
        high_relevance_threshold=_current_settings.get("high_relevance_threshold"),
        partial_relevance_threshold=_current_settings.get("partial_relevance_threshold"),
        llm_provider=_current_settings.get("llm_provider"),
        # API keys are never returned to client, but base URL is safe
        llm_api_key=None,
        llm_base_url=_llm_base_url,
        llm_configured=_check_key("OPENAI_API_KEY")
        or _check_key("ANTHROPIC_API_KEY")
        or _check_key("LITELLM_API_KEY")
        or _llm_api_key is not None,
        s2_configured=_check_key("SEMANTIC_SCHOLAR_API_KEY"),
        openalex_configured=_check_key("OPENTALEX_API_KEY"),
    )


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

    This endpoint accepts API keys in the payload but stores them server-side
    and never returns them to the client.
    """
    global _current_settings, _llm_api_key, _llm_base_url

    updates: dict[str, object] = {}
    if payload.researcher_llm is not None:
        updates["researcher_llm"] = payload.researcher_llm
    if payload.summary_llm is not None:
        updates["summary_llm"] = payload.summary_llm
    if payload.max_rounds is not None:
        updates["max_rounds"] = payload.max_rounds
    if payload.candidates_per_round is not None:
        updates["candidates_per_round"] = payload.candidates_per_round
    if payload.citation_expansion_limit is not None:
        updates["citation_expansion_limit"] = payload.citation_expansion_limit
    if payload.high_relevance_threshold is not None:
        updates["high_relevance_threshold"] = payload.high_relevance_threshold
    if payload.partial_relevance_threshold is not None:
        updates["partial_relevance_threshold"] = payload.partial_relevance_threshold
    if payload.llm_provider is not None:
        updates["llm_provider"] = payload.llm_provider

    _current_settings.update(updates)

    # Store API key and base URL server-side (not in _current_settings to avoid exposure)
    if payload.llm_api_key is not None:
        _llm_api_key = payload.llm_api_key
        # Also set as environment variable for litellm to pick up
        os.environ["LLM_API_KEY"] = payload.llm_api_key
    if payload.llm_base_url is not None:
        _llm_base_url = payload.llm_base_url
        os.environ["LLM_BASE_URL"] = payload.llm_base_url

    logger.info("Settings updated: %s", list(updates.keys()))
    if payload.llm_api_key:
        logger.info("API key updated (value hidden)")
    if payload.llm_base_url:
        logger.info("Base URL updated: %s", _llm_base_url)

    # Update the engine's LLM configuration if API credentials changed
    if payload.llm_api_key is not None or payload.llm_base_url is not None:
        _update_engine_config(request.app)

    # Re-read current state for response
    return await get_settings()


def _update_engine_config(app) -> None:
    """Update the engine's LLM config with latest API credentials.
    
    Args:
        app: The FastAPI app instance with engine in state.
    """
    engine = getattr(app.state, "engine", None)
    if engine is not None and hasattr(engine, "settings"):
        engine.settings.llm_api_key = _llm_api_key
        engine.settings.llm_base_url = _llm_base_url
        # Reinitialize the LLM model with new credentials
        engine.llm_model = engine.settings.get_llm()
        logger.info("Engine LLM config updated with latest API credentials")


def get_llm_credentials() -> tuple[str | None, str | None]:
    """Get the stored LLM API key and base URL for engine initialization."""
    return _llm_api_key, _llm_base_url
