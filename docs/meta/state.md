# Project State

> 本文件是 AI Agent 的状态入口。每次 commit 后，Cursor Agent 会自动追加 Recent Decisions。
> 人类不需要手动维护，只需在 commit 时简要描述"做了什么重要决定"。

---

## Current Focus

- **P0**: 修复 stats 字段映射（后端 usage 事件 → 前端 SearchStats 字段名对齐）
- **P0**: 答案引用可点击展示（后端 answer 事件含 papers_cited，前端丢弃了）

## Architecture

```
evoscholar/
├── src/evoscholar/
│   ├── literature_qa/         # Papers, Docs, Settings, Tools (原 agents/)
│   │   ├── core.py            # Docs, AgentConfig, prompts
│   │   ├── models.py          # PQAResult 等
│   │   ├── settings.py        # Settings 类（聚合所有子 Settings）
│   │   ├── env.py             # 环境状态函数
│   │   ├── tools.py           # Agent 工具
│   │   └── search.py          # 搜索入口
│   ├── iterative_search/      # Research engine（多轮迭代搜索）
│   │   ├── engine.py          # arun()，多轮迭代循环
│   │   ├── models.py          # QueryUnderstanding, SubQuery, AcademicPaper, ResearchSession
│   │   ├── settings.py        # ResearchSettings
│   │   └── core.py            # 空包（预留）
│   ├── query_understanding/   # LLM 意图分析，子查询分解
│   │   ├── analyze.py         # analyze_and_expand_query()
│   │   ├── models.py          # QueryAnalysis, QueryIntent
│   │   └── settings.py        # QueryUnderstandingSettings
│   ├── paper_ranker/          # 论文排序，MMR 策略
│   │   ├── ranker.py          # 综合排序
│   │   ├── mmr.py             # Maximal Marginal Relevance
│   │   └── relevance.py       # RelevanceTier
│   ├── synthesis/             # 答案合成，SSE 事件格式化
│   │   ├── builder.py         # build_evidence_and_answer()
│   │   ├── models.py          # EvidenceSnippet, AnswerSummary, UsageStats
│   │   ├── sse_formatter.py   # SSE payload 字段格式化
│   │   └── settings.py        # SynthesisSettings
│   ├── metadata_clients/      # 外部 API 客户端
│   │   ├── academic_search.py # Semantic Scholar / OpenAlex / Crossref
│   │   └── journal_quality.py # 期刊质量评分
│   ├── utils/                 # 共享工具层
│   │   ├── _helpers.py        # 原 utils_helpers.py（包内私有）
│   │   ├── paths.py           # 路径工具
│   │   ├── llms.py            # LLM 工具
│   │   └── math_utils.py      # 数学工具
│   └── server/                # FastAPI 服务
│       ├── app.py             # FastAPI 应用，路由注册
│       ├── bridge.py           # ResearchSession → SSE 事件
│       ├── events.py           # EventType 枚举
│       ├── settings.py         # ServerSettings
│       └── routes/
│           ├── sessions.py     # SSE 会话路由（有 bug）
│           └── graph.py        # 关系图路由（有 bug）
├── frontend/src/
│   ├── stores/search.ts       # 前端状态，applyEvent()，normalize()
│   ├── views/
│   │   ├── SearchView.vue     # 搜索主页（有 stats 字段映射 bug）
│   │   ├── ResultsView.vue    # 结果页（evidence/answer 展示极简）
│   │   └── GraphView.vue      # 关系图（有 bug）
│   └── api/index.ts           # snake→camel normalizer
└── docs/meta/
    ├── state.md             # 项目状态，Recent Decisions 表
    └── gotchas.md          # 踩过的坑 + 设计原则
```

## Recent Decisions

