# Batch A：基础设施准备（Commit 0 + 1）

## 1. 任务概述

执行 `refactor-plan.md` §7 中的：

- **Commit 0**：包重命名 `paperqa` → `evoscholar`
- **Commit 1**：基础设施准备（pyproject.toml、目录结构骨架）

这是**所有后续 Batch 的前置**。

## 2. 前置依赖

- **无**（起点）

## 3. 必读章节

- `refactor-plan.md` §7 Commit 0（line 723 起）
- `refactor-plan.md` §7 Commit 1（line 744 起）
- `refactor-plan.md` §1（目录结构总览）
- `refactor-plan.md` §3.7（包重命名）

## 4. 详细步骤

### 4.1 Commit 0（包重命名）

```bash
# 1. 验证当前状态
git status  # 应该是 clean
git log --oneline -5

# 2. 全局替换 package_name
# 在 pyproject.toml 中：
#   name = "evoscholar"  # 原 paperqa
#   packages = ["evoscholar"]  # 原 paperqa
#   [project.scripts]
#   evoscholar = "evoscholar.cli:main"  # 原 paperqa

# 3. 目录重命名
git mv src/paperqa src/evoscholar

# 4. 全局替换 import（注意：所有 from paperqa.X import Y 改为 from evoscholar.X import Y）
# 用 rg 确认范围：
rg "from paperqa\." src/ tests/

# 推荐用 sed 或 IDE 全局替换：
rg "from paperqa\." -l | xargs sed -i 's/from paperqa\./from evoscholar./g'
rg "import paperqa\." -l | xargs sed -i 's/import paperqa\./import evoscholar./g'

# 5. 兼容垫片（保留 paperqa 作为 alias）
# 在 evoscholar/__init__.py 顶部加：
#   import importlib
#   import sys as _sys
#   _paperqa = importlib.import_module("evoscholar")
#   _sys.modules["paperqa"] = _paperqa
# 或者更安全的方式：在 pyproject.toml 加 alias

# 6. 验证
python -c "import evoscholar; print(evoscholar.__file__)"
python -c "import paperqa"  # 兼容垫片，应该也能 import
```

### 4.2 Commit 1（基础设施准备）

```bash
# 创建顶层目录骨架（用户已在 refactor-plan §1 规划）
# 注意：metadata_clients / query_understanding / iterative_search / paper_ranker / synthesis / literature_qa / server
# 这些目录在 Commit 2-7 才会创建
# Commit 1 只创建 utils/ 因为这是 §1 顶层目录

mkdir -p src/evoscholar/utils
touch src/evoscholar/utils/__init__.py

# 更新 pyproject.toml：
# - 添加 [tool.ruff] / [tool.mypy] 等开发工具配置
# - 添加 [project.optional-dependencies] 拆分 dev/test/docs
# - 配置 pre-commit hook（依赖反向校验，见 §6.3）

# 更新 README.md：
# - 包名改为 evoscholar
# - 架构图改用新结构
```

## 5. 验证清单

完成后必跑：

```bash
# 1. 基础 import
python -c "import evoscholar; print(evoscholar.__file__)"
python -c "import paperqa"  # 兼容垫片

# 2. 原有导入路径仍可用
python -c "from evoscholar.agents import ask"  # 旧路径
python -c "from evoscholar.research.engine import ResearchEngine"  # 旧路径

# 3. 重组后路径生效
python -c "import evoscholar.utils"
ls src/evoscholar/utils/  # 看到 __init__.py

# 4. 既有测试
pytest tests/ -x -q --tb=short 2>&1 | head -30  # 不需要全过，但要确认没有新失败
```

## 6. 范围外（不要做）

- ❌ 不要创建 `metadata_clients/` `query_understanding/` 等功能包目录（那是 Batch B/C）
- ❌ 不要创建各功能包下的 `core.py` `settings.py`（那是 Batch E/F）
- ❌ 不要删除旧路径（兼容垫片保留到 Batch G）
- ❌ 不要重命名 `agents/` → `literature_qa/`（那是 Batch C 的 Commit 7）

## 7. 报告模板

完成后输出：

```
Batch A 完成
- Commit 0: <hash>  refactor: rename package paperqa to evoscholar
- Commit 1: <hash>  chore: create utils/ shared directory + infra setup
- 验证:
  - import evoscholar: OK
  - import paperqa (兼容垫片): OK
  - 旧路径 / 新路径: 都 OK
- 改动文件: <list of moved files + pyproject.toml + README.md>
- 兼容垫片位置: <evoscholar/__init__.py 还是 pyproject.toml alias>
- 附带 gotchas.md 更新: <是/否，列条目>
- 遇到的问题: <任何偏离 plan 的>
```

## 8. 父 Agent 收到后

1. 验证两个 commit 都成功
2. 跑 `git status` 确认 clean
3. 进入 Batch B（Commit 2 + 3）
