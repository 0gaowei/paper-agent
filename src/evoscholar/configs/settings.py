"""Aggregated settings for evoscholar.

Replaces the deleted ``evoscholar.literature_qa.settings.Settings`` with a
minimal version that carries only the fields consumed by in-tree code:

- Top-level LLM fields (``llm`` / ``llm_config`` / ``summary_llm`` /
  ``llm_api_key`` / ``llm_base_url``)
- Top-level embedding fields (``embedding`` / ``embedding_config``)
- ``research: ResearchSettings`` (iterative_search 配置)
- ``get_llm()`` 工厂方法 (lazy, 复用于 engine 与 routes)

Notes:
- ``llm_api_key`` 标记 ``exclude=True``，避免 model_dump 泄露
- ``get_settings()`` 返回 singleton，便于 routes / lifespan 共享状态
- 我们从 ``literature_qa.settings`` 复活了**最小集**，不做完整功能恢复
  （如 ``agent`` / ``parsing`` / ``index_directory`` 等论文库场景字段已删除）
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from ..iterative_search.settings import ResearchSettings

if TYPE_CHECKING:
    pass  # 占位，避免 future-annotations 跨类型边界问题


class Settings(BaseModel):
    """聚合的 evoscholar 研究配置。"""

    model_config = ConfigDict(extra="ignore")

    # === LLM ===
    llm: str = Field(
        default="gpt-4o-mini",
        description="研究阶段默认 LLM 模型名（litellm 解析）。",
    )
    summary_llm: str = Field(
        default="gpt-4o-mini",
        description="答案合成 LLM（已与 llm 解耦；暂未使用，将来可独立配置）。",
    )
    llm_config: dict[str, Any] = Field(
        default_factory=dict,
        description="研究 LLM 透传配置（如 temperature / max_tokens / api_base 等）。",
    )
    llm_api_key: str | None = Field(
        default=None,
        exclude=True,
        description="LLM API key（exclude=True，不参与序列化）。",
    )
    llm_base_url: str | None = Field(
        default=None,
        description="LLM 自定义 endpoint（litellm 透传）。",
    )

    # === Embedding ===
    embedding: str = Field(
        default="st-multi-qa-MiniLM-L6-cos-v1",
        description="embedding 模型（st-* / litellm-* / hybrid-* 等）。",
    )
    embedding_config: dict[str, Any] = Field(
        default_factory=dict,
        description="透传给 embedding_model_factory 的 kwargs。",
    )

    # === 子包配置 ===
    research: ResearchSettings = Field(default_factory=ResearchSettings)

    def get_llm(self) -> Any:
        """惰性创建 ``lmi.LLMModel`` 单例。

        与 routes / lifespan 共享：每次调用都基于当前 ``Settings`` 重建
        （简单起见；性能不是瓶颈），保证 ``model_copy`` 后的修改生效。
        """
        from lmi import LiteLLMModel

        kwargs: dict[str, Any] = dict(self.llm_config or {})
        if self.llm_api_key:
            kwargs.setdefault("api_key", self.llm_api_key)
        if self.llm_base_url:
            kwargs.setdefault("api_base", self.llm_base_url)
        return LiteLLMModel(name=self.llm, config=kwargs)


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_DEFAULT_SETTINGS: Settings | None = None


def get_settings() -> Settings:
    """返回进程级单例（首次调用创建）。"""
    global _DEFAULT_SETTINGS
    if _DEFAULT_SETTINGS is None:
        _DEFAULT_SETTINGS = Settings()
    return _DEFAULT_SETTINGS


def reset_settings() -> None:
    """重置单例（测试 / lifespan 启动时使用）。"""
    global _DEFAULT_SETTINGS
    _DEFAULT_SETTINGS = None


__all__ = ["Settings", "get_settings", "reset_settings"]