| 日期 | 决定 | 理由 |
|------|------|------|
| 2026-07-29 | 移除 query understanding 启发式兜底，LLM 失败直接抛错 | 原 heuristic 方案质量差，且让 sessions.py 里 fallback_used 逻辑复杂化 |
| 2026-07-29 | 删除 `QueryUnderstanding.fallback_used` / `error_message` 字段及所有相关代码 | 兜底路径已移除，这些字段不再有意义 |
| 2026-07-29 | 建立 state.md + gotchas.md 替代 HANDOFF | HANDOFF 文件过多且割裂，改用单一状态入口 + 坑集积累 |
| 2026-08-06 | 包重命名 paperqa → evoscholar | refactor-plan Batch A Commit 0：git mv + 全局 import 替换 |
| 2026-08-06 | 包目录骨架创建 + shadowing 修复 | refactor-plan Batch A Commit 1：新建 core/ 等 9 个包目录；重命名 core.py→core_impl.py、settings.py→settings_config.py、utils.py→utils_helpers.py 以避免同名冲突 |
| 2026-08-06 | sys.modules 兼容垫片：evoscholar/__init__.py 末尾将 paperqa alias 指向 evoscholar | 过渡期允许 import paperqa 仍可用 |
| 2026-07-27 | SSE ERROR 事件字段从 `message` 改为 `error` | 前端 expect `{error: string}`，字段名不匹配导致前端无法展示错误 |
| 2026-07-27 | `_TrackedLLMAdapter` 只暴露 `call_single`，不暴露 `acomplete` | 统一接口，但导致 test stub 中 FakeLLM 需要在 call_single 首次返回 JSON |
| 2026-07-26 | 合并 roadmap → state.md，roadmap 冻结 | 功能清单已过时，用 state.md 替代 |
| 2026-08-07 | 删除全部测试文件和 ClinicalTrials 模块 | tests/、cassettes/、packages/*/tests/ 及 clinical_trials.py 全部删除；项目聚焦核心搜索代理，测试和临床试验功能暂不维护 |
| 2026-08-07 | 删除所有兼容垫片（Commit 10） | Batch G 收尾：agents/、research/、clients.py 目录/文件全部删除；utils_helpers.py 重命名为 utils/_helpers.py；paperqa sys.modules 别名保留（供 paperqa_pypdf/pymupdf 下游 wheel 在 evoscholar 已加载后使用） |
| 2026-08-07 | 澄清后端启动方式：`pqa-serve` 才是官方入口，uvicorn 直接跑是 Agent 记忆错误 | README 定义 source env.sh && pqa-serve；pqa-serve 内部调 uvicorn，支持 PQA_HOST/PQA_PORT 环境变量 |

## TODO

### P0（影响用户可见）

- [ ] **stats 字段映射**：`search.ts` 中 `usage` 事件 → `SearchStats` 字段对齐
  - 后端发送：`totalTokens`, `totalCost`, `searchCalls`, `llmCalls`
  - 前端期望：`stats.tokenUsage`, `stats.cost`, `stats.apiCalls`
  - `totalPapers` / `duration` 在 usage 事件中不存在，需前端自行计算
- [ ] **答案引用展示**：`answer` 事件的 `papers_cited` / `citations` 渲染为可点击链接

### P1（功能补全）

- [ ] **Evidence 展示增强**：关联论文标题、来源 provider、相关度评分
- [ ] **按意图归纳 UI**：根据子查询 intent 分组展示（后端已有，前端无 UI）
- [ ] **GraphView 边匹配 bug**：`routes/graph.py` L93，`sq.round == paper.relevance_tier` 类型错误

### P2（架构验证）

- [ ] 真实 API key E2E 验证（当前 API key 额度不足，无法测试完整流程）
- [ ] 多 round 端到端验证（`max_rounds > 1`，SSE 事件序列）
- [ ] citation_expanded 事件验证
- [ ] 删除测试后：补充必要的 smoke test / integration test（待规划）

## Dependencies

- 后端：`python >= 3.12`，`litellm`，`lmi`，`fastapi`，`uvicorn`
- 前端：`node >= 18`，`vue 3`，`pinia`，`element-plus`
- 启动命令：`pqa-serve`（后端，source env.sh && pqa-serve），`npm run dev`（前端，frontend 目录）
