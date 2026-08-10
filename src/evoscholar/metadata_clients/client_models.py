"""学术搜索 Provider 共用的抽象基类 / 查询类型。

被 paper-qa 上游的 `metadata_clients/client_models.py` 删除后局部复活，承载
搜索 Provider 仍需要的最小集：
- `DOIQuery` / `TitleAuthorQuery`：Provider `_query(query)` 的入参类型
- `DOIOrTitleBasedProvider`：Provider 抽象基类（仅声明接口，无业务字段）

**只承载搜索 Provider 类型**，不暴露 `DocDetails`、LDP 字段等论文库概念。
若你需要论文库语义，请改用 `evoscholar.lightning.PaperDetail`。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Collection
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ClientQuery(BaseModel):
    """Provider `_query()` 的基类：仅承载 `httpx.AsyncClient` 句柄。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    client: httpx.AsyncClient


class DOIQuery(ClientQuery):
    """以 DOI 询问 Provider。"""

    doi: str
    fields: Collection[str] | None = None


class TitleAuthorQuery(ClientQuery):
    """以标题（+ 可选作者）询问 Provider。

    复用 paperqa 上游语义：`fields` 会自动追加 `doi` / `title`（必要时追加
    `authors`），保证跨 provider 行为一致。
    """

    title: str
    authors: list[str] = Field(default_factory=list)
    title_similarity_threshold: float = 0.75
    fields: Collection[str] | None = None

    @model_validator(mode="before")
    @classmethod
    def ensure_fields_are_present(cls, data: dict[str, Any]) -> dict[str, Any]:
        # 镜像 paperqa 上游行为：fields 缺省时自动补 doi / title / authors
        # 这样下游映射 (`SEMANTIC_SCHOLAR_API_MAPPING` 等) 不会因为 fields
        # 缺失而漏掉关键 key。
        if fields := data.get("fields"):
            if "doi" not in fields:
                fields.append("doi")
            if "title" not in fields:
                fields.append("title")
            if data.get("authors") is not None and "authors" not in fields:
                fields.append("authors")
        return data


class DOIOrTitleBasedProvider(ABC):
    """以 DOI 或 标题(+作者) 为入口的 Provider 抽象基类。

    子类实现 `_query(query)`，对 `DOIQuery` / `TitleAuthorQuery` 二选一
    返回 `PaperDetail | None`（找不到时返回 None）。`get_doc_details` /
    `search_by_title` 由基类根据查询类型分派。

    注意：返回值类型以字符串注解形式表达，避免在 `client_models` 中硬引用
    `evoscholar.lightning.PaperDetail`（防止未来重构 lightning 时连带影响）。
    """

    name: str

    @abstractmethod
    async def _query(self, query: DOIQuery | TitleAuthorQuery) -> Any:
        """Provider 内部实现：消费 `DOIQuery` 或 `TitleAuthorQuery`，
        返回 `PaperDetail | None`。"""


__all__ = [
    "DOIOrTitleBasedProvider",
    "DOIQuery",
    "TitleAuthorQuery",
]
