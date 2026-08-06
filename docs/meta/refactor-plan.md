# evoscholar 重构方案（原 paper-qa）

> 文档版本：2026-07-30
> 目标：将 paper-qa 单体包重构为 `evoscholar`（自进化论文搜索代理）按功能分包的模块化架构
> 包名来源：evolutionary scholar agent（自进化论文搜索代理），简称 evoscholar

---

## 1. 目标目录结构

```
evoscholar/                      # 包名 → evoscholar（自进化论文搜索代理）
├── __init__.py
├── utils/                      # 跨包共享的多包复用工具（至少 2 个功能包都需要的代码放这里）
│   ├── __init__.py
│   ├── paths.py                # 路径管理常量
│   ├── llms.py                 # 通用 LLM 工厂函数
│   ├── math_utils.py           # cosine_similarity / normalize 等通用数学工具
│   └── ...
│
├── literature_qa/              # ⑥ 文档问答 (RAG/QA 核心)
│   ├── __init__.py
│   ├── core.py                 # 本包 core：Docs / DocDetails / PQASession / PDF readers / RAG prompts / DocDetails 等
│   ├── settings.py             # 本包 settings：Answer / Parsing / Prompt / Index / Agent
│   ├── env.py
│   ├── tools.py
│   ├── main.py
│   ├── models.py
│   ├── search.py
│   └── helpers.py
│
├── query_understanding/      # ① 查询理解与分解
│   ├── __init__.py
│   ├── core.py                 # 本包 core：通用工具 / 路径（按需引用）
│   ├── settings.py             # 本包 settings：当前无独立 Settings，可保留为空文件
│   ├── models.py
│   ├── analyze.py
│   └── prompts.py
│
├── iterative_search/         # ② 自主搜索策略迭代优化
│   ├── __init__.py
│   ├── core.py                 # 本包 core：_TrackedLLMAdapter（LLM 适配）
│   ├── settings.py             # 本包 settings：ResearchSettings + AsyncContextSerializer + _FormatDict
│   ├── models.py
│   ├── engine.py
│   ├── callbacks.py
│   └── prompts.py
│
├── paper_ranker/             # ③ 论文综合排序
│   ├── __init__.py
│   ├── core.py                 # 本包 core：embedding / 数值工具（如有需要）
│   ├── settings.py             # 本包 settings：排名相关（目前并入 ResearchSettings，可保留空文件）
│   ├── ranker.py
│   ├── embedder.py
│   └── mmr.py
│
├── synthesis/                 # ④ 搜索结果归纳整理
│   ├── __init__.py
│   ├── core.py                 # 本包 core：答案合成工具
│   ├── settings.py             # 本包 settings：合成相关（若需要可独立；目前可保留空文件）
│   ├── models.py
│   ├── builder.py
│   └── sse_formatter.py
│
├── metadata_clients/         # ⑤ 学术元数据客户端（数据怎么来）
│   ├── __init__.py
│   ├── core.py                 # 本包 core：HTTP 通用工具 / 异常基类（如有需要）
│   ├── settings.py             # 本包 settings：metadata 专属（若需要可独立；目前可保留空文件）
│   ├── academic_search.py
│   ├── client_models.py
│   ├── crossref.py
│   ├── semantic_scholar.py
│   ├── openalex.py
│   ├── unpaywall.py
│   ├── journal_quality.py
│   ├── retractions.py
│   └── exceptions.py
│
├── server/                    # ⑦ HTTP 接口（FastAPI）
│   ├── __init__.py
│   ├── app.py
│   ├── bridge.py
│   ├── dependencies.py
│   ├── events.py
│   ├── repository.py
│   ├── schemas.py
│   ├── sse_callback.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── graph.py
│   │   ├── history.py
│   │   ├── papers.py
│   │   ├── sessions.py
│   │   ├── settings.py        # 合并后的 Settings 路由（薄封装）
│   │   └── usage.py
│
├── configs/                   # 预设配置 JSON
│   ├── __init__.py
│   ├── high_quality.json
│   ├── fast.json
│   └── ...
│
├── _ldp_shims.py             # 兼容性垫片（保留）
└── version.py                 # 版本号（保留在根）
```

### 1.1 功能包结构总览（赛题功能视角）

| 赛题功能 | 包名 | 入口模块 | 关键类/函数 |
|---|---|---|---|
| ① 查询理解与分解 | `query_understanding/` | `analyze.py` | `analyze_and_expand_query`、`QueryUnderstanding` |
| ② 自主搜索策略迭代优化 | `iterative_search/` | `engine.py` | `ResearchEngine.arun()` |
| ③ 论文综合排序 | `paper_ranker/` | `ranker.py` | `score_papers`、`rank_with_mmr`、`RelevanceTier` |
| ④ 搜索结果归纳整理 | `synthesis/` | `builder.py` | `build_evidence_and_answer`、`AnswerSummary` |
| ⑤ 学术元数据客户端 | `metadata_clients/` | `academic_search.py` | `AcademicSearchClient` |
| ⑥ 文档问答 (RAG) | `literature_qa/` | `main.py` | `agent_query`、`ask` |
| ⑦ HTTP 接口 | `server/` | `app.py` | `app` (FastAPI) |

### 1.2 每个功能包内部统一结构

每个功能包遵循 **统一目录结构**：

```
<feature_package>/
├── __init__.py
├── core.py              # 本包专属的 core（基础类型 / 工具 / LLM 适配）
├── settings.py          # 本包专属的 settings（Pydantic BaseModel / 配置）
├── models.py            # 本包业务模型（数据类）
├── <entry_module>.py    # 主入口
└── ...
```

**判断标准**：
- **core.py**：放**仅本包使用**的核心设施（`Docs` 类 → `literature_qa/core.py`；`_TrackedLLMAdapter` → `iterative_search/core.py`）
- **settings.py**：放**仅本包使用**的 Settings（`AnswerSettings`/`ParsingSettings`/`PromptSettings`/`IndexSettings`/`AgentSettings` → `literature_qa/settings.py`；`ResearchSettings` → `iterative_search/settings.py`）
- **多包复用**（≥2 个功能包都用）：放 **`evoscholar/utils/`** 顶层共享文件夹（按子模块分文件：`utils/paths.py`、`utils/llms.py` 等）
- **单包使用**：放该包自己的 `core.py`，不要污染 utils/

**owner 唯一性原则**：同一个核心类型只能有一个 owner。
- `Docs` 的 owner = `literature_qa`（即使 `iterative_search` 也需要它，也通过 `from evoscholar.literature_qa.core import Docs` 引用）
- `ResearchSettings` 的 owner = `iterative_search`
- 没有"跨包独立 core"（`evoscholar/core/`、`evoscholar/settings/` 目录被拆解到各功能包内）

**视觉关系**：

