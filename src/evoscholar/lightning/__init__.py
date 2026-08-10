"""Lightning: 极简版 paper-qa 子模块。

提供搜索场景所需的轻量数据模型与极简答案合成逻辑，
替代被删除的 `evoscholar.literature_qa` 包（论文库场景全套）。

设计原则：
- 数据模型对齐学术搜索 API（OpenAlex / Semantic Scholar）原始字段
- 不引入论文库特有概念（bibtex / citation key / publisher / issn）
- 通过 `other: dict` 字典承载任意扩展字段（保证向后兼容）
"""

from .types import PaperDetail

__all__ = ["PaperDetail"]
