# Project State

> 本文件是 AI Agent 的状态入口。每次 commit 后，Cursor Agent 会自动追加 Recent Decisions。
> 人类不需要手动维护，只需在 commit 时简要描述"做了什么重要决定"。

---

## Current Focus

- **P0**: 修复 stats 字段映射（后端 usage 事件 → 前端 SearchStats 字段名对齐）
- **P0**: 答案引用可点击展示（后端 answer 事件含 papers_cited，前端丢弃了）

## Architecture

```
paper-qa/
├── src/paperqa/
│   ├── research/
│   │   ├── engine.py          # 核心搜索循环，arun()，多轮迭代
│   │   ├── query_understanding.py  # LLM 意图分析，子查询分解
│   │   ├── ranking.py         # 综合排序，MMR，RelevanceTier
│   │   ├── callbacks.py       # ResearchProgressCallback 协议
│   │   └── models.py          # QueryUnderstanding, SubQuery, AcademicPaper 等
│   ├── server/
│   │   ├── routes/
│   │   │   ├── sessions.py    # SSE 会话路由，_run_research_engine 后台任务
│   │   │   └── graph.py       # 关系图谱路由（有 bug：边匹配类型错误）
│   │   ├── bridge.py          # ResearchSession → SSE 事件，build_events()
│   │   ├── sse_callback.py    # SSEProgressCallback 实现
│   │   └── events.py          # EventType 枚举
│   └── clients/               # Semantic Scholar / OpenAlex / Crossref API
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
| 2026-07-27 | SSE ERROR 事件字段从 `message` 改为 `error` | 前端 expect `{error: string}`，字段名不匹配导致前端无法展示错误 |
| 2026-07-27 | `_TrackedLLMAdapter` 只暴露 `call_single`，不暴露 `acomplete` | 统一接口，但导致 test stub 中 FakeLLM 需要在 call_single 首次返回 JSON |
| 2026-07-26 | 合并 roadmap → state.md，roadmap 冻结 | 功能清单已过时，用 state.md 替代 |

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

### P2（验证）

- [ ] 真实 API key E2E 验证（当前 API key 额度不足，无法测试完整流程）
- [ ] 多 round 端到端验证（`max_rounds > 1`，SSE 事件序列）
- [ ] citation_expanded 事件验证

## Dependencies

- 后端：`python >= 3.12`，`litellm`，`lmi`，`fastapi`，`uvicorn`
- 前端：`node >= 18`，`vue 3`，`pinia`，`element-plus`
- 启动命令：`pqa-serve`（后端），`npm run dev`（前端，frontend 目录）