```
                    ┌──────────────────┐
                    │      server       │ ← 唯一外部入口
                    └─────────┬────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌─────────────────┐    ┌──────────────┐
│literature_qa │    │  synthesis       │    │iterative_search│
│   (RAG)      │    │  (归纳整理)      │    │  (迭代搜索)    │
└──────┬───────┘    └────────┬────────┘    └──────┬────────┘
       │                     │                     │
       │                     │           ┌─────────┴────────┐
       │                     │           ▼                  ▼
       │                     │  ┌──────────────┐  ┌──────────────┐
       │                     │  │ query_       │  │ paper_ranker  │
       │                     │  │ understanding │  │  (排序)       │
       │                     │  └──────────────┘  └──────────────┘
       │                     │                     │
       └─────────────────────┴─────────────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ metadata_clients  │ ← 只被 query_understanding /
                    │  (HTTP 搬运)      │       iterative_search 调用
                    └──────────────────┘
```

---

## 2. 各目录职责

| 目录 | 职责 |
|---|---|
| `literature_qa/` | 文档问答 (RAG)：文档索引、RAG evidence 聚合、agent 工具集；本包 `core.py` 持有 `Docs`/`DocDetails`/`PQASession`，本包 `settings.py` 持有 `AnswerSettings`/`ParsingSettings`/`PromptSettings`/`IndexSettings`/`AgentSettings` |
| `query_understanding/` | 查询理解与分解：意图分析、领域识别、子查询分解、查询扩展；本包 `core.py`/`settings.py` 留空或按需 |
| `iterative_search/` | 自主搜索策略迭代优化：LLM 驱动 BFS 搜索循环、引用图扩展、预算控制；本包 `core.py` 持有 `_TrackedLLMAdapter`，本包 `settings.py` 持有 `ResearchSettings` + `AsyncContextSerializer` + `_FormatDict` |
| `paper_ranker/` | 论文综合排序：向量相关性、词汇相关性、综合打分、MMR 多样性、双阈值分级；本包 `core.py`/`settings.py` 按需 |
| `synthesis/` | 搜索结果归纳整理：evidence 聚合、答案合成、按意图分组、SSE 事件格式化；本包 `core.py`/`settings.py` 按需 |
| `metadata_clients/` | 学术元数据 API 封装（Crossref/SemanticScholar/OpenAlex/Unpaywall 等）；本包 `core.py`/`settings.py` 按需 |
| `server/` | FastAPI HTTP 接口，调用功能包，是**唯一**外部入口 |
| `utils/` | 跨包共享的多包复用工具（≥2 个功能包都需要的代码）。按子模块分文件：`paths.py` / `llms.py` / `math_utils.py` 等。**慎用**：放进来就意味着所有包都能引用，等于变相"共享 core"，必须严格控制 |

---

## 3. 模块迁移映射表

### 3.1 agents/ → literature_qa/

| 原路径 | 新路径 | 备注 |
|---|---|---|
| `agents/__init__.py` | `literature_qa/__init__.py` | 导出 `agent_query`, `index_search`, `ask`, `search_query`, `build_index` |
| `agents/env.py` | `literature_qa/env.py` | |
| `agents/tools.py` | `literature_qa/tools.py` | 移除 `ClinicalTrialsSearch`（已清理） |
| `agents/main.py` | `literature_qa/main.py` | |
| `agents/models.py` | `literature_qa/models.py` | |
| `agents/search.py` | `literature_qa/search.py` | |
| `agents/helpers.py` | `literature_qa/helpers.py` | |

### 3.2 research/ → 4 个功能包

**包名选择**（按赛题功能划分）：

| 新包 | 中文 | 职责 | 颜色标记 |
|---|---|---|---|
| `query_understanding/` | ① 查询理解与分解 | 意图分析、领域识别、子查询分解、查询扩展 | 🟦 |
| `iterative_search/` | ② 自主搜索策略迭代优化 | LLM 驱动 BFS 循环、引用图扩展、预算控制 | 🟩 |
| `paper_ranker/` | ③ 论文综合排序 | 向量/词汇相关性、综合打分、MMR 多样性 | 🟨 |
| `synthesis/` | ④ 搜索结果归纳整理 | evidence 聚合、答案合成、SSE 事件格式化 | 🟪 |

#### 3.2.1 query_understanding/ 迁移

| 原路径 | 新路径 | 备注 |
|---|---|---|
| `research/query_understanding.py` | `query_understanding/analyze.py` | `analyze_and_expand_query()` + 启发式兜底 |
| `research/models.py:QueryIntent` | `query_understanding/models.py` | 6 类意图枚举 |
| `research/models.py:Domain` | `query_understanding/models.py` | 12 类领域 + 别名 |
| `research/models.py:SubQuery` | `query_understanding/models.py` | 子查询模型 |
| `research/models.py:QueryUnderstanding` | `query_understanding/models.py` | 整体理解结果 |
| `research/prompts.py:QUERY_UNDERSTANDING_*` | `query_understanding/prompts.py` | 理解与扩展的 prompt |

#### 3.2.2 iterative_search/ 迁移

| 原路径 | 新路径 | 备注 |
|---|---|---|
| `research/engine.py` | `iterative_search/engine.py` | `ResearchEngine`：BFS / follow-up / 引用扩展 |
| `research/callbacks.py` | `iterative_search/callbacks.py` | `ResearchProgressCallback` |
| `research/models.py:StopReason` | `iterative_search/models.py` | 6 种终止原因 |
| `research/models.py:CitationEdge` | `iterative_search/models.py` | 引用图边 |
| `research/models.py:AcademicPaper` | `iterative_search/models.py` | 论文模型（业主） |
| `research/models.py:SearchRound` | `iterative_search/models.py` | 搜索轮次 |
| `research/models.py:ResearchSession` | `iterative_search/models.py` | 整个 search session |
| `research/models.py:SearchResult` | `iterative_search/models.py` | 搜索结果封装 |
| `server/routes/sessions.py:_run_research_engine` | `iterative_search/engine.py` 中相应位置 | 业务逻辑下移（可选，§4.2 详述） |

#### 3.2.3 paper_ranker/ 迁移

| 原路径 | 新路径 | 备注 |
|---|---|---|
| `research/ranking.py:score_papers / ascore_papers` | `paper_ranker/ranker.py` | 综合打分 |
| `research/ranking.py:_assign_scores` | `paper_ranker/ranker.py` | 多因子加权 |
| `research/ranking.py:_lexical_relevance` | `paper_ranker/ranker.py` | 词汇相关性兜底 |
| `research/ranking.py:_embed_texts / _cosine` | `paper_ranker/embedder.py` | embedding 相关 |
| `research/ranking.py:rank_with_mmr` | `paper_ranker/mmr.py` | 多样性排序 |
| `research/models.py:RelevanceTier` | `paper_ranker/ranker.py` 或 `paper_ranker/__init__.py` | HIGH / PARTIAL 分级 |

#### 3.2.4 synthesis/ 迁移

| 原路径 | 新路径 | 备注 |
|---|---|---|
| `research/engine.py:_build_evidence_and_answer` | `synthesis/builder.py` | evidence 聚合 + 答案合成 |
| `research/models.py:EvidenceSnippet` | `synthesis/models.py` | 证据片段 |
| `research/models.py:AnswerSummary` | `synthesis/models.py` | 答案总结 |
| `research/models.py:UsageStats` | `synthesis/models.py` | 使用统计（按 token / API 调用） |
| `server/routes/sessions.py:SSE_*` 事件构造 | `synthesis/sse_formatter.py` | SSE 事件格式化（**注意**：传输协议仍在 server） |
| `server/sse_callback.py` 部分格式化逻辑 | `synthesis/sse_formatter.py` | SSE payload 字段生成 |

