# Batch D：synthesis 迁移 + SSE 拆分（Commit 6）

## 1. 任务概述

执行 `refactor-plan.md` §7 中的：

- **Commit 6**：`synthesis/` 包迁移 + SSE 事件格式化下沉（**中等偏高风险**）

这是**业务循环下沉 + SSE 拆分**的边界变更，必须保证：
1. 字段映射正确（参考 `private-docs/roadmap.md` §6）
2. `_build_evidence_and_answer` 正确归属到 synthesis
3. SSE 字段名与前端 `SearchStats` 对齐

## 2. 前置依赖

- Batch C 的 Commit 4（iterative_search）已合并
- `research/engine.py` 已被 Commit 4 移到 `iterative_search/engine.py`

## 3. 必读章节

- `refactor-plan.md` §7 Commit 6（line 840 起）
- `refactor-plan.md` §3.2.4（synthesis 包设计）
- `private-docs/roadmap.md` §6（**字段映射表，Commit 6 必读**）
- `refactor-plan.md` §6.3（**特别注意：synthesis 不调用 metadata_clients**）

## 4. 详细步骤

### 4.1 Commit 6（synthesis + SSE）

```bash
# 1. 创建目录
mkdir src/evoscholar/synthesis
touch src/evoscholar/synthesis/core.py   # 占位
touch src/evoscholar/synthesis/settings.py  # 占位

# 2. 从 iterative_search/engine.py 提取 _build_evidence_and_answer
# 这是关键：必须从 engine.py 抽出到 synthesis/builder.py
# 注意保留所有依赖（包括 research.models 中的类型，可以通过 owner import）

# 3. 提取 evidence_adapter 等合成相关的辅助函数
# 全部进入 synthesis/builder.py

# 4. 创建合成相关模型
# 从 iterative_search/models.py（或 research/models.py）提取：
#   EvidenceSnippet / AnswerSummary / UsageStats
# 进入 src/evoscholar/synthesis/models.py

# 5. SSE 事件 payload 拆分
# 从 server/routes/sessions.py 提取 SSE payload 构造 → synthesis/sse_formatter.py
# 从 server/sse_callback.py 提取字段格式化 → synthesis/sse_formatter.py
# server/ 保留路由 + stream 推送，业务逻辑下沉

# 6. 字段名校验（**关键**）
# 对照 private-docs/roadmap.md §6 字段映射表
# 必查字段：
#   totalTokens / totalCost / searchCalls / llmCalls
# 不能出现旧字段名：
#   tokenUsage / apiCalls

# 7. 更新 iterative_search/engine.py
# 调用 synthesis.builder 而不是内嵌 _build_evidence_and_answer
# from evoscholar.synthesis.builder import build_evidence_and_answer

# 8. 更新 server
# server/routes/sessions.py 改为：保留 HTTP 路由 + stream 推送
# 字段格式化调用 synthesis.sse_formatter

# 9. 创建 __init__.py + 导出
touch src/evoscholar/synthesis/__init__.py

# 10. 兼容垫片（保留到 Batch G）
# src/evoscholar/research/ 目录此时应该空了，保留但加个 deprecation warning
```

### 4.2 字段映射校验（**必做**）

```bash
# 对照 roadmap.md §6
python -c "
from evoscholar.synthesis.sse_formatter import format_usage_event
payload = format_usage_event(tokens=100, cost=0.01, search_calls=5, llm_calls=3)
assert payload['totalTokens'] == 100, '前端 SearchStats 字段名 totalTokens'
assert payload['totalCost'] == 0.01, '前端 SearchStats 字段名 totalCost'
assert payload['searchCalls'] == 5, '前端 SearchStats 字段名 searchCalls'
assert payload['llmCalls'] == 3, '前端 SearchStats 字段名 llmCalls'
assert 'tokenUsage' not in payload, '旧字段名 tokenUsage 不能出现'
assert 'apiCalls' not in payload, '旧字段名 apiCalls 不能出现'
print('字段映射校验通过')
"
```

## 5. 验证清单

```bash
# 1. 基础 import
python -c "from evoscholar.synthesis import AnswerSummary, EvidenceSnippet"
python -c "from evoscholar.synthesis.sse_formatter import format_progress_event, format_usage_event"
python -c "from evoscholar.synthesis.builder import build_evidence_and_answer"

# 2. iterative_search 仍可用（只是调用 synthesis）
python -c "from evoscholar.iterative_search import ResearchEngine; print(ResearchEngine)"

# 3. server 仍可启动
python -c "from evoscholar.server.app import app"

# 4. 字段映射校验（§4.2）

# 5. 依赖反向校验（**synthesis 禁止调用 metadata_clients**）
rg "from evoscholar\.metadata_clients" src/evoscholar/synthesis/
# 预期：空（违反 §6.3 铁律）

# 6. research/ 目录清空确认
ls src/evoscholar/research/  # 应只剩 __init__.py 等垫片文件
```

## 6. 范围外（不要做）

- ❌ 不要修改 `iterative_search/engine.py` 的核心业务逻辑（仅删除 _build_evidence_and_answer）
- ❌ 不要修改 SSE 字段名（要保持与前端对齐）
- ❌ 不要让 synthesis import metadata_clients（§6.3 铁律）
- ❌ 不要删除 `research/` 目录（Batch G 才会删）
- ❌ 不要填充 `core.py` `settings.py` 的实际内容（Batch E/F）

## 7. 报告模板

```
Batch D 完成
- Commit 6: <hash>  refactor: extract synthesis package + SSE event split
- 验证:
  - synthesis import: OK
  - iterative_search 仍可用: OK
  - server 启动: OK
  - 字段映射校验: OK
  - 依赖反向校验: OK
- 改动文件: <list>
- SSE 字段名清单: <list of format_*_event functions + 字段>
- 附带 gotchas.md 更新: <是/否>
- 任何偏离 plan 的: <list>
```

## 8. 父 Agent 收到后

1. 验证字段映射校验通过
2. 验证 §6.3 铁律（synthesis 不调用 metadata_clients）
3. 进入 Batch E（Commit 8）
