# 项目 Roadmap

> ⚠️ 本文档上次更新：2026-07-27（基于代码审查全面校准）
> 核心发现：`research/` 包全部核心功能已完成，roadmap 历史状态严重滞后。

## 1. 查询理解与分解

| 功能点 | 状态 | 实现位置 | 说明 |
| --- | --- | --- | --- |
| LLM 意图分析（6 类意图） | ✅ 已完成 | `research/query_understanding.py` | `analyze_and_expand_query()`：survey / specific / comparative / current_state / background / general |
| 领域识别（12 类 + 别名映射） | ✅ 已完成 | `research/query_understanding.py` | `_DOMAIN_KEYWORDS` / `_DOMAIN_ALIASES`，支持中英文 |
| 子查询分解（优先级排序） | ✅ 已完成 | `research/query_understanding.py` | `SubQuery` 模型，含 priority / purpose / domain |
| 无 LLM 时的启发式兜底 | ✅ 已完成 | `research/query_understanding.py` | `_heuristic_understanding()` 纯关键词方案 |
| 查询改写与扩展策略（survey/domain/general） | ✅ 已完成 | `research/query_understanding.py` | `search_strategy` 字段，prompt 模板区分三种策略 |

## 2. 基于大模型的自主搜索策略迭代优化

| 功能点 | 状态 | 实现位置 | 说明 |
| --- | --- | --- | --- |
| 自主规划搜索词（LLM 生成子查询） | ✅ 已完成 | `research/engine.py` | `arun()` 中的 BFS 队列，`_run_searches()` 并发执行 |
| 搜索结果过滤（异常捕获） | ✅ 已完成 | `research/engine.py` | `isinstance(outcome, BaseException)` 过滤失败搜索 |
| 迭代式检索策略（BFS + follow-up） | ✅ 已完成 | `research/engine.py` | 每轮取 top-2 paper 动态生成 follow-up 查询入队 |
| 引文网络扩展（递归获取引用） | ✅ 已完成 | `research/engine.py` | `_expand_references()`：获取 ref → 打分 → merge |
| 预算控制（token / API 调用 / cost） | ✅ 已完成 | `research/engine.py` | `_budget_exceeded()`：三维度控制，`StopReason` 6 种 |
| 多轮迭代终止条件 | ✅ 已完成 | `research/engine.py` | MAX_ROUNDS / QUEUE_EMPTY / MAX_HIGH_RELEVANT / NO_NEW_PAPERS / BUDGET_EXCEEDED |

## 3. 论文综合排序

| 功能点 | 状态 | 实现位置 | 说明 |
| --- | --- | --- | --- |
| 向量相似度相关性评估 | ✅ 已完成 | `research/ranking.py` | `ascore_papers()` + `_embed_texts()` + `_cosine()` |
| 词汇相关性兜底（无 embedding 时） | ✅ 已完成 | `research/ranking.py` | `_lexical_relevance()`：coverage + saturation 组合 |
| 综合排序算法（多因子加权） | ✅ 已完成 | `research/ranking.py` | `_assign_scores()`：relevance 55% / recency 15% / citation 15% / diversity 15% |
| MMR 多样性排序 | ✅ 已完成 | `research/ranking.py` | `rank_with_mmr()`：lambda_mult=0.5，基于 fields_of_study 和 title 相似度 |
| 双阈值分级（HIGH ≥ 0.75 / PARTIAL ≥ 0.5） | ✅ 已完成 | `research/ranking.py` | `RelevanceTier` 枚举，`_assign_scores()` 判定 |
| 按领域分组多样性展示 | ✅ 已完成 | `research/ranking.py` | `_assign_scores()` 中 `field_counts` 统计 |

## 4. 搜索结果归纳整理