#### 3.2.5 设计决策：AcademicPaper 的归属

**问题**：`AcademicPaper` 类型既被 `metadata_clients/academic_search.py` 导入（构造 paper），又被 `iterative_search/engine.py` 用（编排 paper），还被 `synthesis/` 用（合成答案）。

**决策**：放 `iterative_search/models.py`（业务编排层），不放在 `metadata_clients/`。

**理由**：
1. `metadata_clients` 是 **HTTP 搬运工**，它的职责是"调用 API 返回 raw json"。raw json 是 dict，不是 `AcademicPaper`。
2. `AcademicSearchClient`（在 `metadata_clients/academic_search.py`）做了 raw json → `AcademicPaper` 的转换，但**这是搜索层面的组装工作**，不是元数据 API 的责任。
3. 放到 `iterative_search/models.py` 后，`metadata_clients/academic_search.py` 需要 `from ..iterative_search.models import AcademicPaper`。这是**反向依赖**，破坏了"metadata_clients 是底层"的层序。

**替代方案**（如果反向依赖不可接受）：把 `AcademicPaper` 提至 `core/models.py`。

**最终建议**：保留 `AcademicPaper` 在 `iterative_search/`，`metadata_clients` 通过 import 引用。理由：
- `metadata_clients` 不被 `iterative_search` 直接依赖（`engine.py` 通过 `AcademicSearchClient` 接口调用，**不需要**直接 import `AcademicPaper`）
- `metadata_clients` 只在 `academic_search.py` 一处构造 `AcademicPaper`，这是细枝末节，不影响层序
- 把 `AcademicPaper` 放到 `iterative_search/` 语义更清晰（论文是搜索的产物，不是 API 的产物）

#### 3.2.6 拆分顺序与依赖

4 个新包之间存在严格依赖关系，**必须按以下顺序 commit**：

```
query_understanding  ──→  iterative_search  ──→  paper_ranker
        │                    │                       │
        │                    │                       ↓
        │                    │                   synthesis
        │                    └──────────────────────→↓
        └──────────────────────────────────────────────↓
metadata_clients  ────────────────────────────────────↓
```

依赖矩阵（行依赖列）：

|        | query_understanding | iterative_search | paper_ranker | synthesis | metadata_clients |
|--------|---------------------|------------------|--------------|-----------|------------------|
| query_understanding | — | | | | |
| iterative_search | ✅ | — | | | ✅ |
| paper_ranker | | ✅ (用 AcademicPaper) | — | | |
| synthesis | | ✅ (用 StopReason / SearchRound) | ✅ (用 RelevanceTier) | — | |
| metadata_clients | | | | | — |

**Commit 顺序（必须）**：
1. `query_understanding`（无依赖）
2. `iterative_search`（依赖 query_understanding + metadata_clients）
3. `paper_ranker`（依赖 iterative_search 的 AcademicPaper 类型）
4. `synthesis`（依赖 iterative_search + paper_ranker）

> **关键**：`paper_ranker` 之所以依赖 `iterative_search` 而非反过来，原因是 `engine.py` 在搜索循环里调用 `ranking`（见 `research/engine.py:533`、`engine.py:569`）。搜索先取候选 → 排序 → 决定下一轮。

### 3.3 clients/ → metadata_clients/

| 原路径 | 新路径 | 备注 |
|---|---|---|
| `clients/__init__.py` | `metadata_clients/__init__.py` | 导出 `DocsClients`, `MetadataClients` |
| `clients/academic_search.py` | `metadata_clients/academic_search.py` | 赛题搜索核心，需保留 |
| `clients/client_models.py` | `metadata_clients/client_models.py` | |
| `clients/crossref.py` | `metadata_clients/crossref.py` | |
| `clients/semantic_scholar.py` | `metadata_clients/semantic_scholar.py` | |
| `clients/openalex.py` | `metadata_clients/openalex.py` | |
| `clients/unpaywall.py` | `metadata_clients/unpaywall.py` | |
| `clients/journal_quality.py` | `metadata_clients/journal_quality.py` | |
| `clients/retractions.py` | `metadata_clients/retractions.py` | |
| `clients/exceptions.py` | `metadata_clients/exceptions.py` | |

### 3.4 根目录文件 → core/

| 原路径 | 新路径 | 备注 |
|---|---|---|
| `docs.py` | `core/docs.py` | `Docs` 类是跨包共享的核心类型 |
| `types.py` | `core/types.py` | |
| `prompts.py` | `core/prompts.py` | |
| `readers.py` | `core/readers.py` | |
| `llms.py` | `core/llms.py` | |
| `utils.py` | `core/utils.py` | |
| `paths.py` | `core/paths.py` | |

### 3.5 settings 下沉到各功能包（替换 §3.5 原方案）

**原方案**：把 `settings.py`（1356 行）拆成顶层 `settings/` 子包（`settings_answer.py`、`settings_parsing.py`、...）。

**新方案**：**删除顶层 `settings/`，每个功能包有自己的 `settings.py`**，该包专属的 Settings 类下沉到对应包。

#### 3.5.1 Settings 归属映射

| Settings 子类 | 行数估算 | 新归属 | 备注 |
|---|---|---|---|
| `AnswerSettings` | ~130 | `literature_qa/settings.py` | 答案生成配置 |
| `ParsingSettings`, `ChunkingOptions`, `MultimodalOptions` | ~170 | `literature_qa/settings.py` | PDF 解析分块配置 |
| `PromptSettings` | ~115 | `literature_qa/settings.py` | RAG Prompt 配置 |
| `IndexSettings` | ~95 | `literature_qa/settings.py` | 索引配置 |
| `AgentSettings` | ~140 | `literature_qa/settings.py` | Agent 配置 |
| `ResearchSettings` | ~30 | `iterative_search/settings.py` | 搜索循环配置 |
| `AsyncContextSerializer` (Protocol) | ~12 | `iterative_search/settings.py` | 辅助 Protocol |
| `_FormatDict` | ~15 | `iterative_search/settings.py` | 辅助 dict |
| 主 `Settings` 类 + `get_settings()` | ~80 | `literature_qa/settings.py`（主）+ 各功能包按需 re-export | 主聚合类 |

#### 3.5.2 主 Settings 聚合策略

主 `Settings` 类作为根入口，**保留在 `literature_qa/settings.py`**（因为其他 Settings 都在 literature_qa 体系内），但**作为 re-export 入口**让其他包能 `from evoscholar.iterative_search.settings import ResearchSettings` 直接 import。

主 Settings 字段聚合：
```python
# literature_qa/settings.py
class Settings(BaseSettings):
    answer: AnswerSettings = Field(default_factory=AnswerSettings)
    parsing: ParsingSettings = Field(default_factory=ParsingSettings)
    prompts: PromptSettings = Field(default_factory=PromptSettings)
    index: IndexSettings = Field(default_factory=IndexSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)

# 跨包引用示例：iterative_search 通过共享基类接入
class Settings(BaseSettings):
    literature_qa: LiteratureQASettings = Field(...)   # 来自 literature_qa.settings
    research: ResearchSettings = Field(default_factory=ResearchSettings)
```

