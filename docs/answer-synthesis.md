# 搜索结果归纳与答案生成

本文档基于 `_build_evidence_and_answer()`（`src/paperqa/research/engine.py` 第 382-453 行）说明当前「4. 搜索结果归纳整理」中的**答案生成方案**，对应 roadmap 第 44-47 行的后端实现。

## 架构概览

```
ResearchEngine._build_evidence_and_answer()
    │
    ├── 过滤: session.final_papers 中 abstract 非空的论文
    │
    ├── _EvidenceAdapter(papers) → Docs()
    │       │
    │       └── 把每篇论文的 abstract 注入为 Text  (绕过 PDF/文件读取)
    │
    ├── (1) aget_evidence() → PQASession.contexts
    │       │
    │       ├── evidence_retrieval = False        (不二次检索)
    │       ├── evidence_skip_summary = True      (跳过 evidence 摘要)
    │       └── get_evidence_if_no_contexts = False (空 context 直接返回)
    │
    │       └── 转 EvidenceSnippet[]
    │               ├── paper_id / paper_title
    │               ├── content (文本片段)
    │               ├── relevance_score (0-1 归一化)
    │               ├── subquery_addressed
    │               ├── citation
    │               └── provider
    │
    ├── (2) aquery() → PQASession.answer + contexts
    │       │
    │       └── 复用 PaperQA 自己的 answer synthesis (LLM)
    │
    └── AnswerSummary
            ├── answer = answered.answer or answered.raw_answer (兜底)
            ├── subqueries_covered = 所有 subquery 文本
            ├── evidence_used = len(session.evidence)
            ├── papers_cited = 去重后的 context dockey 列表
            ├── citations = 去重后的 citation 字符串列表
            ├── raw_answer = answered.raw_answer
            └── has_successful_answer
```

> 核心思路：**复用 PaperQA 内部 `Docs.aquery()`** 完成 evidence 抽取与答案合成，但 data source 是论文 abstract 而非 PDF。

---

## 1. _EvidenceAdapter：把 abstract 喂给 Docs

**文件**: `src/paperqa/research/engine.py` 第 119-159 行

### 设计动机

PaperQA 的 `Docs.aget_evidence()` / `Docs.aquery()` 默认从**文件/PDF** 读取内容。`_EvidenceAdapter` 是薄包装层，把搜索阶段已经获得的 `paper.abstract` 直接注入为 `Docs.texts`，**完全不下载 PDF**。

### 实现要点

```python
for paper in papers:
    if not (paper.abstract or "").strip():
        continue
    citation = self._citation(paper)            # 第 149-153 行
    details = DocDetails(docname=..., dockey=..., citation=...)
    text = Text(name=..., text=paper.abstract, doc=details)
    self.docs.docs[details.dockey] = details
    self.docs.texts.append(text)
```

- **跳过无 abstract 的论文**：避免 PaperQA 把空 text 当成 context
- **稳定 ID 复用**：`dockey = paper.stable_id`（与搜索阶段同 ID，便于前端引用串联）
- **citation 格式**（`_citation()` 第 149-153 行）：`"{authors[:3]}. {title}. {year}."`，无作者时填 `"Unknown authors"`，无年份时填 `"n.d."`

### ProgressCallback 钩子

`_build_evidence_and_answer()` 第 420-426 行依次触发：

1. `on_evidence_extraction_done(session_id, len(evidence))`
2. `on_answer_synthesis_start(session_id, "Synthesizing answer from evidence...")`

---

## 2. Evidence 抽取（aget_evidence）

### 关键 settings 开关

`_build_evidence_and_answer()` 第 392-395 行：

| 字段 | 值 | 含义 |
|---|---|---|
| `evidence_retrieval` | `False` | **不二次检索**，因为 text 已经是摘要 |
| `evidence_skip_summary` | `True` | **跳过 evidence 摘要步骤**，LLM 不再对每条 context 做摘要 |
| `get_evidence_if_no_contexts` | `False` | 没有 context 时**直接返回空**，不触发兜底查询 |

### EvidenceSnippet 字段映射（第 404-419 行）

| EvidenceSnippet 字段 | 来源 |
|---|---|
| `paper_id` | `str(context.text.doc.dockey)` |
| `paper_title` | `getattr(context.text.doc, "title", None)` |
| `content` | `context.context`（摘要文本片段） |
| `relevance_score` | `clamp(context.score / 10.0, 0, 1)`（PaperQA 原始 0-10，归一化） |
| `subquery_addressed` | `context.question`（子查询文本） |
| `citation` | `context.text.doc.citation` |
| `provider` | 通过 `adapter.paper_by_id[dockey].source` 反查，缺失时填 `"unknown"` |

---

## 3. 答案合成（aquery）

`aquery()` 第 427-433 行把同一个 `pqa_session`（含上一步产出的 `contexts`）再交给 PaperQA 的答案合成流水线，由 LLM 综合 evidence 写出最终答案。

**返回的 `AnswerSummary`**（第 445-453 行）：

```python
AnswerSummary(
    answer=answered.answer or answered.raw_answer,        # 兜底链
    subqueries_covered=[s.query for s in understanding.subqueries],  # 全平铺
    evidence_used=len(session.evidence),
    papers_cited=dedup([c.text.doc.dockey for c in answered.contexts]),
    citations=dedup([c.text.doc.citation for c in answered.contexts]),
    raw_answer=answered.raw_answer,
    has_successful_answer=answered.has_successful_answer,
)
```