| 功能点 | 状态 | 实现位置 | 说明 |
| --- | --- | --- | --- |
| 结构化列表展示 | ✅ 已完成 | `research/models.py` | `AcademicPaper` / `SearchResult` / `SearchRound` 模型 |
| 关系图展示 | ✅ 已完成 | 前端 `GraphView.vue` (D3.js) | 前端已有，需对接 `citation_graph` 数据 |
| 按意图归纳整理 | ✅ 已完成 | `research/engine.py` | `_build_evidence_and_answer()`：evidence + answer synthesis |
| Evidence 片段提取 | ✅ 已完成 | `research/engine.py` | `_EvidenceAdapter` + `aget_evidence()` → `EvidenceSnippet` 列表 |
| 答案合成（带引用） | ✅ 已完成 | `research/engine.py` | `adapter.aquery()` → `AnswerSummary` 含 citations |
| 答案合成失败兜底 | ✅ 已完成 | `research/engine.py` | `except` 块：用 abstract 替代 evidence，保证有输出 |

## 5. 技术对接

| 功能点 | 状态 | 实现位置 | 说明 |
| --- | --- | --- | --- |
| 多 academic provider 聚合 | ✅ 已完成 | `clients/academic_search.py` | `AcademicSearchClient` 统一封装 |
| Semantic Scholar API | ✅ 已完成 | `clients/semantic_scholar.py` | 完整实现 |
| OpenAlex API | ✅ 已完成 | `clients/openalex.py` | 完整实现 |
| Crossref API | ✅ 已完成 | `clients/crossref.py` | 完整实现 |
| S2 API | ✅ 已完成 | `clients/semantic_scholar.py` | 复用 |
| LLM 集成（多模型支持） | ✅ 已完成 | `research/engine.py` | `_TrackedLLMAdapter` 支持 `call_single` / `acomplete` |
| 成本统计（Token / API 调用） | ✅ 已完成 | `research/models.py` | `UsageStats` 模型：llm_calls / tokens / cost / api_calls_by_provider |
| PDF 解析与 chunk 索引 | ✅ 已完成 | `agents/search.py` | Tantivy 索引 + `Docs.aadd()` |

## 6. 前端界面

| 功能点 | 状态 | 实现位置 |
| --- | --- | --- |
| 搜索主页 | ✅ 已完成 | `frontend/src/views/SearchView.vue` |
| 结果列表页 | ✅ 已完成 | `frontend/src/views/ResultsView.vue` |
| 论文详情页 | ✅ 已完成 | `frontend/src/views/PaperDetailView.vue` |
| 关系图谱页 | ✅ 已完成 | `frontend/src/views/GraphView.vue` |
| 历史记录页 | ✅ 已完成 | `frontend/src/views/HistoryView.vue` |
| 设置页 | ✅ 已完成 | `frontend/src/views/SettingsView.vue` |
| SSE 实时推送接收 | ✅ 已完成 | `frontend/src/stores/search.ts` + `SubQueryList.vue` |

## 7. 评测指标

| 指标 | 权重 | 说明 |
| --- | --- | --- |
| F1 Score | 70% | 精确率与召回率 |
| 运行效率 | 20% | API 调用次数、Token 消耗、端到端延时 |
| 结果结构化 | 10% | 列表、关系图展示 |

> 📌 注：评测指标部分仅有设计文档，**无 benchmark 实现代码**。如需评测，需接入 Asta-Bench / paper-qa 现有测试框架。

---

## 下一步：待完成项

| 优先级 | 功能点 | 说明 |
| --- | --- | --- |
| P0 | 评测 benchmark 接入 | 将 `UsageStats` / `AnswerSummary` 对接 Asta-Bench 评测框架 |
| P1 | 真实 API key E2E 验证 | 填入 `OPENAI_API_KEY` / `S2_API_KEY` 后验证完整流程 |
| P1 | GraphView 对接 citation_graph | 前端图谱尚未接入 `CitationEdge` 数据 |
| P2 | 多 round 端到端验证 | `max_rounds > 1` 时 SSE 事件序列完整性 |
| P2 | citation_expanded 事件验证 | `_expand_references` 触发时 bridge 层事件对齐 |
| P3 | 性能优化 | embedding 批量并行、`_run_searches` 并发数调参 |
