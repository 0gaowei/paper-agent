# Batch F：settings 下沉（Commit 9）

## 1. 任务概述

执行 `refactor-plan.md` §7 中的：

- **Commit 9**：`settings.py` → 各包 `settings.py` + 合并 Server Settings

**核心变化**：
- 不存在顶层 `evoscholar/settings/`；每个包有自己的 `settings.py`
- `Settings` 主类作为聚合入口，保留在 `literature_qa/settings.py`（因为大多数 Settings 集中在此）
- 主 `Settings` 通过引用直接 re-export 各包 Settings

## 2. 前置依赖

- Batch E 已完成（`core.py` 全部下沉完成）
- 各包 `core.py` 已存在，引用正常

## 3. 必读章节

- `refactor-plan.md` §7 Commit 9（line 935 起）
- `refactor-plan.md` §3.5（settings 下沉方案）
- `refactor-plan.md` §3.5.1（Settings 归属映射）
- `refactor-plan.md` §3.5.2（主 Settings 聚合策略）

## 4. 详细步骤

### 4.1 Settings 归属映射

| Settings 子类 | 行数估算 | 新归属 |
|---|---|---|
| `AnswerSettings` | ~130 | `literature_qa/settings.py` |
| `ParsingSettings`, `ChunkingOptions`, `MultimodalOptions` | ~170 | `literature_qa/settings.py` |
| `PromptSettings` | ~115 | `literature_qa/settings.py` |
| `IndexSettings` | ~95 | `literature_qa/settings.py` |
| `AgentSettings` | ~140 | `literature_qa/settings.py` |
| `ResearchSettings` | ~30 | `iterative_search/settings.py` |
| `AsyncContextSerializer` (Protocol) | ~12 | `iterative_search/settings.py` |
| `_FormatDict` | ~15 | `iterative_search/settings.py` |
| 主 `Settings` + `get_settings()` | ~80 | `literature_qa/settings.py`（聚合） |

### 4.2 执行顺序

```bash
# 1. 移动 source settings.py
# 这里 git mv 不合适，因为要拆分到多个包
# 直接读取 src/evoscholar/settings.py 内容，按 owner 拆分

# 2. 填充 literature_qa/settings.py
# 创建 literature_qa/_answer.py / _parsing.py / _prompts.py / _index.py / _agent.py 临时文件
# 拆分 AnswerSettings / ParsingSettings / PromptSettings / IndexSettings / AgentSettings
# 然后 literature_qa/settings.py 顶部 import 并 re-export

# 3. 填充 iterative_search/settings.py
# 移动 ResearchSettings / AsyncContextSerializer / _FormatDict

# 4. 主 Settings 聚合
# 在 literature_qa/settings.py 中：
#   from evoscholar.iterative_search.settings import ResearchSettings, AsyncContextSerializer, _FormatDict
#   class Settings(BaseSettings):
#       answer: AnswerSettings = Field(default_factory=AnswerSettings)
#       parsing: ParsingSettings = Field(default_factory=ParsingSettings)
#       prompts: PromptSettings = Field(default_factory=PromptSettings)
#       index: IndexSettings = Field(default_factory=IndexSettings)
#       agent: AgentSettings = Field(default_factory=AgentSettings)
#       research: ResearchSettings = Field(default_factory=ResearchSettings)

# 5. 删除原 src/evoscholar/settings.py
git rm src/evoscholar/settings.py

# 6. 合并 Server Settings
# server/routes/settings.py 改为薄封装
# 删除 _SETTINGS_DEFAULTS dict
# 改读写 app.state.settings（顶层 Settings 实例）
# 更新 server/app.py：启动时初始化 app.state.settings = Settings()

# 7. 其他功能包 settings.py 保持占位
# query_understanding / paper_ranker / synthesis / metadata_clients
# 各自保留空文件：pass 或 """TODO: 填充该包专属内容"""
```

### 4.3 关键引用替换

```bash
# 替换规则
# from evoscholar.settings import AnswerSettings → from evoscholar.literature_qa.settings import AnswerSettings
# from evoscholar.settings import Settings → from evoscholar.literature_qa.settings import Settings
# from evoscholar.settings import ResearchSettings → from evoscholar.iterative_search.settings import ResearchSettings
# 等等
```

## 5. 验证清单

```bash
# 1. 主入口
python -c "from evoscholar.literature_qa.settings import Settings, get_settings"
python -c "from evoscholar.literature_qa.settings import AnswerSettings, PromptSettings, IndexSettings"
python -c "from evoscholar.literature_qa.settings import ParsingSettings, ChunkingOptions, MultimodalOptions"
python -c "from evoscholar.literature_qa.settings import AgentSettings"

# 2. 跨包引用
python -c "from evoscholar.iterative_search.settings import ResearchSettings, AsyncContextSerializer, _FormatDict"

# 3. 主 Settings 聚合（含 ResearchSettings）
python -c "from evoscholar.literature_qa.settings import Settings; s = Settings(); assert hasattr(s, 'research')"
python -c "from evoscholar.literature_qa.settings import Settings; s = Settings(); assert hasattr(s, 'answer')"
python -c "from evoscholar.literature_qa.settings import Settings; s = Settings(); assert hasattr(s, 'parsing')"

# 4. get_settings() 工作正常
python -c "from evoscholar.literature_qa.settings import get_settings; s = get_settings(); print(type(s).__name__)"

# 5. FastAPI 启动正常
python -c "from evoscholar.server.app import app"

# 6. 兜底：旧路径失效
python -c "from evoscholar.settings import Settings" 2>&1 | grep ImportError

# 7. 依赖反向校验
rg "from evoscholar\.literature_qa\.settings" src/evoscholar/iterative_search/
# 预期：空（iterative_search 只暴露自己的 settings.py，不应跨包引 literature_qa 的 settings）
```

## 6. 范围外（不要做）

- ❌ 不要修改 settings 内容（字段、默认值、验证规则的修改不属于本次重构）
- ❌ 不要新增 Settings 子类（除非必要）
- ❌ 不要在 server/routes/settings.py 加新字段（合并到 app.state.settings 即可）
- ❌ 不要破坏向后兼容（**保留主 Settings 在 literature_qa/settings.py** 以便 from evoscholar.literature_qa.settings import Settings 仍可用）

## 7. Server Settings 合并要点

```python
# server/app.py 改动示例
from evoscholar.literature_qa.settings import Settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings = Settings()  # 启动时初始化
    yield

# server/routes/settings.py 改动示例
from fastapi import Request

@router.get("/settings")
async def get_settings(request: Request):
    return request.app.state.settings

@router.post("/settings")
async def update_settings(request: Request, new_settings: dict):
    settings = request.app.state.settings
    # 用 Pydantic 的更新方法
    updated = settings.model_copy(update=new_settings)
    request.app.state.settings = updated
    return updated
```

## 8. 报告模板

```
Batch F 完成
- Commit 9: <hash>  refactor: split settings.py into per-package settings + merge server settings
- 验证:
  - 主入口: OK
  - 跨包引用: OK
  - 主 Settings 聚合: OK
  - get_settings(): OK
  - FastAPI 启动: OK
  - 旧路径失效: OK
  - 依赖反向校验: OK
- 改动文件: <list>
- Server Settings 合并方式: <描述如何从独立 dict 改为 app.state.settings>
- 附带 gotchas.md 更新: <是/否>
```

## 9. 父 Agent 收到后

1. 验证 Settings 聚合正常
2. 验证 Server Settings 合并不破坏现有接口
3. 进入 Batch G（Commit 10）
