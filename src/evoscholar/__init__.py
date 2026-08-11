"""evoscholar (renamed from paper-qa 2026.3.19).

顶层 export 极简：
- 来自 ``lmi`` 的 EmbeddingModel / LLMModel / embedding_model_factory
- 来自 ``evoscholar.configs`` 的 Settings / get_settings
- 来自 ``evoscholar.utils.llms`` 的 embedding_model_factory re-export
- 版本号

论文库相关（Docs / DocDetails / Context / Doc / PQASession / Text /
NumpyVectorStore / QdrantVectorStore / VectorStore / ask / agent_query）
均已删除 — 见 ``docs/meta/HANDOFF-2026-08-10-23-no-paper-library-simplify.md``。
"""

from lmi import (
    EmbeddingModel,
    HybridEmbeddingModel,
    LiteLLMEmbeddingModel,
    LiteLLMModel,
    LLMModel,
    LLMResult,
    SentenceTransformerEmbeddingModel,
    SparseEmbeddingModel,
    embedding_model_factory,
)

from evoscholar.configs import Settings, get_settings
from evoscholar.version import __version__

__all__ = [
    "EmbeddingModel",
    "HybridEmbeddingModel",
    "LLMModel",
    "LLMResult",
    "LiteLLMEmbeddingModel",
    "LiteLLMModel",
    "SentenceTransformerEmbeddingModel",
    "Settings",
    "SparseEmbeddingModel",
    "__version__",
    "embedding_model_factory",
    "get_settings",
]


# Compatibility alias: keep ``import paperqa`` working so legacy downstream
# code (e.g. ``paperqa_pypdf`` / ``paperqa_pymupdf`` wheels that still
# reference paperqa.*) keeps loading. New in-tree code imports from
# ``evoscholar.*`` directly.
#
# Note: Python inserts the importing module into ``sys.modules`` *before*
# executing ``__init__.py``, so ``sys.modules["evoscholar"]`` is reliably
# available here.
import sys as _sys

_paperqa = _sys.modules.get("evoscholar")
if _paperqa is not None:
    _sys.modules["paperqa"] = _paperqa
