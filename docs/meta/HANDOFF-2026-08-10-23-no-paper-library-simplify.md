# HANDOFF: 2026-08-10-23-no-paper-library-simplify

> 最近一次更新：2026-08-10 23:00 (UTC+8)

## Status

- [x] 当前阶段：**部分实现（WIP commit 已落，项目当前不可运行）**
- 一句话目标：删除 paper-qa 上游 "论文库场景"（`metadata_clients` 论文库 Provider + 整个 `literature_qa` 包），保留学术搜索 + 自己写轻量答案合成。
- 路径选择：**搜索 + 极简总结**（保留 LLM 总结能力，但用自写轻量版替代 paperqa.Docs）。
- 完成度：约 **30%**（元数据客户端清理完成；数据模型与上层重构未开始）。

## Environment

- workspace：`/home/gaowei/paper-search/paper-qa`
- 分支：`refactor/simplify-no-paper-library`（已基于 `paper-agent` 7dcfaa7 开新分支）
- 关键依赖：上游 `paper-qa==2026.3.19`（pip install）；`evoscholar` 本地包
- Python：3.12
- 测试/服务：`pytest`、`pqa-serve`

## Git state

- branch：`refactor/simplify-no-paper-library`
- last commit：`6454572` wip: 删除 metadata_clients 论文库 Provider/Processor + literature_qa 全包
- dirty files：✅ 已提交（WIP 已落地）
- 主分支：`paper-agent`（未受影响）

## Progress

### ✅ 已完成

1. **删除论文库相关 Provider/Processor**（8 文件）
   - `src/evoscholar/metadata_clients/crossref.py`（Provider，论文库场景用）
   - `src/evoscholar/metadata_clients/unpaywall.py`（Provider，PDF 下载）
   - `src/evoscholar/metadata_clients/journal_quality.py`（PostProcessor，期刊打分）
   - `src/evoscholar/metadata_clients/retractions.py`（PostProcessor，撤稿检测）
   - `src/evoscholar/metadata_clients/client_models.py`（抽象基类）
   - `src/evoscholar/metadata_clients/exceptions.py`（`DOINotFoundError`）
   - `src/evoscholar/metadata_clients/settings.py`（占位）
   - `src/evoscholar/metadata_clients/__init__.py`（包入口）

2. **删除整个 `literature_qa` 包**（13 文件）
   - `core.py` `core_impl.py` `docs.py` `main.py` `tools.py` `search.py`
   - `settings.py` `models.py` `helpers.py` `prompts.py` `readers.py`
   - `env.py` `types.py` `__init__.py`

3. **元数据客户端验证**
   - `academic_search.py` 不依赖被删的 `client_models` / `exceptions`，可独立运行
   - `semantic_scholar.py` `openalex.py` 仍引用 `evoscholar.literature_qa.core` —— **必须改造**

### ⚠️ 已识别但未改动的引用（9 个文件需要 Phase B 处理）

1. `src/evoscholar/__init__.py` —— 从 `literature_qa` 导入 `ask`, `agent_query`, `Docs`, `Context`, `Doc`, `DocDetails`, `PQASession`, `Text`, `Settings`, `get_settings`
2. `src/evoscholar/types.py` —— `from evoscholar.literature_qa.types import ParsedMedia, ParsedMetadata, ParsedText`
3. `src/evoscholar/readers.py` —— `resolve_page_range`
4. `src/evoscholar/utils/llms.py` —— `NumpyVectorStore`, `Docs`, `Text`
5. `src/evoscholar/metadata_clients/semantic_scholar.py` —— `BibTeXSource`, `DocDetails`
6. `src/evoscholar/metadata_clients/openalex.py` —— `DocDetails`
7. `src/evoscholar/iterative_search/engine.py` —— `Docs`, `DocDetails`, `Text`（904 行）
8. `src/evoscholar/synthesis/builder.py` —— `Docs`, `DocDetails`, `Text`
9. `src/evoscholar/server/app.py` + `server/routes/settings.py` —— `Settings`
10. `src/evoscholar/contrib/zotero.py` —— `PDFParserFn`

### ❌ 当前项目状态

**不可运行**。`python -c "from evoscholar import ..."` 立即报：

```
ImportError: cannot import name 'ask' from 'evoscholar.literature_qa' (unknown location)
```

## Next steps（subagent 推进顺序）

### Phase A：创建轻量数据模型（15 分钟）

**新增文件**：`src/evoscholar/lightning/types.py`

