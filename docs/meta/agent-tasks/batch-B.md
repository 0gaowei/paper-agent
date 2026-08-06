# Batch B：叶子包迁移（Commit 2 + 3）

## 1. 任务概述

执行 `refactor-plan.md` §7 中的：

- **Commit 2**：`clients/` → `metadata_clients/`（低风险）
- **Commit 3**：从 `research/query_understanding.py` 抽取建 `query_understanding/` 包（低风险）

**两个 commit 互相独立，可由两个 Agent 并行执行**。如果只用一个 Agent，按顺序执行即可。

## 2. 前置依赖

- Batch A（Commit 0 + 1）已完成
- 包名已改为 `evoscholar`

## 3. 必读章节

- `refactor-plan.md` §7 Commit 2（line 757 起）
- `refactor-plan.md` §7 Commit 3（line 775 起）
- `refactor-plan.md` §3.2.1（query_understanding 包设计）
- `refactor-plan.md` §3.3.1（metadata_clients 包设计）

## 4. 详细步骤

### 4.1 Commit 2（clients → metadata_clients）

```bash
# 1. 创建目录
mkdir src/evoscholar/metadata_clients

# 2. 移动文件
git mv src/evoscholar/clients/academic_search.py src/evoscholar/metadata_clients/academic_search.py
git mv src/evoscholar/clients/client_models.py src/evoscholar/metadata_clients/client_models.py
git mv src/evoscholar/clients/crossref.py src/evoscholar/metadata_clients/crossref.py
git mv src/evoscholar/clients/semantic_scholar.py src/evoscholar/metadata_clients/semantic_scholar.py
git mv src/evoscholar/clients/openalex.py src/evoscholar/metadata_clients/openalex.py
git mv src/evoscholar/clients/unpaywall.py src/evoscholar/metadata_clients/unpaywall.py
git mv src/evoscholar/clients/journal_quality.py src/evoscholar/metadata_clients/journal_quality.py
git mv src/evoscholar/clients/retractions.py src/evoscholar/metadata_clients/retractions.py
git mv src/evoscholar/clients/exceptions.py src/evoscholar/metadata_clients/exceptions.py

# 3. 处理 __init__.py（如果有）
git mv src/evoscholar/clients/__init__.py src/evoscholar/metadata_clients/__init__.py

# 4. 加兼容垫片（保留到 Batch G）
# src/evoscholar/clients/__init__.py 留个 shim：
#   from evoscholar.metadata_clients import *  # re-export
# 或更狠：rmdir src/evoscholar/clients，单独建 shim 文件

# 5. 更新所有 import
rg "from evoscholar\.clients" src/ tests/ -l
# 替换为 from evoscholar.metadata_clients
```

### 4.2 Commit 3（query_understanding）

```bash
# 1. 创建目录
mkdir src/evoscholar/query_understanding

# 2. 移动主文件
git mv src/evoscholar/research/query_understanding.py src/evoscholar/query_understanding/analyze.py

# 3. 提取模型（QueryIntent / Domain / SubQuery / QueryUnderstanding）
# 从 research/models.py 中提取
git mv src/evoscholar/research/models.py src/evoscholar/query_understanding/models.py
# （如果 research/models.py 还要为其他 Batch 留用，先复制再删原文件，不要直接 mv）
# 实际：仅复制需要的类到 query_understanding/models.py，剩余类留 research/models.py

# 4. 提取 prompt
# 从 research/prompts.py 中提取 QUERY_UNDERSTANDING_PROMPT / QUERY_UNDERSTANDING_SYSTEM
# 创建 src/evoscholar/query_understanding/prompts.py

# 5. 创建 __init__.py + 导出
touch src/evoscholar/query_understanding/__init__.py

# 6. 兼容垫片（保留到 Batch G）
# src/evoscholar/research/query_understanding.py 改为：
#   from evoscholar.query_understanding.analyze import *  # shim
```

## 5. 验证清单

每个 commit 完成后必跑：

```bash
# Commit 2 验证
python -c "from evoscholar.metadata_clients import AcademicSearchClient"
python -c "from evoscholar.metadata_clients.crossref import CrossrefProvider"
python -c "from evoscholar.metadata_clients.semantic_scholar import SemanticScholarProvider"
python -c "from evoscholar.metadata_clients.openalex import OpenAlexProvider"
# 旧路径兼容
python -c "from evoscholar.clients import AcademicSearchClient"  # 通过 shim

# Commit 3 验证
python -c "from evoscholar.query_understanding import analyze_and_expand_query, QueryUnderstanding"
python -c "from evoscholar.query_understanding.models import QueryIntent, SubQuery"
python -c "from evoscholar.query_understanding.prompts import QUERY_UNDERSTANDING_PROMPT"
# 旧路径兼容
python -c "from evoscholar.research.query_understanding import analyze_and_expand_query"  # 通过 shim

# 依赖反向校验（§6.3 铁律：metadata_clients 不依赖其他业务包）
rg "from evoscholar\.(query_understanding|iterative_search|paper_ranker|synthesis|literature_qa)" src/evoscholar/metadata_clients/
# 预期：空
```

## 6. 范围外（不要做）

- ❌ 不要创建 `iterative_search/` `paper_ranker/` `synthesis/` `literature_qa/` 包（那是 Batch C）
- ❌ 不要删除 `research/` 目录（Batch D Commit 6 才会删）
- ❌ 不要拆解 `research/engine.py` 或 `research/models.py` 中其他类（留给对应 Batch）
- ❌ 不要修改 `metadata_clients/` 内部代码（仅移动位置）

## 7. 报告模板

```
Batch B 完成
- Commit 2: <hash>  refactor: rename clients/ to metadata_clients/
- Commit 3: <hash>  refactor: extract query_understanding package
- 验证: <全部通过 / 部分失败已修复 / 失败未通过>
- 改动文件: <list>
- 兼容垫片位置: <行号>
- 附带 gotchas.md 更新: <是/否>
```

## 8. 父 Agent 收到后

1. 验证两个 commit 都成功
2. 进入 Batch C（Commit 4 + 5 + 7）
