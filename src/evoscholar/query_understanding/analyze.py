from __future__ import annotations

import inspect
import json
import logging
import re
from typing import Any

from aviary.core import Message

from .models import Domain, QueryIntent, QueryUnderstanding
from .prompts import QUERY_UNDERSTANDING_PROMPT, QUERY_UNDERSTANDING_SYSTEM

logger = logging.getLogger(__name__)

_DOMAIN_ALIASES = {
    "ai": Domain.CS_AI,
    "artificial intelligence": Domain.CS_AI,
    "computer science": Domain.CS_AI,
    "cs": Domain.CS_AI,
    "natural language processing": Domain.NLP,
    "machine learning": Domain.ML,
    "computer vision": Domain.CV,
    "biology": Domain.BIO,
    "medicine": Domain.MED,
    "medical": Domain.MED,
    "social science": Domain.SOCIAL,
    "multidisciplinary": Domain.MULTIDISCIPLINARY,
    "unknown": Domain.UNKNOWN,
}


def _extract_text(response: Any) -> str:
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        if isinstance(response.get("content"), str):
            return response["content"]
        choices = response.get("choices") or []
        if choices:
            message = choices[0].get("message", {})
            if isinstance(message.get("content"), str):
                return message["content"]
    if isinstance(getattr(response, "text", None), str):
        return response.text
    choices = getattr(response, "choices", None) or []
    if choices:
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if isinstance(content, str):
            return content
    raise TypeError(f"Unsupported LLM response type: {type(response).__name__}")


def _extract_json(text: str) -> dict[str, Any]:
    stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    start, end = stripped.find("{"), stripped.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("LLM response did not contain a JSON object")
    value = json.loads(stripped[start : end + 1])
    if not isinstance(value, dict):
        raise TypeError("LLM response JSON must be an object")
    return value


def _coerce_domain(value: Any) -> Domain:
    if isinstance(value, Domain):
        return value
    normalized = str(value).strip().lower().replace("-", "_")
    try:
        return Domain(normalized)
    except ValueError:
        return _DOMAIN_ALIASES.get(normalized.replace("_", " "), Domain.UNKNOWN)


def _normalize_payload(query: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        intent = QueryIntent(str(payload.get("intent", "general")).lower())
    except ValueError:
        intent = QueryIntent.GENERAL
    domains = [_coerce_domain(value) for value in payload.get("domains") or []]
    domains = list(dict.fromkeys(domains)) or [Domain.UNKNOWN]

    normalized_subqueries: list[dict[str, Any]] = []
    for item in payload.get("subqueries") or []:
        if isinstance(item, str):
            item = {"query": item}
        if not isinstance(item, dict) or not str(item.get("query", "")).strip():
            continue
        normalized_subqueries.append(
            {
                **item,
                "query": str(item["query"]).strip(),
                "parent_intent": intent,
                "domain": _coerce_domain(item.get("domain", domains[0])),
            }
        )
    if not normalized_subqueries:
        normalized_subqueries = [
            {
                "query": query,
                "purpose": "Search the original research question",
                "priority": 10,
                "parent_intent": intent,
                "domain": domains[0],
            }
        ]

    return {
        **payload,
        "original_query": query,
        "intent": intent,
        "domains": domains,
        "subqueries": normalized_subqueries,
    }


async def _call_llm(llm_model: Any, messages: list[dict[str, str]]) -> Any:
    logger.debug("_call_llm start, model=%s", getattr(llm_model, "name", type(llm_model).__name__))
    if hasattr(llm_model, "acomplete"):
        result = llm_model.acomplete(messages)
    elif hasattr(llm_model, "call_single"):
        result = llm_model.call_single(
            messages=[Message(role=m["role"], content=m["content"]) for m in messages],
            name="research_query_understanding",
        )
    else:
        raise TypeError("LLM model must provide acomplete() or call_single()")
    response = await result if inspect.isawaitable(result) else result
    logger.debug("_call_llm done")
    return response


async def analyze_and_expand_query(
    query: str, settings: Any, llm_model: Any
) -> QueryUnderstanding:
    """Analyze a query with the configured LLM and return a structured understanding.

    Raises:
        ValueError: If the query is empty.
        Exception: Propagated from the LLM call or JSON parsing if the LLM
            response cannot be parsed into a ``QueryUnderstanding``.
    """
    query = query.strip()
    if not query:
        raise ValueError("query must not be empty")

    logger.info(
        "analyze_and_expand_query start, query='%s'",
        query[:80],
    )

    messages = [
        {"role": "system", "content": QUERY_UNDERSTANDING_SYSTEM},
        {
            "role": "user",
            "content": QUERY_UNDERSTANDING_PROMPT.format(query=query),
        },
    ]
    response = await _call_llm(llm_model, messages)
    payload = _normalize_payload(query, _extract_json(_extract_text(response)))
    result = QueryUnderstanding.model_validate(payload)

    logger.info(
        "analyze_and_expand_query done, intent=%s, domains=%s, subqueries=%d",
        result.intent,
        result.domains,
        len(result.subqueries),
    )
    for sq in result.subqueries:
        logger.debug(
        "  subquery: priority=%.2f, domain=%s, purpose='%s', query='%s'",
            sq.priority,
            sq.domain,
            getattr(sq, "purpose", "N/A"),
            sq.query[:80],
        )
    return result
