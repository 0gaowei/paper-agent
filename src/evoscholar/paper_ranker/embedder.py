from __future__ import annotations

import inspect
from typing import Any


async def embed_texts_async(
    embedding_model: Any, texts: list[str]
) -> list[list[float]]:
    """Embed texts asynchronously using the provided embedding model."""
    if hasattr(embedding_model, "embed_documents"):
        result = embedding_model.embed_documents(texts)
    elif hasattr(embedding_model, "aembed"):
        result = embedding_model.aembed(texts)
    elif hasattr(embedding_model, "embed"):
        result = embedding_model.embed(texts)
    else:
        raise TypeError("embedding model does not provide a supported embedding method")
    value = await result if inspect.isawaitable(result) else result
    if not isinstance(value, list) or len(value) != len(texts):
        raise ValueError("embedding model returned an unexpected batch shape")
    return value


def embed_texts_sync(embedding_model: Any, texts: list[str]) -> list[list[float]]:
    """Embed texts synchronously using the provided embedding model."""
    if hasattr(embedding_model, "embed_documents"):
        result = embedding_model.embed_documents(texts)
    elif hasattr(embedding_model, "embed"):
        result = embedding_model.embed(texts)
    else:
        raise TypeError("embedding model does not provide a synchronous embed method")
    if inspect.isawaitable(result):
        close = getattr(result, "close", None)
        if close is not None:
            close()
        raise TypeError("embedding model exposes an asynchronous embed method")
    if not isinstance(result, list) or len(result) != len(texts):
        raise ValueError("embedding model returned an unexpected batch shape")
    return result