**简化方案**（推荐）：保留扁平的主 `Settings`，但 Settings 的字段直接 re-export 各功能包的 Settings：

```python
# literature_qa/settings.py - 主入口
from ._answer import AnswerSettings
from ._parsing import ParsingSettings, ChunkingOptions, MultimodalOptions
from ._prompts import PromptSettings
from ._index import IndexSettings
from ._agent import AgentSettings

# 跨包 Settings 直接 re-export（仅做引用，不重新声明）
from evoscholar.iterative_search.settings import ResearchSettings

class Settings(BaseSettings):
    answer: AnswerSettings = Field(...)
    parsing: ParsingSettings = Field(...)
    # ...
    research: ResearchSettings = Field(default_factory=ResearchSettings)
```

#### 3.5.3 `utils/` 的设计

某些工具是**多包复用**的（≥2 个独立功能包都需要），放 **`evoscholar/utils/`** 顶层共享文件夹（按子模块分文件）。

```
utils/
├── __init__.py
├── paths.py            # 路径管理常量（绝对路径、缓存目录等）
├── llms.py             # 通用 LLM 工厂函数（与具体业务无关的 model 加载）
├── math_utils.py       # cosine_similarity / normalize / 通用数值工具
├── string_utils.py     # 字符串处理（截断 / 转义 / 等）
└── ...                 # 按需新增，不强制一开始就建全部
```

**判断标准**：
- 至少 **2 个独立功能包**需要 → 进 `utils/`
- 仅 1 个包需要 → 进该包 `core.py`
- **server 自己用到的辅助**也可以放 `utils/`（不限于功能包）

**禁止往 utils/ 放的**：
- 业务模型（如 `AcademicPaper`、`ResearchSession`）→ 放各包 `models.py`
- Settings 子类 → 放各包 `settings.py`
- 业务专用的辅助（如 `_TrackedLLMAdapter`）→ 放各包 `core.py`

#### 3.5.4 server 自己的字段

**保留在 `server/routes/settings.py`**（薄封装层），不进任何功能包。理由：HTTP 配置和 LLM/检索配置语义不同，放一起会让序列化时混淆。

### 3.6 迁移脚本映射

```bash
# agents/ → literature_qa/  （Commit 0 已将 src/paperqa 重命名为 src/evoscholar，下同）
mv src/evoscholar/agents src/evoscholar/literature_qa
# 在 literature_qa/ 内创建 core.py 和 settings.py（从根目录 core 文件和 settings.py 抽取后填入）
touch src/evoscholar/literature_qa/core.py src/evoscholar/literature_qa/settings.py

# research/ → 4 个功能包（按依赖顺序拆）
# ① query_understanding
mkdir src/evoscholar/query_understanding
touch src/evoscholar/query_understanding/core.py src/evoscholar/query_understanding/settings.py
mv src/evoscholar/research/query_understanding.py src/evoscholar/query_understanding/analyze.py
# 提取相关模型（QueryIntent/Domain/SubQuery/QueryUnderstanding）到 src/evoscholar/query_understanding/models.py
# 提取相关 prompt 到 src/evoscholar/query_understanding/prompts.py

# ② iterative_search
mkdir src/evoscholar/iterative_search
touch src/evoscholar/iterative_search/core.py
mv src/evoscholar/research/engine.py src/evoscholar/iterative_search/engine.py
mv src/evoscholar/research/callbacks.py src/evoscholar/iterative_search/callbacks.py
# 提取相关模型（StopReason/CitationEdge/AcademicPaper/SearchRound/ResearchSession/SearchResult）到 src/evoscholar/iterative_search/models.py
# iterative_search/settings.py 在 settings 拆分 commit 中创建（见 §7 Commit 11）

# ③ paper_ranker
mkdir src/evoscholar/paper_ranker
touch src/evoscholar/paper_ranker/core.py src/evoscholar/paper_ranker/settings.py
mv src/evoscholar/research/ranking.py src/evoscholar/paper_ranker/ranker.py
# 拆分：embedder.py / mmr.py
# 提取 RelevanceTier 到 src/evoscholar/paper_ranker/ranker.py

# ④ synthesis
mkdir src/evoscholar/synthesis
touch src/evoscholar/synthesis/core.py src/evoscholar/synthesis/settings.py
# 分离 _build_evidence_and_answer 到 src/evoscholar/synthesis/builder.py
# 提取 AnswerSummary / EvidenceSnippet / UsageStats 到 src/evoscholar/synthesis/models.py
# 从 server/ 提取 SSE 事件格式化逻辑到 src/evoscholar/synthesis/sse_formatter.py

# 清理空目录
rmdir src/evoscholar/research  # 确认全空

# clients/ → metadata_clients/
mv src/evoscholar/clients src/evoscholar/metadata_clients
touch src/evoscholar/metadata_clients/core.py src/evoscholar/metadata_clients/settings.py

# 顶层 utils/ 创建（多包复用的纯工具）
mkdir src/evoscholar/utils
touch src/evoscholar/utils/__init__.py

# 根目录文件 → 各包 core.py 或 utils/
#   docs.py / types.py / readers.py / utils/ 内容  → literature_qa/core.py（主 owner）
#   paths.py  → utils/paths.py
#   llms.py  → utils/llms.py
#   prompts.py → literature_qa/core.py（随 Docs 一起 owner）

# settings.py → 各包 settings.py（按 §3.5.1 映射）
#   AnswerSettings / ParsingSettings / PromptSettings / IndexSettings / AgentSettings / 主 Settings → literature_qa/settings.py
#   ResearchSettings / AsyncContextSerializer / _FormatDict → iterative_search/settings.py
```

### 3.7 包重命名：paperqa → evoscholar

旧包名 `paperqa` → 新包名 **`evoscholar`**（evolutionary scholar agent：自进化论文搜索代理）

| 用途 | 名称 |
|---|---|
| 顶层目录 | `src/evoscholar/` |
| Python 包名 | `evoscholar` |
| pyproject.toml `name` | `evoscholar` |
| import 路径 | `from evoscholar import ...` |
| CLI 命令 | `evoscholar` |

> **回退兼容**：在 `pyproject.toml` 中保留 `paperqa` 作为 alias / extra-name。
> **完整模块替换** 见 §7 Commit 0。

---

## 4. 架构关系图

### 4.1 跨包依赖关系

```
server/                ← 唯一外部接口
  │
  ├── literature_qa/       (RAG / QA)
  │     └── 调用 metadata_clients/ 获取 paper 元数据
  │
  ├── synthesis/           (结果归纳整理)
  │     ├── 接收 iterative_search 的轮次结果
  │     ├── 接收 paper_ranker 的 RelevanceTier
  │     └── 提供 SSE 事件格式化（被 server 消费）
  │
  ├── iterative_search/    (自主搜索策略迭代优化)
  │     ├── 调用 query_understanding/ 分解子查询
  │     ├── 调用 metadata_clients/ 搜索学术论文
  │     └── 调用 paper_ranker/ 排序候选
  │
  ├── query_understanding/ (查询理解与分解)
  │     └── 独立，无入向依赖
  │
  ├── paper_ranker/        (论文综合排序)
  │     └── 依赖 iterative_search 的 AcademicPaper 类型
  │
  └── metadata_clients/    (which sources)
        └── 独立，仅依赖 core/
```

