"""Embedding 模型工厂 + 极简辅助工具。

Phase C 重构后，`utils/llms.py` 仅保留 LLM/embedding 配置相关 helper。
论文库场景专用的 `VectorStore` / `NumpyVectorStore` / `QdrantVectorStore`
已全部删除（它们只为已删除的 `evoscholar.literature_qa.docs.Docs` 服务，
而我们"搜索 + 极简总结"路径不需要向量存储）。
"""

from __future__ import annotations

from lmi import (
    EmbeddingModel,
    HybridEmbeddingModel,
    LiteLLMEmbeddingModel,
    SentenceTransformerEmbeddingModel,
    SparseEmbeddingModel,
)

__all__ = [
    "EmbeddingModel",
    "HybridEmbeddingModel",
    "LiteLLMEmbeddingModel",
    "SentenceTransformerEmbeddingModel",
    "SparseEmbeddingModel",
    "embedding_model_factory",
]


def embedding_model_factory(embedding: str, **kwargs) -> EmbeddingModel:
    """根据字符串前缀选择合适的 Embedding 模型实现。

    支持：
    - `"hybrid-..."`：稀疏 + 稠密混合
    - `"st-..."`：SentenceTransformer 本地嵌入
    - `"litellm-..."`：litellm 代理嵌入
    - `"sparse"`：纯稀疏嵌入
    - 其余：默认走 litellm
    """
    embedding = embedding.strip()

    if embedding.startswith("hybrid-"):
        dense_name = embedding[len("hybrid-") :]

        if not dense_name:
            raise ValueError(
                "Hybrid embedding must contain at least one component embedding."
            )

        dense_model = embedding_model_factory(dense_name, **kwargs)
        sparse_model = SparseEmbeddingModel(**kwargs)

        return HybridEmbeddingModel(models=[dense_model, sparse_model])

    if embedding.startswith("st-"):
        model_name = embedding[len("st-") :].strip()
        if not model_name:
            raise ValueError(
                "SentenceTransformer model name must be specified after 'st-'."
            )

        return SentenceTransformerEmbeddingModel(
            name=model_name,
            config=kwargs,
        )

    if embedding.startswith("litellm-"):
        model_name = embedding[len("litellm-") :].strip()
        if not model_name:
            raise ValueError("model name must be specified after 'litellm-'.")

        return LiteLLMEmbeddingModel(
            name=model_name,
            config=kwargs,
        )

    if embedding == "sparse":
        return SparseEmbeddingModel(**kwargs)

    return LiteLLMEmbeddingModel(name=embedding, config=kwargs)
