# Batch G：清理垫片（Commit 10）

## 1. 任务概述

执行 `refactor-plan.md` §7 中的：

- **Commit 10**：删除所有兼容垫片（破坏性变更）

**这是整个重构的最后一个 commit**，所有兼容性垫片统一清理。

## 2. 前置依赖

- Batch A + B + C + D + E + F 全部完成
- 全量测试通过

## 3. 必读章节

- `refactor-plan.md` §7 Commit 10（line 969 起）
- `refactor-plan.md` §9（注意事项）

## 4. 详细步骤

### 4.1 兼容垫片清单（按 Batch 累积）

之前各 Batch 留下的垫片：

| 来源 Batch | 垫片位置 | 垫片内容 |
|---|---|---|
| A | `evoscholar/__init__.py` 或 `pyproject.toml alias` | `paperqa` → `evoscholar` 别名 |
| B | `src/evoscholar/clients/__init__.py` | re-export from metadata_clients |
| B | `src/evoscholar/research/query_understanding.py` | re-export from query_understanding |
| C | `src/evoscholar/research/engine.py` | re-export from iterative_search |
| C | `src/evoscholar/research/ranking.py` | re-export from paper_ranker |
| C | `src/evoscholar/agents/` | 整个目录 re-export from literature_qa |
| D | `src/evoscholar/research/` | 空目录兼容 |
| 其他 | 各种 `from evoscholar.X import Y` 的兼容 re-export | 视情况 |

### 4.2 执行步骤

```bash
# 1. 验证全量测试通过（**前置必须**）
pytest tests/ -x -q --tb=short
# 如果失败 → 不要进入本 Batch，先修复

# 2. 扫描所有兼容垫片
rg "DeprecationWarning" src/evoscholar/
rg "from evoscholar\." src/evoscholar/ -l | xargs grep -l "re-export\|shim"

# 3. 删除 paperqa 别名
# 方式 A：从 evoscholar/__init__.py 移除 sys.modules["paperqa"]
# 方式 B：从 pyproject.toml 移除 alias
# （看 Batch A 怎么做的）

# 4. 删除旧目录
git rm -r src/evoscholar/agents  # 旧路径
git rm -r src/evoscholar/research  # 旧路径
git rm -r src/evoscholar/clients  # 旧路径

# 5. 删除旧顶层文件
git rm src/evoscholar/agents.py  # 如果之前误留
git rm src/evoscholar/clients.py  # 如果之前误留
# 其他兼容垫片文件

# 6. 更新 src/evoscholar/__init__.py 导出
# 按 refactor-plan §1 新结构导出主入口

# 7. 验证
python -c "from evoscholar.agents import ask" 2>&1 | grep ImportError
python -c "from evoscholar.research.engine import ResearchEngine" 2>&1 | grep ImportError
python -c "from evoscholar.clients import AcademicSearchClient" 2>&1 | grep ImportError
python -c "from paperqa import X" 2>&1 | grep ImportError
```

### 4.3 注意

- **不要改 README.md 中关于兼容垫片的说明**（如果还提到"兼容旧路径"，改为"请使用新路径"）
- **不要修改任何业务代码**（仅删除垫片）
- **不要修改 pyproject.toml 的 metadata**（除非删除 paperqa alias）

## 5. 验证清单

```bash
# 1. 旧路径全部失效
python -c "from evoscholar.agents import ask" 2>&1 | grep -q ImportError && echo "OK"
python -c "from evoscholar.research.engine import ResearchEngine" 2>&1 | grep -q ImportError && echo "OK"
python -c "from evoscholar.clients import AcademicSearchClient" 2>&1 | grep -q ImportError && echo "OK"
python -c "from paperqa import X" 2>&1 | grep -q ImportError && echo "OK"

# 2. 新路径全部正常
python -c "import evoscholar; print(evoscholar.__file__)"
python -c "from evoscholar.literature_qa import ask"
python -c "from evoscholar.iterative_search import ResearchEngine"
python -c "from evoscholar.paper_ranker import score_papers"
python -c "from evoscholar.synthesis import AnswerSummary"
python -c "from evoscholar.query_understanding import analyze_and_expand_query"
python -c "from evoscholar.metadata_clients import AcademicSearchClient"
python -c "from evoscholar.server.app import app"

# 3. 全量测试
pytest tests/ -x -q --tb=short

# 4. 依赖反向校验（最后一次确认 §6.3 铁律）
rg "from evoscholar\.(query_understanding|iterative_search|paper_ranker|synthesis)" src/evoscholar/literature_qa/
rg "from evoscholar\.(iterative_search|paper_ranker|synthesis|literature_qa)" src/evoscholar/query_understanding/
rg "from evoscholar\.synthesis" src/evoscholar/paper_ranker/
rg "from evoscholar\.metadata_clients" src/evoscholar/synthesis/
# 全部预期：空
```

## 6. 范围外（不要做）

- ❌ 不要修改任何业务代码
- ❌ 不要新增兼容垫片
- ❌ 不要留下灰色路径（all-or-nothing 删除）
- ❌ 不要在 README.md 里描述 old paths 作为兼容（改为直接展示新路径）

## 7. 报告模板

```
Batch G 完成
- Commit 10: <hash>  refactor: remove all compatibility shims
- 验证:
  - 旧路径失效: OK
  - 新路径正常: OK
  - 全量测试: OK
  - 依赖反向校验: OK
- 删除的兼容垫片: <list>
- 改动文件: <list of deleted files>
- 附带 gotchas.md 更新: <是/否>
- 任何遗留的兼容问题: <list>
```

## 8. 父 Agent 收到后

1. 验证全量测试通过
2. 验证所有旧路径失效
3. 更新 `docs/meta/state.md` 标记重构完成
4. 在 `docs/meta/agent-context.md` §4 当前进度表标记全部完成
5. 通知用户：重构完成
