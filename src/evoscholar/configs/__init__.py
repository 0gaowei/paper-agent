"""evoscholar 的预置配置文件 + 聚合 settings。

承载：
- 各场景下的 ``*.json`` 配置（按 provider / 模型类型 / topic 划分）
- ``evoscholar.configs.settings.Settings`` 主聚合类（替代已删除的
  ``evoscholar.literature_qa.settings.Settings``）
"""

from __future__ import annotations

from .settings import Settings, get_settings, reset_settings

__all__ = ["Settings", "get_settings", "reset_settings"]