### 4.2 业务逻辑下沉建议

`server/routes/sessions.py:_run_research_engine`（约 200 行）当前夹杂了：
- 搜索会话的创建/状态管理
- SSE 事件推送
- 业务循环编排（计划下沉到 `iterative_search`）

**建议下沉**：
- `server/routes/sessions.py` 只保留：HTTP 路由 + SSE 推送 + 错误处理
- 业务循环（搜索 + 排序 + 引用扩展 + 终止判断）→ `iterative_search/engine.py`
- SSE 事件 payload 构造 → `synthesis/sse_formatter.py`

**理由**：让 `iterative_search` 可独立测试（不依赖 FastAPI / SSE），便于未来以 CLI 或 notebook 形式调用。

### 4.3 clients/ 不并入 literature_qa/

**保留在 `metadata_clients/`，不并入 `literature_qa/`**

理由：
1. `AcademicSearchProvider` 是 `iterative_search` 依赖的接口，不是 `literature_qa`
2. `metadata_clients/` 的所有客户端（Crossref、SemanticScholar、OpenAlex、Unpaywall）都是**元数据提供者**，与 `literature_qa` 的 RAG 逻辑无直接依赖
3. `literature_qa` 通过 `metadata_clients` 获取文档元数据，两者是**生产者-消费者**关系，而非同一模块内的代码

### 4.4 data 流向（一次完整 search 调用）

```
1. user query
   ↓
2. server 接收请求
   ↓
3. query_understanding.analyze_and_expand_query()  →  SubQuery[]
   ↓
4. iterative_search.engine.run_session():          →  ResearchSession
   │
   ├── metadata_clients.AcademicSearchClient.search(SubQuery)  →  AcademicPaper[]
   │
   └── paper_ranker.score_papers()  →  ranked[AcademicPaper]
   ↓
5. synthesis.builder.build_evidence_and_answer()   →  AnswerSummary
   ↓
6. synthesis.sse_formatter.format_*()              →  SSE 事件 payload
   ↓
7. server.stream() 推送 SSE
```

---

## 5. 两个 Settings 合并方案

当前问题：
- `src/paperqa/settings.py`（1356 行）：PaperQA 内部配置（Answer/Parsing/Prompt/Index/Agent/Research）
- `src/paperqa/server/routes/settings.py`（151 行）：Server 层 researcher 配置（llm/阈值/轮次）

两者有大量字段重复（`researcher_llm`, `summary_llm`, `max_rounds` 等），且 `server/routes/settings.py` 是独立 dict，不继承自任何 Pydantic 类。

**推荐方案：server 改为薄封装，直接读写顶层 `Settings` 实例**

不再把 server 字段塞进 `settings/` 包，因为：
- server 配置是 **HTTP 层特有的运行时状态**（API key 是否存在、CORS、API base URL），不应该污染核心 `Settings`（核心 `Settings` 是构建 `Docs` / `ResearchEngine` 时用的，跟 HTTP 无关）
- 把 server 字段塞进 `Settings` 会让所有 LLM 配置序列化时夹带 HTTP 字段
- 真正要做的是：让 `server/routes/settings.py` 的接口读写**主 Settings 实例**（存到 `app.state.settings`），不再用独立的 `_current_settings` dict

具体步骤：
1. 在 `server/app.py` 启动时实例化主 `Settings` → 存入 `app.state.settings`（替代原来的 `_current_settings`）
2. `server/routes/settings.py` 的 `GET/PUT` 改为读写 `request.app.state.settings`
3. `_SETTINGS_DEFAULTS` 删除（不再需要镜像默认值，主 Settings 的字段默认值就是默认值）
4. `SettingsPayload` (server/schemas.py) 中重复字段（如 `max_rounds`、`thresholds`、`researcher_llm`）改为引用主 Settings 的字段类型

**风险**：Server 层原来用独立 dict 避免暴露 API key；合并后需确保 API key 仍然通过 `Settings.llm_api_key` 的 `exclude=True` 不序列化到客户端响应中。

---

## 6. 导入兼容策略（Shim 层）

删除旧路径后，必须保证外部 import 不崩溃。

### 6.1 paperqa 模块兼容

在 `paperqa/__init__.py` 中添加兼容导出：

```python
# 兼容旧导入路径
from paperqa.literature_qa import (
    ask,
    agent_query,
    search_query,
    build_index,
)
from paperqa.iterative_search import ResearchEngine
from paperqa.metadata_clients import (
    CrossrefProvider,
    SemanticScholarProvider,
    OpenAlexProvider,
    # ...
)

# 保留主 Settings 在根路径
from paperqa.settings import Settings, get_settings, ParsingSettings
```

### 6.2 旧导入路径垫片（可选，长期可废弃）

```python
# paperqa/agents/__init__.py → 添加 shim 警告
import warnings

warnings.warn(
    "paperqa.agents is deprecated, use paperqa.literature_qa",
    DeprecationWarning,
    stacklevel=2,
)
from paperqa.literature_qa import *
```

### 6.3 内部跨包导入原则

重构后，各包之间通过以下方式通信：

**允许的依赖方向**：

| 来源包 | 可调用 | 不可调用 |
|---|---|---|
| `metadata_clients` | `utils/*` | 所有其他业务包 |
| `query_understanding` | `utils/*`, `metadata_clients` | `iterative_search`, `paper_ranker`, `synthesis` |
| `iterative_search` | `utils/*`, `query_understanding`, `metadata_clients`, `paper_ranker`, `literature_qa.core` (Docs/Text) | `synthesis` |
| `paper_ranker` | `utils/*`, `iterative_search` | `query_understanding`, `synthesis` |
| `synthesis` | `utils/*`, `iterative_search`, `paper_ranker` | `query_understanding`, `metadata_clients` |
| `server` | 全部 | — |
| `literature_qa` | `utils/*`, `metadata_clients` | `query_understanding`, `iterative_search`, `paper_ranker`, `synthesis` |

**关于"共享代码"的来源**：
- **`utils/*`**：多包复用工具（≥2 个包都用），如 `paths.py` / `llms.py` / `math_utils.py`。所有功能包可引用
- **其他包 `core.py`**：单包专属，仅 owner 自己用；其他包若需要 import 该包 owner 的类型（如 `iterative_search` 需要 `Docs`），是**允许**的（因为 `Docs` 是 owner 的产物，引用是正常消费）
- **禁止**：跨包 `core.py`/`settings.py` 内部互相调用对方的私有 helper（仅可 import 对方 `models.py`/`__init__.py` 暴露的公开类型）

**铁律**：
- `literature_qa` 与 `iterative_search` **业务代码互不依赖**（RAG 路径 vs 搜索路径，独立）。但双方都可通过 `utils/` 或对方的**公开类型**（如 `Docs`）消费
- `query_understanding` **不知道** `iterative_search` 存在（用户提问时只做理解，不做搜索）
- `synthesis` **不调用** `metadata_clients`（整理结果时不需要再搜）
- `server` 是**唯一**可以调用所有业务层的层

