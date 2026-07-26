from __future__ import annotations

import inspect
import json
import re
from typing import Any

from aviary.core import Message

from .models import Domain, QueryIntent, QueryUnderstanding, SubQuery
from .prompts import QUERY_UNDERSTANDING_PROMPT, QUERY_UNDERSTANDING_SYSTEM

_DOMAIN_KEYWORDS: dict[Domain, tuple[str, ...]] = {
    Domain.NLP: (
        "nlp",
        "language model",
        "llm",
        "transformer",
        "text generation",
        "自然语言",
        "语言模型",
    ),
    Domain.ML: (
        "machine learning",
        "deep learning",
        "neural network",
        "reinforcement learning",
        "机器学习",
        "深度学习",
    ),
    Domain.CV: (
        "computer vision",
        "image recognition",
        "object detection",
        "视觉",
        "图像",
    ),
    Domain.MED: (
        "medicine",
        "medical",
        "clinical",
        "patient",
        "医学",
        "临床",
    ),
    Domain.BIO: ("biology", "genomics", "protein", "cell", "生物", "基因"),
    Domain.PHYSICS: ("physics", "quantum", "物理", "量子"),
    Domain.CHEMISTRY: ("chemistry", "molecule", "chemical", "化学", "分子"),
    Domain.ECONOMICS: ("economics", "economic", "market", "经济", "市场"),
    Domain.PSYCHOLOGY: ("psychology", "cognitive", "心理", "认知"),
    Domain.SOCIAL: ("social science", "sociology", "社会科学", "社会学"),
    Domain.CS_AI: (
        "artificial intelligence",
        "computer science",
        "algorithm",
        "人工智能",
        "计算机",
        "算法",
    ),
}

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
        "fallback_used": False,
        "error_message": None,
    }


async def _call_llm(llm_model: Any, messages: list[dict[str, str]]) -> Any:
    if hasattr(llm_model, "acomplete"):
        result = llm_model.acomplete(messages)
    elif hasattr(llm_model, "call_single"):
        result = llm_model.call_single(
            messages=[Message(role=m["role"], content=m["content"]) for m in messages],
            name="research_query_understanding",
        )
    else:
        raise TypeError("LLM model must provide acomplete() or call_single()")
    return await result if inspect.isawaitable(result) else result


async def analyze_and_expand_query(
    query: str, settings: Any, llm_model: Any
) -> QueryUnderstanding:
    """Analyze a query with the configured LLM, falling back to local heuristics."""
    query = query.strip()
    if not query:
        raise ValueError("query must not be empty")

    messages = [
        {"role": "system", "content": QUERY_UNDERSTANDING_SYSTEM},
        {
            "role": "user",
            "content": QUERY_UNDERSTANDING_PROMPT.format(query=query),
        },
    ]
    try:
        response = await _call_llm(llm_model, messages)
        return QueryUnderstanding.model_validate(
            _normalize_payload(query, _extract_json(_extract_text(response)))
        )
    except Exception as exc:  # The research loop must remain available without an LLM.
        return _heuristic_understanding(query, settings, error_message=str(exc))


def _heuristic_understanding(
    query: str, settings: Any, error_message: str | None = None
) -> QueryUnderstanding:
    """Infer a conservative intent/domain decomposition using local keywords."""
    lowered = query.casefold()
    if any(term in lowered for term in ("compare", "versus", " vs ", "comparison", "对比", "比较")):
        intent = QueryIntent.COMPARATIVE
    elif any(term in lowered for term in ("latest", "recent", "current", "state of the art", "最新", "近期", "现状")):
        intent = QueryIntent.CURRENT_STATE
    elif any(term in lowered for term in ("survey", "review", "overview", "综述", "概览")):
        intent = QueryIntent.SURVEY
    elif any(term in lowered for term in ("history", "foundational", "background", "基础", "历史")):
        intent = QueryIntent.BACKGROUND
    elif any(term in lowered for term in ("how", "why", "what", "which", "如何", "为什么", "什么")):
        intent = QueryIntent.SPECIFIC
    else:
        intent = QueryIntent.GENERAL

    domains = [
        domain
        for domain, keywords in _DOMAIN_KEYWORDS.items()
        if any(keyword in lowered for keyword in keywords)
    ]
    domains = list(dict.fromkeys(domains)) or [Domain.UNKNOWN]

    research_settings = getattr(settings, "research", settings)
    providers = list(
        getattr(research_settings, "providers", ["semantic_scholar", "openalex"])
    )
    subqueries = [
        SubQuery(
            query=query,
            purpose="Search the original research question",
            priority=10,
            parent_intent=intent,
            domain=domains[0],
        )
    ]
    if intent in {QueryIntent.SURVEY, QueryIntent.CURRENT_STATE}:
        subqueries.append(
            SubQuery(
                query=f"{query} recent advances review",
                purpose="Cover recent work and synthesis papers",
                priority=7,
                parent_intent=intent,
                domain=domains[0],
            )
        )
    elif intent == QueryIntent.BACKGROUND:
        subqueries.append(
            SubQuery(
                query=f"{query} foundational papers",
                purpose="Find foundational literature",
                priority=7,
                parent_intent=intent,
                domain=domains[0],
            )
        )

    strategy = "survey" if intent in {QueryIntent.SURVEY, QueryIntent.CURRENT_STATE} else (
        "domain" if domains != [Domain.UNKNOWN] else "general"
    )
    return QueryUnderstanding(
        original_query=query,
        intent=intent,
        domains=domains,
        suitable_sources=providers,
        subqueries=subqueries,
        search_strategy=strategy,
        fallback_used=True,
        error_message=error_message,
    )