```python
from __future__ import annotations
from typing import Any
from pydantic import BaseModel

class PaperDetail(BaseModel):
    """轻量版搜索结果数据模型，替代原 DocDetails。

    仅保留：搜索结果存储 + 答案合成需要的最少字段。
    """
    docname: str           # 唯一 id
    dockey: str            # 同 docname
    title: str = ""
    authors: list[str] = []
    year: int | None = None
    doi: str | None = None
    abstract: str = ""
    citation: str = ""
    content: str = ""      # 给 LLM 的文本（搜索结果就用 abstract）
    other: dict[str, Any] = {}
```

完成标准：
```bash
python -c "from evoscholar.lightning.types import PaperDetail; print(PaperDetail)"
```

### Phase B：替换 metadata_clients 数据类型引用（30 分钟）

修改以下 3 个文件中所有 `evoscholar.literature_qa.core` 导入 → `evoscholar.lightning.types`，所有 `DocDetails` → `PaperDetail`：

1. `src/evoscholar/metadata_clients/semantic_scholar.py`
2. `src/evoscholar/metadata_clients/openalex.py`
3. `src/evoscholar/metadata_clients/academic_search.py`

**关键点**：
- `BibTeXSource` 可能不存在于 PaperDetail 中 —— 简化为 `other: dict[str, Any]`
- 看 `_doc_to_paper` 函数（`academic_search.py`），确认只用了 `title/authors/year/doi/abstract/other`

完成标准：
```bash
python -c "from evoscholar.metadata_clients.academic_search import AcademicSearchClient"
```

### Phase C：替换 utils/llms.py + types.py + readers.py + contrib（30 分钟）

1. `src/evoscholar/utils/llms.py`：删 `NumpyVectorStore`、`Docs`、`Text` 实现。改成仅保留 `embedding_model_factory` 和必要的 LLM util（约 30 行）。如果 `Docs`/`Text` 不再被外部用，直接删整个文件。
2. `src/evoscholar/types.py`：改成 `from evoscholar.lightning.types import PaperDetail`，并删除 `ParsedMedia`/`ParsedMetadata`/`ParsedText` 或用 PaperDetail 替代
3. `src/evoscholar/readers.py`：内联 `resolve_page_range`（简单正则 `"100-105"` 解析），不再 import `literature_qa`
4. `src/evoscholar/contrib/zotero.py`：注释掉 `PDFParserFn` 引用或用 `Any` 替代

### Phase D：重写 iterative_search/engine.py + synthesis/builder.py（60 分钟，最大工作量）

两个文件都用了 `Docs`、`DocDetails`、`Text`，必须替换：

1. `src/evoscholar/iterative_search/engine.py:129-130`：
   - 旧：`from evoscholar.literature_qa.docs import Docs; from evoscholar.literature_qa.core import DocDetails, Text`
   - 新：替换为搜索流程中的 PaperDetail 构造逻辑

2. `src/evoscholar/synthesis/builder.py:107-108`：同样替换

3. **简化 answers**：
   - 原本用 `Docs.aget_evidence`（向量检索 + LLM 重排）
   - 改成**最简版**：`papers → 拼接 abstract → 送给 LLM 总结`（新增 `lightning/answer_builder.py`）

### Phase E：清理 evoscholar/__init__.py + server（20 分钟）

1. `src/evoscholar/__init__.py`：删 4 行 `literature_qa` import；移除 `ask`, `agent_query`, `Docs`, `Context`, `Doc`, `DocDetails`, `PQASession`, `Text`, `Settings`, `get_settings` 导出
2. `src/evoscholar/server/app.py:53,96`：替换 `Settings` 来源
3. `src/evoscholar/server/routes/settings.py:23`：同上
4. `src/evoscholar/iterative_search/settings.py`、`synthesis/settings.py`、`query_understanding/settings.py`、`paper_ranker/settings.py`：检查是否从 `literature_qa.settings` 引用，改为本地定义

### Phase F：删除冗余/未用模块（15 分钟）

确认以下是否可以删除（如还有 QA 相关逻辑）：
- `src/evoscholar/agents/` —— 多 agent 编排，如不再用则删除
- `src/evoscholar/contrib/` —— 如 Zotero 不再需要

### Phase G：测试 + 文档（30 分钟）

1. **导入测试**：
   ```bash
   python -c "from evoscholar import __version__"
   python -c "from evoscholar.iterative_search import ResearchEngine"
   python -c "from evoscholar.metadata_clients.academic_search import AcademicSearchClient"
   ```

2. **跑测试**：
   ```bash
   pytest tests/test_academic_search.py -x
   pytest tests/test_research_engine.py -x
   ```

