"""Settings routes for reading/updating researcher configuration."""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException, status

from paperqa.server.schemas import SettingsPayload

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
}

# In-memory mutable settings (non-API-key fields)
_current_settings: dict[str, object] = dict(_SETTINGS_DEFAULTS)


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
        llm_configured=_check_key("OPENAI_API_KEY")
        or _check_key("ANTHROPIC_API_KEY")
        or _check_key("LITELLM_API_KEY"),
        s2_configured=_check_key("SEMANTIC_SCHOLAR_API_KEY"),
        openalex_configured=_check_key("OPENTALEX_API_KEY"),
    )


@router.put(
    "",
    response_model=SettingsPayload,
    summary="Update researcher settings",
)
async def update_settings(payload: SettingsPayload) -> SettingsPayload:
    """Update researcher settings (non-API-key fields only).

    This endpoint intentionally rejects any API keys passed in the body.
    Only researcher LLM config, thresholds, rounds, and similar fields are accepted.
    """
    global _current_settings

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

    _current_settings.update(updates)
    logger.info("Settings updated: %s", list(updates.keys()))

    # Re-read current state for response
    return await get_settings()
