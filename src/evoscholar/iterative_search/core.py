"""Core components for iterative search.

This module contains:
- _TrackedLLMAdapter: LLM adapter for usage tracking

Owner: iterative_search package.
"""
from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

from lmi import LLMResult

if TYPE_CHECKING:
    from evoscholar.synthesis.models import UsageStats


class _TrackedLLMAdapter:
    """Expose PaperQA's call_single API around either supported LLM interface.

    This adapter is used in query understanding (before synthesis) to track
    LLM usage. The usage is accumulated into the session's UsageStats.
    """

    def __init__(self, delegate: Any, usage: "UsageStats") -> None:
        self.delegate = delegate
        self.usage = usage

    async def call_single(self, messages: Any, **kwargs: Any) -> Any:
        if hasattr(self.delegate, "call_single"):
            response = self.delegate.call_single(messages=messages, **kwargs)
        elif hasattr(self.delegate, "acomplete"):
            serialized = [
                {
                    "role": getattr(message, "role", None) or "user",
                    "content": getattr(message, "content", None) or str(message),
                }
                for message in messages
            ]
            response = self.delegate.acomplete(serialized)
        else:
            raise TypeError("LLM model must provide call_single() or acomplete()")
        response = await response if inspect.isawaitable(response) else response
        self.usage.llm_calls += 1

        if isinstance(response, LLMResult):
            self.usage.llm_prompt_tokens += response.prompt_count or 0
            self.usage.llm_completion_tokens += response.completion_count or 0
            self.usage.llm_cost_usd += response.cost
            return response

        def _usage_value_inner(usage: Any, *names: str) -> int:
            for name in names:
                value = usage.get(name) if isinstance(usage, dict) else getattr(usage, name, None)
                if value is not None:
                    return int(value)
            return 0

        raw_usage = (
            response.get("usage") if isinstance(response, dict) else getattr(response, "usage", None)
        )
        prompt_tokens = _usage_value_inner(raw_usage, "prompt_tokens", "input_tokens")
        completion_tokens = _usage_value_inner(raw_usage, "completion_tokens", "output_tokens")
        hidden = getattr(response, "_hidden_params", {}) or {}
        cost = float(hidden.get("response_cost") or 0.0)
        self.usage.llm_prompt_tokens += prompt_tokens
        self.usage.llm_completion_tokens += completion_tokens
        self.usage.llm_cost_usd += cost
        return response
