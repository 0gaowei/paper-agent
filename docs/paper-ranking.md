# 论文综合排序

本文档基于 `research/ranking.py` 说明「论文综合排序」的实现方案。

## 架构概览

```
score_papers() / ascore_papers()
    │
    ├── try: embedding_model.embed_documents() / aembed()
    │       │
    │       └── _embed_texts() → 批量 embedding
    │           │
    │           └── _cosine(query_vec, doc_vec) → relevance_scores
    │
    ├── except: → _lexical_relevance()  (embedding 不可用兜底)
    │
    └── _assign_scores()
            │
            ├── relevance (0.55) ─ cosine 或 lexical
            ├── recency   (0.15) ─ 1 - (当前年-论文年) / 20
            ├── citation  (0.15) ─ log1p(citations) / log1p(max)
            └── diversity (0.15) ─ Σ(1/field_count) / num_fields
                    │
                    └── weighted combined → RelevanceTier (HIGH / PARTIAL / LOW)

rank_with_mmr()
    │
    └── 贪心选取 λ·combined - (1-λ)·max_similarity
            │
            └── _paper_similarity() → max(field_jaccard, title_jaccard)
```

> 排序主路径走 embedding cosine，embedding 不可用时静默降级到词法兜底；MMR 在最终选择阶段引入多样性去重。

## 1. 向量相似度相关性评估

- `ascore_papers()` 第 181-201 行（async）/ `score_papers()` 第 153-178 行（sync）是入口
- `_embed_texts()` 第 54-66 行批量调用 embedding 模型
- `_cosine()` 第 41-51 行计算查询向量与文档向量的余弦相似度

## 2. 词汇相关性兜底（无 embedding 时）

`_lexical_relevance()` 第 26-38 行在 embedding 不可用时兜底，采用 coverage + saturation 加权组合：

| 因子 | 权重 |
|---|---|
| coverage（查询词命中率） | 0.75 |
| saturation（词频饱和度） | 0.25 |

## 3. 综合排序算法（多因子加权）

`_assign_scores()` 第 90-150 行四因子加权，最终分数归一化（除以权重总和）：

| 因子 | 默认权重 | 计算方式 |
|---|---|---|
| relevance | 0.55 | embedding cosine 或 lexical relevance |
| recency | 0.15 | `1 - (当前年 - 论文年) / 20`，封顶 20 年 |
| citation | 0.15 | `log1p(citation_count) / log1p(max_citations)` |
| diversity | 0.15 | `Σ(1 / field_count[field]) / num_fields` |

## 4. MMR 多样性排序

`rank_with_mmr()` 第 222-256 行：

- `lambda_mult = 0.5` 平衡相关性与多样性
- 候选按 `combined` 分数排序后贪心选择，每步选取 `λ * combined - (1-λ) * max_similarity`
- `_paper_similarity()` 第 204-219 行：取 `fields_of_study` 的 Jaccard 与 `title` token 的 Jaccard 的最大值

## 5. 双阈值分级（HIGH ≥ 0.75 / PARTIAL ≥ 0.5）

阈值读取于第 95-96 行，分级判定于第 137-143 行：

| 阈值 | 等级 |
|---|---|
| `relevance ≥ 0.75` | `RelevanceTier.HIGH` |
| `relevance ≥ 0.5` | `RelevanceTier.PARTIAL` |
| 其他 | `RelevanceTier.LOW` |

阈值可通过 `config.high_threshold` / `config.partial_threshold` 配置。

## 6. 按领域分组多样性展示

`_assign_scores()` 第 100-120 行：

- `field_counts` 统计所有 `fields_of_study` 的出现频次
- 每篇论文的 diversity 因子 = 该论文各 field 的倒数和 / field 数，体现「所属领域越冷门，多样性贡献越高」