**非法方向示例**（会被 commit hook 拦截）：
```python
# ❌ synthesis 直接 import metadata_clients
from evoscholar.metadata_clients import AcademicSearchClient

# ❌ literature_qa 直接 import iterative_search 的 engine
from evoscholar.iterative_search.engine import ResearchEngine

# ❌ query_understanding import paper_ranker
from evoscholar.paper_ranker import ascore_papers

# ❌ 业务包 import utils/* 之外的其他业务包的私有 helper
from evoscholar.iterative_search.core import _TrackedLLMAdapter  # _ 前缀是私有
```

### 6.4 Prompt 文件职责边界（防重复）

迁移后预计有 **5 个** prompts 文件，按归属包拆分（**禁止跨包合并**）：

| 文件 | 内容 | 调用方 | 迁移后位置 |
|---|---|---|---|
| 原 `prompts.py`（根） | `QA_PROMPT_TEMPLATE`、`CONTEXT_INNER/OUTER_PROMPT`、`CITATION_KEY_CONSTRAINTS`、`CANNOT_ANSWER_PHRASE` | `Docs.aget_evidence()`、`Docs.aquery()` | **`literature_qa/core.py`**（随 Docs 一起 owner） |
| `query_understanding/prompts.py` | `QUERY_UNDERSTANDING_PROMPT`、`QUERY_UNDERSTANDING_SYSTEM` | `query_understanding/analyze.py` | `query_understanding/prompts.py`（独立） |
| `iterative_search/prompts.py` | （若新增）搜索循环中 LLM 决策 prompt，例如"是否继续搜索" | `iterative_search/engine.py` | `iterative_search/prompts.py` |
| `paper_ranker/prompts.py` | （若新增）LLM 辅助评分的 prompt | `paper_ranker/ranker.py` | `paper_ranker/prompts.py` |
| `synthesis/prompts.py` | 答案合成 prompt（如 "summarize the following evidence"） | `synthesis/builder.py` | `synthesis/prompts.py` |

**判定**：**全部不重复**，因为每个 prompt 服务于一个独立业务流**语义层不重叠**：

- `literature_qa/core.py` 内的 prompts 不知道搜索路径，反之亦然
- `query_understanding/prompts.py` 是"理解"专用
- `synthesis/prompts.py` 是"合成"专用（即便都是基于 LLM，prompt 喂入的数据不同）

**注意**：`literature_qa/settings.py` 内的 `PromptSettings` 是**配置**（存 LLM prompt 的 metadata），不是 prompt 文本本身，与上面 5 个文件不冲突。

**检查清单**（避免后续有人合并）：
```bash
rg "from evoscholar.query_understanding.prompts" src/evoscholar/iterative_search/  # 应为 0
rg "from evoscholar.paper_ranker.prompts" src/evoscholar/synthesis/  # 应为 0
rg "from evoscholar.iterative_search.prompts" src/evoscholar/query_understanding/  # 应为 0
```

---

## 7. 分阶段执行计划

### Commit 0：包重命名 paperqa → evoscholar（低风险）

**内容**：
- `git mv src/paperqa src/evoscholar`
- 修改 `pyproject.toml`：`name = paperqa` → `name = evoscholar`，保留 `[project.entry-points."paperqa"]` 之类的 alias
- 替换所有内部 `from paperqa.xxx` → `from evoscholar.xxx`（用 `sed -i 's|from paperqa|from evoscholar|g'` 或 `rg -l "from paperqa" | xargs sed -i ...`）
- 替换所有字符串字面量 `"paperqa"` → `"evoscholar"`（注意 `pyproject.toml` 里的 tool 段、README）

**风险**：低，纯重命名。但 commit 内容多，需要确保 grep 替换不漏文件。

**验证**：
```bash
python -c "from evoscholar import Docs"
python -c "from paperqa import Docs"  # 兼容期允许失败
rg "from paperqa" src/ tests/  # 应该为 0
```

> 备注：此 commit **必须在所有功能包迁移之前**完成，否则 import 路径改一次不够。

---

### Commit 1：基础设施准备（低风险）

**内容**：
- 创建 `core/`, `literature_qa/`, `query_understanding/`, `iterative_search/`, `paper_ranker/`, `synthesis/`, `metadata_clients/`, `settings/` 目录结构
- 创建各目录的 `__init__.py`（留空或简单导出）
- 创建 `configs/` 目录 `__init__.py`

**风险**：低。纯新建文件，无破坏性。

**验证**：`python -c "import evoscholar"` 不崩

---

### Commit 2：迁移 clients/ → metadata_clients/（低风险）

**内容**：
- 将 `clients/*.py` 移动到 `metadata_clients/`
- 更新 `clients/academic_search.py` 中 `from ..research.models` → `from ..iterative_search.models`（详见 §3.2.5 关于 `AcademicPaper` 归属的决策）
- 更新 `metadata_clients/__init__.py` 导出
- 添加 `clients/` → `metadata_clients` 兼容垫片

**风险**：低。clients 无外部依赖，只被 research/engine.py 使用。

**验证**：
```bash
python -c "from evoscholar.metadata_clients import AcademicSearchClient"
python -c "from evoscholar.research import ResearchEngine"  # 旧路径仍兼容
```

---

### Commit 3：迁移 query_understanding/（低风险，独立包）

**内容**：
- `mkdir src/evoscholar/query_understanding`
- `mv src/evoscholar/research/query_understanding.py src/evoscholar/query_understanding/analyze.py`
- 从 `research/models.py` 提取 `QueryIntent`、`Domain`、`SubQuery`、`QueryUnderstanding` → `query_understanding/models.py`
- 提取 `QUERY_UNDERSTANDING_PROMPT` / `QUERY_UNDERSTANDING_SYSTEM` → `query_understanding/prompts.py`
- 更新 `research/engine.py` 的 import（指向新位置）
- 添加 `research/query_understanding.py` → `query_understanding.analyze` 兼容垫片

**风险**：低。query_understanding 是独立叶子包，无依赖。

**验证**：
```bash
python -c "from evoscholar.query_understanding import analyze_and_expand_query, QueryUnderstanding"
python -c "from evoscholar.research.query_understanding import analyze_and_expand_query"  # 垫片
```

---

### Commit 4：迁移 iterative_search/（中等风险）

**内容**：
- `mkdir src/evoscholar/iterative_search`
- `mv src/evoscholar/research/engine.py src/evoscholar/iterative_search/engine.py`
- `mv src/evoscholar/research/callbacks.py src/evoscholar/iterative_search/callbacks.py`
- 从 `research/models.py` 提取 `StopReason`、`CitationEdge`、`AcademicPaper`、`SearchRound`、`ResearchSession`、`SearchResult` → `iterative_search/models.py`
- 更新 `research/ranking.py` 的 import（仍然引用 `AcademicPaper`）
- 更新 `metadata_clients/academic_search.py` 的 import → `from evoscholar.iterative_search.models import AcademicPaper`
- 更新 `server/routes/sessions.py` 的 import
- 添加 `research/` → `iterative_search` 兼容垫片

**风险**：**中等**。`engine.py` 是核心循环，依赖多个模块；`AcademicPaper` 跨包被引用，必须保证 import 路径一致。

