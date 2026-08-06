# Batch C：核心路径迁移（Commit 4 + 5 + 7）

## 1. 任务概述

执行 `refactor-plan.md` §7 中的：

- **Commit 4**：`iterative_search/`（中风险）
- **Commit 5**：`paper_ranker/`（中风险）
- **Commit 7**：`literature_qa/`（原 `agents/`，中风险）

### 关键依赖关系

- **Commit 4 和 5 互相独立**（不互相依赖）→ 可并行
- **Commit 7 完全独立**（与 4/5/6 都不依赖）→ 可与 4/5 任意组合并行
- **Commit 6（Batch D）依赖 Commit 4**，但**不依赖 5 或 7**

→ 如果资源允许，**三个 Agent 并行**分别执行 Commit 4、5、7 是最快的。

## 2. 前置依赖

- Batch A + Batch B 已完成
- `metadata_clients/`、`query_understanding/` 已创建

## 3. 必读章节

- `refactor-plan.md` §7 Commit 4（line 795 起）
- `refactor-plan.md` §7 Commit 5（line 820 起）
- `refactor-plan.md` §7 Commit 7（line 874 起）
- `refactor-plan.md` §3.2.2 / §3.2.3 / §3.2.5（包设计）
- `refactor-plan.md` §6.3（依赖矩阵，**绝对反向校验**）

## 4. 详细步骤

### 4.1 Commit 4（iterative_search）

```bash
# 1. 创建目录
mkdir src/evoscholar/iterative_search

# 2. 移动主文件
git mv src/evoscholar/research/engine.py src/evoscholar/iterative_search/engine.py
git mv src/evoscholar/research/callbacks.py src/evoscholar/iterative_search/callbacks.py

# 3. 提取相关模型（StopReason / CitationEdge / AcademicPaper / SearchRound / ResearchSession / SearchResult）
# 从 research/models.py 提取到 iterative_search/models.py
# 注意：仅复制需要的类，剩余类留 research/models.py

# 4. 创建 __init__.py + 导出
touch src/evoscholar/iterative_search/__init__.py

# 5. iterative_search/settings.py 在 Batch F 填充（现在留空或不放）
touch src/evoscholar/iterative_search/settings.py  # 占位空文件

# 6. iterative_search/core.py 暂不创建（Batch E 会创建）

# 7. 更新 import
rg "from evoscholar\.research\.engine" src/ tests/ -l
# 替换为 from evoscholar.iterative_search.engine

# 8. 兼容垫片（保留到 Batch G）
# src/evoscholar/research/engine.py 改为：
#   from evoscholar.iterative_search.engine import *  # shim
```

### 4.2 Commit 5（paper_ranker）

```bash
# 1. 创建目录
mkdir src/evoscholar/paper_ranker

# 2. 移动主文件
git mv src/evoscholar/research/ranking.py src/evoscholar/paper_ranker/ranker.py

# 3. 拆分（按 refactor-plan §3.2.3）
# embedder.py / mmr.py 从 ranker.py 抽出
# 提取 RelevanceTier 到 paper_ranker/ranker.py 顶部

# 4. 创建 __init__.py + 导出
touch src/evoscholar/paper_ranker/__init__.py
touch src/evoscholar/paper_ranker/core.py  # 占位空文件
touch src/evoscholar/paper_ranker/settings.py  # 占位空文件

# 5. 更新 import
rg "from evoscholar\.research\.ranking" src/ tests/ -l
# 替换为 from evoscholar.paper_ranker.ranker

# 6. 兼容垫片
# src/evoscholar/research/ranking.py 改为 shim
```

### 4.3 Commit 7（literature_qa）

```bash
# 1. 创建目录
mkdir src/evoscholar/literature_qa

# 2. 移动整个 agents 目录
git mv src/evoscholar/agents src/evoscholar/literature_qa

# 3. 创建 core.py / settings.py 占位（Batch E/F 填充）
touch src/evoscholar/literature_qa/core.py
touch src/evoscholar/literature_qa/settings.py

# 4. 更新 literature_qa/__init__.py 导出（ask, agent_query, search_query, build_index）
# 注意：仍依赖 evoscholar.prompts / evoscholar.docs 等根目录文件
# 这些 import 在 Batch E 才会改路径

# 5. 兼容垫片（保留到 Batch G）
# src/evoscholar/agents/__init__.py 改为 shim，从 literature_qa re-export
```

## 5. 验证清单

### Commit 4 验证

```bash
python -c "from evoscholar.iterative_search import ResearchEngine"
python -c "from evoscholar.iterative_search.engine import ResearchEngine"
python -c "from evoscholar.iterative_search.models import ResearchSession, StopReason"
python -c "from evoscholar.iterative_search.callbacks import ResearchProgressCallback"
# 旧路径兼容
python -c "from evoscholar.research.engine import ResearchEngine"  # 通过 shim

# 依赖反向校验
rg "from evoscholar\.(query_understanding|paper_ranker|synthesis|literature_qa)" src/evoscholar/iterative_search/
# 预期：空（query_understanding 是允许的，paper_ranker 是允许的，但 synthesis/literature_qa 禁止）
```

### Commit 5 验证

```bash
python -c "from evoscholar.paper_ranker import score_papers, rank_with_mmr"
python -c "from evoscholar.paper_ranker.ranker import RelevanceTier"
python -c "from evoscholar.paper_ranker.embedder import _embed_texts"
python -c "from evoscholar.paper_ranker.mmr import rank_with_mmr"

# 依赖反向校验
rg "from evoscholar\.(query_understanding|synthesis|literature_qa)" src/evoscholar/paper_ranker/
# 预期：空
```

### Commit 7 验证

```bash
python -c "from evoscholar.literature_qa import ask, agent_query, search_query"
python -c "from evoscholar.literature_qa.tools import PaperSearch"
python -c "from evoscholar.literature_qa.main import agent_query"
# 旧路径兼容
python -c "from evoscholar.agents import ask"  # 通过 shim

# 依赖反向校验（**literature_qa 禁止依赖 4 个搜索包**）
rg "from evoscholar\.(query_understanding|iterative_search|paper_ranker|synthesis)" src/evoscholar/literature_qa/
# 预期：空
```

## 6. 范围外（不要做）

- ❌ 不要创建 `synthesis/` 目录（那是 Batch D）
- ❌ 不要拆 `_build_evidence_and_answer`（Batch D 才会）
- ❌ 不要填充 `core.py` `settings.py` 的实际内容（Batch E/F 填充）
- ❌ 不要修改 `iterative_search/engine.py` 内部业务逻辑（仅移动位置）
- ❌ literature_qa 禁止 import 4 个搜索包（即使只 import 类型也不允许）

## 7. 报告模板

```
Batch C 完成
- Commit 4: <hash>  refactor: extract iterative_search package
- Commit 5: <hash>  refactor: extract paper_ranker package
- Commit 7: <hash>  refactor: rename agents to literature_qa
- 验证: <全部通过 / 部分失败已修复 / 失败未通过>
- 改动文件: <list>
- 兼容垫片位置: <list>
- 附带 gotchas.md 更新: <是/否>
- 三个 commit 并行执行了吗？<是/否>
```

## 8. 父 Agent 收到后

1. 验证 3 个 commit 都成功
2. 跑依赖反向校验（确保 §6.3 铁律）
3. 进入 Batch D（Commit 6）
