# 查询理解与分解

本文档描述 `query_understanding.py` 模块的完整实现方案，涵盖意图分析、领域识别、子查询分解和查询策略生成。

## 架构概览

```
用户查询
    │
    ▼
analyze_and_expand_query()
    │
    └── _call_llm() → JSON 响应 → _normalize_payload() → QueryUnderstanding
```

> LLM 失败时直接抛出异常，由调用方决定如何处理。已不再提供本地启发式兜底。

---

## 1. 意图分析（QueryIntent）

### 1.1 意图类型定义

**文件**: `src/paperqa/research/models.py` 第 22-41 行

系统定义了 6 种意图类型：

| 枚举值 | 说明 |
|---|---|
| `SURVEY` | 全面综述某主题 |
| `SPECIFIC` | 查找特定信息或事实 |
| `COMPARATIVE` | 对比多个方法/论文 |
| `CURRENT_STATE` | 了解某领域当前研究状态 |
| `BACKGROUND` | 查找基础性/背景文献 |
| `GENERAL` | 无特定目标的通用探索 |

### 1.2 LLM 路径

**入口函数**: `src/paperqa/research/query_understanding.py` 第 179-200 行

1. 组装 `QUERY_UNDERSTANDING_SYSTEM` + `QUERY_UNDERSTANDING_PROMPT` 构建消息
2. 调用 `_call_llm()` 发送至 LLM，获取 JSON 响应
3. 经 `_extract_json()` 解析文本中的 JSON 对象
4. 由 `_normalize_payload()` 归一化后构造 `QueryUnderstanding`

如果 LLM 调用或 JSON 解析失败，`analyze_and_expand_query` 直接抛出异常，由调用方（如 sessions 路由）决定如何处理。**不再有本地启发式兜底**。

**Prompt 模板**: `src/paperqa/research/prompts.py` 第 10-54 行

- `QUERY_UNDERSTANDING_SYSTEM`：定义系统角色为"专业研究馆员"
- `QUERY_UNDERSTANDING_PROMPT`：要求 LLM 输出 JSON 格式的意图、领域、实体、子查询列表

**LLM 调用适配**: `src/paperqa/research/query_understanding.py` 第 166-176 行

`_call_llm()` 兼容两种 LLM 接口协议：`acomplete()`（LiteLLM）和 `call_single()`（Aviany），统一返回 LLM 原始响应。

## 2. 领域识别（Domain）

### 2.1 领域类型定义

**文件**: `src/paperqa/research/models.py` 第 44-83 行

系统定义了 13 种领域枚举值：`CS_AI`、`NLP`、`ML`、`CV`、`BIO`、`MED`、`PHYSICS`、`CHEMISTRY`、`ECONOMICS`、`PSYCHOLOGY`、`SOCIAL`、`MULTIDISCIPLINARY`、`UNKNOWN`。

### 2.2 关键词匹配表

**定义**: `src/paperqa/research/query_understanding.py` 第 13-34 行

`_DOMAIN_KEYWORDS` 字典~~为每个领域维护一组中英文关键词元组。查询文本与任一关键词匹配即归入该领域，支持多领域同时识别~~已删除（仅启发式兜底路径使用，兜底删除后随之移除）。

### 2.3 别名映射

**定义**: `src/paperqa/research/query_understanding.py` 第 16-30 行

`_DOMAIN_ALIASES` 提供全称到枚举的快捷映射，例如 `"ai" → CS_AI`、`"natural language processing" → NLP`，用于 `_coerce_domain()` 在 LLM 返回领域字符串时的归一化。

### 2.4 领域归一化

**函数**: `src/paperqa/research/query_understanding.py` 第 56-63 行

`_coerce_domain()` 将任意输入归一化为 `Domain` 枚举：先尝试直接转换小写加下划线的字符串；若失败则查询别名映射；仍无法识别则返回 `UNKNOWN`。

---

## 3. 子查询分解（SubQuery）

### 3.1 模型定义

**文件**: `src/paperqa/research/models.py` 第 121-142 行

每个子查询包含：

| 字段 | 说明 |
|---|---|
| `query` | 子查询文本 |
| `purpose` | 用途说明 |
| `priority` | 优先级 0-10，越高越重要 |
| `parent_intent` | 所属父意图 |
| `domain` | 主要领域 |

### 3.2 归一化与优先级排序

**函数**: `src/paperqa/research/query_understanding.py` 第 66-107 行

`_normalize_payload()` 完成以下处理：

1. **意图归一化**：将 LLM 返回的意图字符串转换为 `QueryIntent` 枚举
2. **领域归一化**：对所有领域调用 `_coerce_domain()` 并去重
3. **子查询归一化**：统一为 dict 格式，补全 `parent_intent` 和 `domain` 字段
4. **空子查询兜底**：若 LLM 返回空列表，生成一条 priority=10 的原查询子查询

---

## 4. 查询改写与扩展策略

### 4.1 策略字段

**文件**: `src/paperqa/research/models.py` 第 169-172 行

`QueryUnderstanding.search_strategy` 字段标识整体搜索策略，取值范围为 `survey`、`domain`、`general`。

### 4.2 策略判定逻辑

**LLM 路径**：prompt 模板指导 LLM 根据意图类型自行选择合适策略（`survey` / `domain` / `general`），LLM 失败时直接抛错，无本地策略推断。

## 5. 完整输出模型

**文件**: `src/paperqa/research/models.py` 第 145-180 行

`QueryUnderstanding` 模型聚合所有分析结果：

| 字段 | 类型 | 说明 |
|---|---|---|
| `original_query` | `str` | 原始用户查询 |
| `intent` | `QueryIntent` | 主要意图 |
| `domains` | `list[Domain]` | 相关领域列表 |
| `entities` | `list[str]` | 关键实体（作者、方法、论文等） |
| `suitable_sources` | `list[str]` | 推荐数据源（如 semantic_scholar） |
| `subqueries` | `list[SubQuery]` | 分解后的子查询列表 |
| `search_strategy` | `str` | 整体搜索策略 |

---

## 6. 响应解析工具

**文本提取**: `src/paperqa/research/query_understanding.py` 第 33-52 行

`_extract_text()` 兼容多种 LLM 响应格式：纯字符串、dict（content 字段）、OpenAI-style choices 格式、含 `text` 属性的对象。

**JSON 提取**: `src/paperqa/research/query_understanding.py` 第 54-63 行

`_extract_json()` 从 LLM 返回文本中提取 JSON 对象，支持处理 markdown 代码块包裹的 JSON，自动定位首尾大括号进行截取。

---

## 7. 配置依赖

详见 [Query Understanding LLM 配置实现](./query-understanding-llm-config.md)。