**验证**：
```bash
python -c "from evoscholar.iterative_search import ResearchEngine, AcademicPaper"
python -c "from evoscholar.research import ResearchEngine"  # 垫片
python -c "from evoscholar.metadata_clients import AcademicSearchClient"
# 端到端冒烟（无 API key 也能跑基础循环）
python -c "from evoscholar.iterative_search import ResearchEngine; e = ResearchEngine.__init__.__doc__"
```

---

### Commit 5：迁移 paper_ranker/（中等风险）

**内容**：
- `mkdir src/evoscholar/paper_ranker`
- `mv src/evoscholar/research/ranking.py src/evoscholar/paper_ranker/ranker.py`
- 拆分内部：`embedder.py`（`_embed_texts`、`_cosine`）、`mmr.py`（`rank_with_mmr`）
- 从 `research/models.py` 提取 `RelevanceTier` → `paper_ranker/ranker.py`
- 更新 `iterative_search/engine.py` 的 import（指向 paper_ranker）
- 删除 `research/ranking.py`（被 paper_ranker 完全替代，无垫片，因为 ranking.py 是私有模块从未暴露）

**风险**：中等。`ranking.py` 是 700 行的 `engine.py` 紧耦合依赖，拆分时函数归属（ranker vs embedder vs mmr）需要仔细判断。

**验证**：
```bash
python -c "from evoscholar.paper_ranker import score_papers, rank_with_mmr, RelevanceTier"
python -c "from evoscholar.iterative_search import ResearchEngine"  # 仍然可用
```

---

### Commit 6：迁移 synthesis/（中等风险，含 SSE）

**内容**：
- `mkdir src/evoscholar/synthesis`
- 从 `research/engine.py` 提取 `_build_evidence_and_answer` → `synthesis/builder.py`
- 从 `research/models.py` 提取 `EvidenceSnippet`、`AnswerSummary`、`UsageStats` → `synthesis/models.py`
- 从 `server/routes/sessions.py` 提取 SSE 事件 payload 构造 → `synthesis/sse_formatter.py`
- 从 `server/sse_callback.py` 提取字段格式化 → `synthesis/sse_formatter.py`
- 更新 `server/routes/sessions.py`：保留 HTTP 路由 + stream 推送，业务逻辑下沉
- 更新 `iterative_search/engine.py`：调用 `synthesis.builder` 而非内嵌
- 删除 `research/engine.py`（**注意**：这是 research 最后一次被引用）

**风险**：**中等偏高**。业务循环下沉 + SSE 拆分涉及两层边界，必须保证：
1. `_build_evidence_and_answer` 与 `evidence_adapter` 的依赖关系清晰
2. SSE 事件 payload 字段名与前端 `search.ts` 期望一致（参考 `private-docs/roadmap.md` §6 字段映射表）
3. 删除 `research/engine.py` 前确认无悬空引用

**验证**：
```bash
python -c "from evoscholar.synthesis import AnswerSummary, EvidenceSnippet"
python -c "from evoscholar.synthesis.sse_formatter import format_progress_event"
python -c "from evoscholar.iterative_search import ResearchEngine"  # 仍可用，调用 synthesis
python -c "from evoscholar.server.app import app"  # FastAPI 仍可启动
# 字段映射校验（防止遗漏 find phase 字段）
python -c "
from evoscholar.synthesis.sse_formatter import format_usage_event
payload = format_usage_event(tokens=100, cost=0.01, search_calls=5, llm_calls=3)
assert payload['totalTokens'] == 100  # 前端 SearchStats 字段名
assert 'tokenUsage' not in payload  # 旧字段名不能出现
"
```

---

### Commit 7：迁移 agents/ → literature_qa/（中等风险）

**内容**：
- `git mv src/evoscholar/agents src/evoscholar/literature_qa`
- 更新 `literature_qa/__init__.py` 导出（`ask`, `agent_query`, `search_query`, `build_index`）
- 更新 `literature_qa/tools.py` 中的 `from .search import get_directory_index`
- 更新 `literature_qa/main.py` 中的 `from .env import PaperQAEnvironment`
- 创建 `literature_qa/core.py`、`literature_qa/settings.py` 占位文件（实际内容在 Commit 8/9 填充）
- 添加 `agents/` → `literature_qa` 兼容垫片

**风险**：中等。agents 与 core（docs.py, types.py）有较多依赖。

**验证**：
```bash
python -c "from evoscholar.literature_qa import ask, agent_query"
python -c "from evoscholar.agents import ask"  # 垫片
# 配合 literature_qa/main.py 调用 metadata_clients
python -c "from evoscholar.literature_qa.tools import PaperSearch"
```

---

### Commit 8：迁移根目录文件 → 各功能包 core.py + utils/（中等风险）