3. **启动服务**：
   ```bash
   pqa-serve  # 或项目定义的启动命令
   # 然后 curl/接口调用 search query 验证
   ```

4. **文档同步**：
   - `docs/meta/state.md`：记录本次重构决策
   - `docs/meta/gotchas.md`：记录踩坑（见下）
   - 删除 `docs/meta/agent-tasks/batch-A..G.md` 中过时的 literature_qa 引用

## Gotchas / 踩过的坑

### 坑 1：`metadata_clients/__init__.py` 必须删

- **触发**：原 `__init__.py` 里有 `DEFAULT_CLIENTS`、`ALL_CLIENTS`、`DocMetadataClient`、`DocMetadataTask`、`MetadataClientQuerier` 类型别名，引用了被删的 `CrossrefProvider` 等
- **现象**：不删就 import 报错
- **解法**：直接 `git rm src/evoscholar/metadata_clients/__init__.py`

### 坑 2：`literature_qa` 被 9+ 个文件深度依赖

- **触发**：看似只在 `docs.py` 里用，实际被 `iterative_search`、`synthesis`、`utils/llms`、`server`、`metadata_clients`、`contrib`、`evoscholar/__init__` 全栈依赖
- **现象**：删除 `literature_qa` 后整个项目立即不可导入
- **解法**：必须**逐步改造引用方**，不要试图一次性 sed 全替换。每个 Phase 单独可测。

### 坑 3：上游 paper-qa 包提供 `paperqa.clients`

- **触发**：用户问"`src/paperqa/` 是什么"，以为要删
- **现象**：根本不存在 `src/paperqa/` 目录；这是 pip install 到 site-packages 的 `paper-qa==2026.3.19` 包
- **解法**：**不要尝试删上游 paperqa 包**。`tests/test_clients.py`、`tests/test_paperqa.py` 测试的就是它，删测试就删测试对应的功能

### 坑 4：Cursor glob `**/*` 输出包含子目录深路径

- **触发**：用 `Glob` 列出 `evoscholar/` 时
- **现象**：输出里出现 `research/engine.py` 等不存在的路径
- **解法**：实际路径要 `ls` 或 `find` 验证，不要轻信 glob 输出的全部条目

### 坑 5：单次对话上下文已用尽

- **触发**：本次会话已经迭代 7+ 轮
- **现象**：LLM 上下文噪声累积，subagent 推进的可靠性下降
- **解法**：用此 HANDOFF 文档 + 每 Phase 一个新 subagent 推进

## Key file references

### 关键文件路径速查

```
src/evoscholar/
├── metadata_clients/                  # 仅剩 3 文件（搜索 Provider）
│   ├── academic_search.py             # 搜索入口（保留）
│   ├── semantic_scholar.py            # S2 Provider
│   └── openalex.py                    # OpenAlex Provider
│
├── iterative_search/                  # 搜索主循环（待重构）
│   ├── engine.py:129-130              # ⚠️ Docs/DocDetails/Text import
│   └── ...
│
├── synthesis/                         # 答案合成（待重写）
│   └── builder.py:107-108             # ⚠️ Docs/DocDetails/Text import
│
├── utils/
│   └── llms.py:399,423,454            # ⚠️ 用 Docs/Text/NumpyVectorStore
│
├── types.py:7                         # ⚠️ ParsedMedia 等
├── readers.py:9                       # ⚠️ resolve_page_range
├── __init__.py:13-22                  # ⚠️ 4 行 literature_qa import
└── ...（其他）

src/evoscholar/lightning/              # 🆕 待新增
├── types.py                           # PaperDetail（轻量 DocDetails）
└── answer_builder.py                  # 极简答案合成器
```

### 已有 commit 引用

- `6454572` —— WIP: 元数据清理 + literature_qa 删除（当前状态，项目不可运行）
- `7dcfaa7` —— 原始 paper-agent 基线（可回退）

## Recommended workflow

1. **开新会话**：用 `git status` 确认在 `refactor/simplify-no-paper-library` 分支
2. **读此 HANDOFF**：用 `cat .cursor/HANDOFF-2026-08-10-23-no-paper-library-simplify.md`
3. **逐 Phase 推进**：每次开一个 subagent（推荐 `generalPurpose`），提供本 HANDOFF + 当前 Phase 范围
4. **每 Phase 必测**：完成标准在每 Phase 列出
5. **完成后**：更新 `docs/meta/state.md` 记录决策，`docs/meta/gotchas.md` 追加新坑
