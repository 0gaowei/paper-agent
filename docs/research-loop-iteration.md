# 自主搜索策略迭代优化

本文档基于 `arun()` 主流程说明「基于大模型的自主搜索策略迭代优化」的实现方案。

## 架构概览

```
ResearchEngine.arun()
    │
    ├── analyze_and_expand_query() → QueryUnderstanding
    │
    ├── 初始化 asyncio.Queue（按 priority 降序入队子查询）
    │
    └── for round in 1..max_rounds:
            │
            ├── _run_searches() → 并发搜索
            │       │
            │       └── provider.search() × N  (asyncio.gather)
            │
            ├── ascore_papers() → 评分 + 分级 (HIGH/PARTIAL/LOW)
            │
            ├── _expand_references() → 引用网络扩展 (HIGH 论文)
            │       │
            │       ├── provider.get_references()
            │       └── provider.get_doc_details() × N
            │
            ├── rank_with_mmr() → 多样性排序
            │
            ├── 动态生成 follow-up 查询入队
            │
            └── _budget_exceeded() → 终止条件判定
```

> 引擎调度是「LLM 规划 → 并发搜索 → 评分 → 引用扩展 → 循环」的闭环；任何一环异常都不会让整个流程崩溃。

---

## 0. 搜索数据源（AcademicSearchClient）

**文件**: `src/paperqa/clients/academic_search.py` 第 135-225 行

`AcademicSearchClient` 是一个**多源聚合搜索客户端**，`arun()` 通过 `self.provider` 间接调用它。构造时（第 148-151 行）默认注册 2 个第三方学术 API：

| Provider | name | 实现位置 | 底层数据源 |
|---|---|---|---|
| Semantic Scholar | `semantic_scholar` | `_SemanticScholarAcademicProvider` 第 83-106 行 | [api.semanticscholar.org](https://api.semanticscholar.org/) — 语义检索 + 论文详情 + 引用列表 |
| OpenAlex | `openalex` | `_OpenAlexAcademicProvider` 第 109-132 行 | [api.openalex.org](https://api.openalex.org/) — 开放学术图谱，搜索 + 文档详情 + referenced_works |

**聚合调用机制**：

- `search()` 第 177-225 行：`asyncio.gather` 并发调用所有 provider 的 `search()`，按 `stable_id`（优先 DOI，否则 SHA1(title+year)）去重；任何一个 provider 抛异常都会被捕获并 log warning，其它 provider 的结果继续合并 → **Partial Success**
- `get_doc_details()` 第 227-242 行：按 provider 顺序**串行回退**调用，返回第一个非空结果
- `get_references()` 第 244-261 行：聚合所有 provider 的引用 ID 后去重

**底层 API 调用**：

- Semantic Scholar：`src/paperqa/clients/semantic_scholar.py` — `s2_topic_search` / `s2_get_doc_details` / `s2_paper_references`
- OpenAlex：`src/paperqa/clients/openalex.py` — `openalex_search` / `openalex_get_doc` / `openalex_referenced_works`

**HTTP 客户端**：复用同一个 `httpx.AsyncClient`（连接池复用），异常重试通过可选 `AsyncRetrying`（tenacity）参数控制。

---

## 1. 自主规划搜索词（LLM 生成子查询）

入口位于 `src/paperqa/research/engine.py` 第 459-493 行，由 `ResearchEngine.arun()` 完成：

1. 调用 `analyze_and_expand_query()` 获得 `QueryUnderstanding`（含子查询列表）
2. 按 `priority` 降序将子查询入队到 `asyncio.Queue`
3. `_run_searches()`（`src/paperqa/research/engine.py` 第 292-311 行）通过 `asyncio.gather` 并发执行所有搜索查询

## 2. 搜索结果过滤（异常捕获）

`_run_searches()` 返回 `list[SearchResult | BaseException]`，在 `arun()` 第 510-516 行通过 `isinstance(outcome, BaseException)` 过滤失败搜索，仅保留 `outcome.success == True` 的结果。

## 3. 迭代式检索策略（BFS + follow-up）

由 `arun()` 第 495-622 行的 `for round_number in range(1, max_rounds + 1)` 主循环驱动：

1. 从队列批量取出本轮所有搜索查询
2. 并发执行搜索，收集候选论文
3. 对候选论文打分排序
4. 取 top-2 且 `relevance_tier != LOW` 的论文，动态生成 follow-up 查询：`{原查询} {论文标题}`，入队供后续轮次使用

## 4. 引文网络扩展（递归获取引用）

`_expand_references()`（`src/paperqa/research/engine.py` 第 313-380 行）对高相关论文执行：

1. 调用 `provider.get_references()` 获取其参考文献 ID 列表
2. 每条引用关系记录为 `CitationEdge`
3. 批量获取参考文献的详细信息
4. 合并到 `session.all_papers` 并重新打分

## 5. 预算控制（token / API 调用 / cost）

`_budget_exceeded()`（`src/paperqa/research/engine.py` 第 247-257 行）检查三维度：

| 维度 | 配置字段 |
|---|---|
| token 总数 | `settings.research.token_budget` |
| LLM 费用（美元） | `settings.research.llm_budget_usd` |
| API 调用次数 | `settings.research.api_budget` |

## 6. 多轮迭代终止条件

由 `arun()` 第 611-624 行的判断块决定：

| 终止条件 | 对应枚举 |
|---|---|
| 达到最大轮次 | `MAX_ROUNDS_REACHED` |
| 队列为空 | `QUEUE_EMPTY` |
| 高相关论文数量达标 | `MAX_HIGH_RELEVANT` |
| 本轮无新论文 | `NO_NEW_PAPERS` |
| 预算超限 | `BUDGET_EXCEEDED` |
| 异常退出 | `ERROR` |
