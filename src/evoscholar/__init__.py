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

from evoscholar.agents import ask
from evoscholar.agents.main import agent_query
from evoscholar.literature_qa.docs import Docs
from evoscholar.literature_qa.core import Context, Doc, DocDetails, PQASession, Text
from evoscholar.utils.llms import (
    NumpyVectorStore,
    QdrantVectorStore,
    VectorStore,
)
from evoscholar.literature_qa.settings import Settings, get_settings
from evoscholar.version import __version__

__all__ = [
    "Context",
    "Doc",
    "DocDetails",
    "Docs",
    "EmbeddingModel",
    "HybridEmbeddingModel",
    "LLMModel",
    "LLMResult",
    "LiteLLMEmbeddingModel",
    "LiteLLMModel",
    "NumpyVectorStore",
    "PQASession",
    "QdrantVectorStore",
    "SentenceTransformerEmbeddingModel",
    "Settings",
    "SparseEmbeddingModel",
    "Text",
    "VectorStore",
    "__version__",
    "agent_query",
    "ask",
    "embedding_model_factory",
    "get_settings",
]

# Compatibility shim: allow `import paperqa` to continue working during transition.
import sys as _sys

_paperqa = _sys.modules.get("evoscholar")
if _paperqa is not None:
    _sys.modules["paperqa"] = _paperqa
