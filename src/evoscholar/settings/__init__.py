# Re-export from the settings config module for backward compatibility.
from evoscholar.settings_config import (
    AgentSettings,
    AnswerSettings,
    ChunkingOptions,
    IndexSettings,
    MaybeSettings,
    MultimodalOptions,
    ParsingSettings,
    PromptSettings,
    ResearchSettings,
    Settings,
    get_settings,
)

__all__ = [
    "AgentSettings",
    "AnswerSettings",
    "ChunkingOptions",
    "IndexSettings",
    "MaybeSettings",
    "MultimodalOptions",
    "ParsingSettings",
    "PromptSettings",
    "ResearchSettings",
    "Settings",
    "get_settings",
]
