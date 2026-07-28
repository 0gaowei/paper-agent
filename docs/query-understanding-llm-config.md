# Query Understanding 模型配置实现

本文档记录 `query_understanding.py` 中 LLM 模型配置的完整实现链路。

## 调用链路概览

```
analyze_and_expand_query()
    ↓
_call_llm(llm_model, messages)
    ↓
ResearchLoop (传入 llm_model)
    ↓
settings.get_llm()
    ↓
LiteLLMModel + make_default_litellm_model_list_settings()
```

## 1. 入口：`analyze_and_expand_query`

**文件**: `src/paperqa/research/query_understanding.py`

```python
async def analyze_and_expand_query(
    query: str, settings: Any, llm_model: Any
) -> QueryUnderstanding:
    """Analyze a query with the configured LLM and return a structured understanding.

    Raises if the LLM call or JSON parsing fails; no heuristic fallback.
    """
    query = query.strip()
    if not query:
        raise ValueError("query must not be empty")

    messages = [
        {"role": "system", "content": QUERY_UNDERSTANDING_SYSTEM},
        {
            "role": "user",
            "content": QUERY_UNDERSTANDING_PROMPT.format(query=query),
        },
    ]
    response = await _call_llm(llm_model, messages)
    return QueryUnderstanding.model_validate(
        _normalize_payload(query, _extract_json(_extract_text(response)))
    )
```

## 2. LLM 调用适配：`_call_llm`

**文件**: `src/paperqa/research/query_understanding.py`

```python
async def _call_llm(llm_model: Any, messages: list[dict[str, str]]) -> Any:
    if hasattr(llm_model, "acomplete"):
        result = llm_model.acomplete(messages)
    elif hasattr(llm_model, "call_single"):
        result = llm_model.call_single(
            messages=[Message(role=m["role"], content=m["content"]) for m in messages],
            name="research_query_understanding",
        )
    else:
        raise TypeError("LLM model must provide acomplete() or call_single()")
    return await result if inspect.isawaitable(result) else result
```

支持两种 LLM 接口协议：

| 接口 | 来源 | 用途 |
|------|------|------|
| `acomplete()` | LiteLLM | 通用 LLM 调用 |
| `call_single()` | Aviany/InnerEye | Agent 场景 |

## 3. 模型来源：`ResearchLoop`

**文件**: `src/paperqa/research/engine.py`

```python
class ResearchLoop:
    def __init__(
        self,
        settings: Any,
        llm_model: Any = None,
        embedding_model: Any = None,
        providers: AcademicSearchProvider | Sequence[AcademicSearchProvider] | None = None,
    ) -> None:
        self.settings = settings
        self.llm_model = llm_model or settings.get_llm()
```

**优先级**:
1. 如果传入了 `llm_model`，直接使用
2. 否则调用 `settings.get_llm()` 从配置构建

## 4. 模型实例化：`get_llm`

**文件**: `src/paperqa/settings.py`

```python
def get_llm(self) -> LiteLLMModel:
    return LiteLLMModel(
        name=self.llm,
        config=self.llm_config
        or make_default_litellm_model_list_settings(
            self.llm, self.temperature, self.llm_api_key, self.llm_base_url
        ),
    )
```

**配置来源**:
- `self.llm` — 模型名称（如 `gpt-4o`、`claude-3-opus`）
- `self.llm_config` — 自定义配置 dict
- `self.temperature` — 温度参数
- `self.llm_api_key` — API 密钥
- `self.llm_base_url` — 自定义 API 端点

## 5. 默认配置构建

**文件**: `src/paperqa/settings.py`

```python
def make_default_litellm_model_list_settings(
    llm: str, temperature: float = 0.0, api_key: str | None = None, api_base: str | None = None
) -> dict:
    """Settings matching "model_list" schema: https://docs.litellm.ai/docs/routing"""
    litellm_params: dict[str, Any] = {
        "model": llm,
        "temperature": temperature,
        "cache_control_injection_points": [
            {"location": "message", "role": "system"}
        ],
        ...
    }
    if api_key:
        litellm_params["api_key"] = api_key
    if api_base:
        litellm_params["api_base"] = api_base
    return {"model_list": [{"litellm_params": litellm_params, "model_info": {...}}]}
```

## 6. 包装层：`_TrackedLLMAdapter`

**文件**: `src/paperqa/research/engine.py`

```python
class _TrackedLLMAdapter:
    """Expose PaperQA's call_single API around either supported LLM interface."""

    def __init__(self, delegate: Any, usage: UsageStats) -> None:
        self.delegate = delegate
        self.usage = usage

    async def call_single(self, messages: Any, **kwargs: Any) -> LLMResult:
        # 统一不同 LLM 接口 + 追踪使用量
        if hasattr(self.delegate, "call_single"):
            response = self.delegate.call_single(messages=messages, **kwargs)
        elif hasattr(self.delegate, "acomplete"):
            ...
            response = self.delegate.acomplete(serialized)
        ...
        self.usage.llm_calls += 1
        self.usage.llm_prompt_tokens += prompt_tokens
        self.usage.llm_completion_tokens += completion_tokens
        self.usage.llm_cost_usd += cost
        return LLMResult(...)
```

**职责**:
1. 适配不同 LLM 接口（`acomplete` → `call_single`）
2. 统一追踪 token 消耗和成本
3. 异步结果处理

## 配置优先级总结

```
ResearchLoop(llm_model=xxx)     ← 最高优先级（可注入自定义模型）
        ↓
settings.get_llm()              ← 从 Settings 实例获取
        ↓
Settings.llm / llm_config       ← 配置文件或环境变量
        ↓
make_default_litellm_model_list_settings()  ← 默认参数
```

## 环境变量配置

可通过以下环境变量覆盖配置：

| 环境变量 | 对应字段 | 说明 |
|----------|----------|------|
| `LITELLM_MODEL` | `settings.llm` | 模型名称 |
| `LITELLM_API_KEY` | `settings.llm_api_key` | API 密钥 |
| `LITELLM_API_BASE` | `settings.llm_base_url` | API 端点 |
| `LITELLM_TEMPERATURE` | `settings.temperature` | 采样温度 |

## 备选方案：无可用兜底

~~当 LLM 调用失败时，系统会回退到本地关键词匹配……~~

启发式兜底已移除。`analyze_and_expand_query` 失败时会直接抛出异常，由调用方（典型场景是 `server/routes/sessions.py` 的后台任务）通过 SSE 的 ERROR 事件+`session.status = "error"` 暴露给客户端。部署环境必须配置可用 LLM。