**内容**：
- 创建 `src/evoscholar/utils/` 目录（含 `__init__.py`）
- 创建 `src/evoscholar/literature_qa/core.py`、`iterative_search/core.py` 等（其他包按需）
- **utils/** 装：
  - `git mv src/evoscholar/paths.py src/evoscholar/utils/paths.py`
  - `git mv src/evoscholar/llms.py src/evoscholar/utils/llms.py`（通用 LLM 工厂部分）
- **literature_qa/core.py** 装：
  - `git mv src/evoscholar/docs.py` → 合并进 `src/evoscholar/literature_qa/core.py`（Docs 类）
  - `git mv src/evoscholar/types.py` → 合并进 `src/evoscholar/literature_qa/core.py`（PQASession/DocDetails/Text）
  - `git mv src/evoscholar/prompts.py` → 合并进 `src/evoscholar/literature_qa/core.py`（RAG prompt 常量）
  - `git mv src/evoscholar/readers.py` → 合并进 `src/evoscholar/literature_qa/core.py`（PDF 解析）
  - `git mv src/evoscholar/utils.py` → 合并进 `src/evoscholar/literature_qa/core.py` + 通用部分抽出到 `utils/`
- **iterative_search/core.py** 装：
  - `_TrackedLLMAdapter`（从 `llms.py` 中分离）
- 更新所有跨包 import 路径（`from evoscholar.docs` → `from evoscholar.literature_qa.core`，`from evoscholar.paths` → `from evoscholar.utils.paths`）

**风险**：中等。所有包都依赖这些核心类型，迁移时需逐文件确认 owner。

**验证**：
```bash
# utils/ 引用
python -c "from evoscholar.utils.paths import *"
python -c "from evoscholar.utils.llms import get_llm_model"

# 各包 core.py
python -c "from evoscholar.literature_qa.core import Docs, DocDetails, PQASession"
python -c "from evoscholar.iterative_search.core import _TrackedLLMAdapter"

# 兜底：确认旧路径失效
python -c "from evoscholar.docs import Docs"  # ImportError
python -c "from evoscholar.paths import *"  # ImportError
```

> **本 commit 不做兼容垫片**：core 化的旧路径（`from evoscholar.docs`）过深，意义不大；若需要兜底，可在 `evoscholar/__init__.py` 一行导出。

---

### Commit 9：拆分 settings.py → 各功能包 settings.py + 合并 Server Settings（中等风险）

**内容**：
- **literature_qa/settings.py** 装：
  - `AnswerSettings` / `ParsingSettings` / `ChunkingOptions` / `MultimodalOptions` / `PromptSettings` / `IndexSettings` / `AgentSettings`
  - 主 `Settings` 类 + `get_settings()`
- **iterative_search/settings.py** 装：
  - `ResearchSettings` / `AsyncContextSerializer` / `_FormatDict`
- 在 `literature_qa/settings.py` 主 Settings 中通过 import 引用 `iterative_search.settings.ResearchSettings`
- 合并 `server/routes/settings.py`：改为薄封装，删 `_SETTINGS_DEFAULTS` dict，改读写 `app.state.settings`（顶层 Settings 实例）
- 更新 `server/app.py`：启动时初始化 `app.state.settings = Settings()`
- 更新 `server/dependencies.py` 等的导入
- 其他功能包（`query_understanding` / `paper_ranker` / `synthesis` / `metadata_clients`）的 `settings.py` 保留空文件占位

**风险**：中等。Settings 是全局配置，修改可能影响所有功能。

**验证**：
```bash
# 主入口
python -c "from evoscholar.literature_qa.settings import Settings, get_settings"
python -c "from evoscholar.literature_qa.settings import AnswerSettings, PromptSettings, IndexSettings"

# 跨包引用
python -c "from evoscholar.iterative_search.settings import ResearchSettings, AsyncContextSerializer"

# 主 Settings 聚合（含 ResearchSettings）
python -c "from evoscholar.literature_qa.settings import Settings; s = Settings(); assert hasattr(s, 'research')"

# FastAPI 启动正常
python -c "from evoscholar.server.app import app"
```

---

### Commit 10：清理垫片（可选，长期）

**内容**：
- 删除 `evoscholar/agents/`, `evoscholar/research/` 兼容垫片目录
- 删除 `evoscholar/docs.py`, `evoscholar/types.py` 等根目录旧文件
- 更新 `evoscholar/__init__.py` 导出

**风险**：高。破坏性变更，需确保所有外部引用已迁移。

**验证**：
```bash
# 应失败：旧路径不再可用
python -c "from evoscholar.agents import ask"  # ImportError
python -c "from evoscholar.research import ResearchEngine"  # ImportError
# 全量测试
pytest tests/ -x -q --tb=short
```

---

## 8. 测试策略

每个 commit 后执行：

```bash
# 基础 import 测试
python -c "import evoscholar"

# 核心类型测试（utils/ + 各包 core.py）
python -c "from evoscholar.utils.paths import *"
python -c "from evoscholar.utils.llms import get_llm_model"
python -c "from evoscholar.literature_qa.core import Docs, DocDetails, PQASession"

# 4 个功能包 import 测试
python -c "from evoscholar.query_understanding import analyze_and_expand_query"
python -c "from evoscholar.iterative_search import ResearchEngine"
python -c "from evoscholar.paper_ranker import score_papers, rank_with_mmr"
python -c "from evoscholar.synthesis import AnswerSummary, EvidenceSnippet"
python -c "from evoscholar.synthesis.sse_formatter import format_progress_event"

# 各功能包 settings.py
python -c "from evoscholar.literature_qa.settings import Settings, AnswerSettings, get_settings"
python -c "from evoscholar.iterative_search.settings import ResearchSettings"

# 既有功能包
python -c "from evoscholar.literature_qa import ask"
python -c "from evoscholar.metadata_clients import AcademicSearchClient"

# server 快速启动测试（不连真实 API）
python -c "from evoscholar.server.app import app"
```

**SSE 字段映射校验**（防 §roadmap.md §6 重蹈覆辙）：

```bash
python -c "
from evoscholar.synthesis.sse_formatter import format_usage_event, format_answer_event
usage = format_usage_event(tokens=100, cost=0.01, search_calls=5, llm_calls=3)
assert usage['totalTokens'] == 100
assert usage['totalCost'] == 0.01
assert usage['searchCalls'] == 5
assert usage['llmCalls'] == 3
assert 'tokenUsage' not in usage  # 旧字段名不可出现
assert 'apiCalls' not in usage
"
```

**依赖反向校验**（CI 阶段跑，确保 §6.3 铁律不被打破）：

```bash
# 禁止 literature_qa 依赖 4 个搜索包
rg "from evoscholar\.(query_understanding|iterative_search|paper_ranker|synthesis)" src/evoscholar/literature_qa/

# 禁止 query_understanding 依赖其他业务包
rg "from evoscholar\.(iterative_search|paper_ranker|synthesis|literature_qa)" src/evoscholar/query_understanding/

# 禁止 paper_ranker 依赖 synthesis
rg "from evoscholar\.synthesis" src/evoscholar/paper_ranker/

# 禁止 synthesis 直接调用 metadata_clients
rg "from evoscholar\.metadata_clients" src/evoscholar/synthesis/
```

预期所有上面 `rg` 输出为空。

全量测试：
```bash
pytest tests/ -x -q --tb=short
```

---

## 9. 注意事项

1. **git mv 优于 rm + add**：用 `git mv` 保留历史
2. **每个 commit 验证一次**：不要跨多个包做多个变更后一起提交
3. **Server Settings 合并在最后**：因为 server 依赖其他所有包，最后合并容易冲突
4. **垫片保留到 Commit 10**：旧路径（`agents/`、`research/`、`clients/`）保留 shim 警告
5. **`academic_search.py` 保留在 `metadata_clients/`**：它是 `iterative_search` 的依赖，不是 `literature_qa` 的内部实现
6. **`research/models.py` 拆分时按归属包切**：13 个类分到 4 个包（见 §3.2.1-3.2.4），不要图省事把整个 `models.py` 单独搬
7. **`_build_evidence_and_answer` 必拆**：必须从 `engine.py` 抽出到 `synthesis/builder.py`，否则 `iterative_search` 与 `synthesis` 死循环耦合
8. **SSE 格式化属于 synthesis**：HTTP 协议（推送 / 关闭）属于 server；SSE payload 字段（论文列表 / 答案 / usage 字段名）属于 synthesis
9. **research/ 删除在 Commit 6**：synthesis 拆分后 `research/` 目录被掏空，最后一次 commit 删除
10. **Avoid 临时调试代码**：迁移过程中如发现 bug，先记 `docs/meta/gotchas.md` 后修，**不要**在迁移 commit 里夹带功能修复
11. **前端字段名校对（Commit 6 必做）**：迁移 `sse_formatter.py` 时对照 `private-docs/roadmap.md` §6，确认 `totalTokens` / `totalCost` / `searchCalls` / `llmCalls` 字段名与前端 `SearchStats` 对齐
12. **依赖反向校验加入 CI**：§8 的 `rg` 检查清单建议作为 pre-commit hook，避免后续开发者无意中违反 §6.3
13. **`utils/` 边界控制**：仅放 ≥2 个功能包都需要的工具。新增 utils 内容前必须先问"如果只在 1 个包用，是不是放该包 `core.py` 更合适？"。`utils/` 膨胀等于变相重建共享 core，破坏 §1.2 的 owner 唯一性
14. **core.py 与 settings.py 占位**：迁移过程中如果某功能包暂时没有专属 core/settings 内容，也要创建空文件（`pass` 或注释 `"""TODO: 填充该包专属内容"""`），保证 §1.2 内部结构对所有包一致
15. **utils/ 不放业务模型**：§3.5.3 已列禁止项；放进去等于让所有包耦合，违反 §6.3 铁律
