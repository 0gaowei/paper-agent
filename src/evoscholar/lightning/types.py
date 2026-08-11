"""轻量级数据模型。

替代被删除的 `evoscholar.literature_qa.core.DocDetails`，仅保留搜索 +
极简答案合成场景需要的字段。论文库特有字段（bibtex / citation key /
publisher / issn / license）通过 `other: dict` 兜底承载。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PaperDetail(BaseModel):
    """学术搜索结果 / 单篇论文的轻量级数据模型。

    设计动机：原 `paperqa.DocDetails` 承载论文库场景全套字段（bibtex /
    citation key / publisher / issn / license 等），与"搜索 + 极简总结"
    场景无关；我们只需保留搜索结果 + 答案合成所需的最少字段。

    字段命名约定：
    - `docname` / `dockey`：稳定 ID（DOI 或 sha1(title|year)），提供给
      LLM 引用答案时使用。`dockey` 保留仅为向后兼容（保留字段名）。
    - `title` / `authors` / `year` / `doi`：搜索结果展示所需最小集。
    - `abstract` / `citation_count` / `pdf_url` / `url` / `journal` /
      `publication_date`：答案合成可能用到的元数据。
    - `other`：escape hatch。OpenAlex 的原始字段
      （如 `concepts` / `referenced_works` 等）均放在这里，避免污染模型字段。
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")

    # === 稳定 ID ===
    docname: str  # 主要 ID，搜索结果排序/去重依据
    dockey: str = ""  # 兼容 paperqa.DocDetails；默认等于 docname

    # === 核心元数据 ===
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    doi: str | None = None

    # === 摘要 / 来源 ===
    abstract: str | None = None  # 部分搜索 provider 不提供，nullable
    journal: str | None = None
    publication_date: datetime | None = None

    # === 引用 / 链接 ===
    citation_count: int | None = None
    pdf_url: str | None = None
    url: str | None = None

    # === 扩展字段（escape hatch）===
    other: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _dockey_defaults_to_docname(self) -> PaperDetail:
        """`dockey` 默认值等于 `docname`（兼容 paperqa.DocDetails API）。"""
        if not self.dockey:
            object.__setattr__(self, "dockey", self.docname)
        return self


# 因 `from __future__ import annotations` + Pydantic v2 model_post_init 在
# 旧版 pydantic 有兼容性差异，回退到 `model_validator(mode="after")`。
# 在模块加载时显式 rebuild 以确保 `datetime` 类型的注解被解析。
PaperDetail.model_rebuild()
