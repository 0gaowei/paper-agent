# Batch E：core 下沉 + utils/ 创建（Commit 8）

## 1. 任务概述

执行 `refactor-plan.md` §7 中的：

- **Commit 8**：根目录文件 → 各包 `core.py` + 创建 `utils/` 顶层共享层

**核心变化**：
- 不存在顶层 `evoscholar/core/`；每个包有自己的 `core.py`，是该包专属核心设施
- `utils/` 顶层共享文件夹（按子模块分文件）
- `utils/` 仅放 ≥2 个功能包都需要的工具

## 2. 前置依赖

- Batch A + B + C + D 全部完成
- 7 个功能包都已创建（literature_qa / iterative_search / paper_ranker / synthesis / query_understanding / metadata_clients / server）

## 3. 必读章节

- `refactor-plan.md` §7 Commit 8（line 896 起）
- `refactor-plan.md` §3.5.3（`utils/` 设计）
- `refactor-plan.md` §1.2（**owner 唯一性**原则）
- `refactor-plan.md` §6.3（依赖矩阵）

## 4. 详细步骤

### 4.1 文件归属映射（**关键**）

| 原文件 | 新归属 | 备注 |
|---|---|---|
| `docs.py`（Docs 类） | `literature_qa/core.py` | 是 Docs 的 owner |
| `types.py`（PQASession / DocDetails / Text） | `literature_qa/core.py` | 跨包用，需要在 utils/ 也放一份？**不**，只放 owner 处 |
| `prompts.py`（RAG prompt 常量） | `literature_qa/core.py` | 随 Docs 一起 owner |
| `readers.py`（PDF 解析） | `literature_qa/core.py` | 文献解析专属 |
| `paths.py`（路径管理） | `utils/paths.py` | 跨包通用 |
| `llms.py`（LLM 工厂） | `utils/llms.py`（通用部分） + `iterative_search/core.py`（`_TrackedLLMAdapter`） | **拆分** |
| `utils.py`（通用工具） | `utils/math_utils.py` / `utils/string_utils.py` / 等 | 按功能拆，按需新建 |

### 4.2 执行顺序

```bash
# 1. 创建 utils/ 子模块
mkdir -p src/evoscholar/utils
touch src/evoscholar/utils/__init__.py

# 2. 移动 paths.py → utils/paths.py
git mv src/evoscholar/paths.py src/evoscholar/utils/paths.py

# 3. 移动 llms.py → utils/llms.py（仅通用部分）
# 先复制整个 llms.py 到 utils/llms.py
# 然后从 iterative_search 内部使用时，仅 import 通用部分
# _TrackedLLMAdapter 提取到 iterative_search/core.py
git mv src/evoscholar/llms.py src/evoscholar/utils/llms.py
# 然后从 utils/llms.py 中删除 _TrackedLLMAdapter，移到 iterative_search/core.py

# 4. 移动 utils.py → 按功能拆到 utils/
# 复制 src/evoscholar/utils.py 内容到 utils/math_utils.py / utils/string_utils.py 等
# 不要 git mv 整个文件，要按功能拆分
git rm src/evoscholar/utils.py  # 删除原文件，函数已分散到 utils/ 各子模块

# 5. 合并 docs.py / types.py / prompts.py / readers.py → literature_qa/core.py
# 这些都是 RAG 专属，全部归 literature_qa owner
# 创建一个新文件 literature_qa/core.py，合并这些内容
git rm src/evoscholar/docs.py
git rm src/evoscholar/types.py
git rm src/evoscholar/prompts.py
git rm src/evoscholar/readers.py
# 注意：git rm 不是 git mv，因为原文件不再独立存在

# 6. 编辑所有 import 路径
rg "from evoscholar\.docs" src/ -l
# 替换为 from evoscholar.literature_qa.core import Docs
# 等等

# 7. 取消兼容垫片（因为路径过深，意义不大）
# 旧路径如 from evoscholar.docs 直接失效
```

### 4.3 关键引用替换

```bash
# 替换规则
# from evoscholar.docs import Docs → from evoscholar.literature_qa.core import Docs
# from evoscholar.types import DocDetails → from evoscholar.literature_qa.core import DocDetails
# from evoscholar.prompts import QA_PROMPT → from evoscholar.literature_qa.core import QA_PROMPT
# from evoscholar.readers import ... → from evoscholar.literature_qa.core import ...
# from evoscholar.paths import ... → from evoscholar.utils.paths import ...
# from evoscholar.llms import get_llm_model → from evoscholar.utils.llms import get_llm_model
# from evoscholar.llms import _TrackedLLMAdapter → from evoscholar.iterative_search.core import _TrackedLLMAdapter
```

## 5. 验证清单

```bash
# 1. utils/ 引用
python -c "from evoscholar.utils.paths import *"
python -c "from evoscholar.utils.llms import get_llm_model"
python -c "from evoscholar.utils.math_utils import *"

# 2. 各包 core.py
python -c "from evoscholar.literature_qa.core import Docs, DocDetails, PQASession"
python -c "from evoscholar.literature_qa.core import QA_PROMPT_TEMPLATE"  # 或类似常量
python -c "from evoscholar.iterative_search.core import _TrackedLLMAdapter"

# 3. 兜底：确认旧路径失效
python -c "from evoscholar.docs import Docs" 2>&1 | grep ImportError
python -c "from evoscholar.paths import *" 2>&1 | grep ImportError

# 4. 依赖反向校验（§6.3）
# utils/ 本身不应被 metadata_clients 以外的业务包耦合"反向"
# literature_qa 不应 import utils/* 之外的其他包
rg "from evoscholar\.(query_understanding|iterative_search|paper_ranker|synthesis)" src/evoscholar/literature_qa/
# 预期：空

# 5. 全部包仍能 import
python -c "from evoscholar.literature_qa import ask"
python -c "from evoscholar.iterative_search import ResearchEngine"
python -c "from evoscholar.paper_ranker import score_papers"
python -c "from evoscholar.synthesis import AnswerSummary"
python -c "from evoscholar.query_understanding import analyze_and_expand_query"
python -c "from evoscholar.metadata_clients import AcademicSearchClient"
python -c "from evoscholar.server.app import app"
```

## 6. 范围外（不要做）

- ❌ 不要修改 settings.py 内容（那是 Batch F）
- ❌ 不要让 utils/ 膨胀（每加一个文件前都要问"是否 ≥2 个包用？"）
- ❌ 不要把业务模型（如 `AcademicPaper`）放到 `utils/`
- ❌ 不要创建 `evoscholar/core/` 顶层目录（设计已经废除）
- ❌ 不要在 utils/ 放 Settings 相关的 helper

## 7. utils/ 边界控制（**严格**）

放进 utils/ 之前必须自问：

> **"如果只在 1 个包用，是不是放该包 `core.py` 更合适？"**

如果是 → 放该包 core.py
如果不是（≥2 个包用）→ 放 utils/

**禁止往 utils/ 放的**：
- 业务模型（`AcademicPaper` / `ResearchSession`）→ 各包 `models.py`
- Settings 子类 → 各包 `settings.py`
- 业务专用的辅助（如 `_TrackedLLMAdapter`）→ 各包 `core.py`

## 8. 报告模板

```
Batch E 完成
- Commit 8: <hash>  refactor: move core files to packages + create utils/ shared layer
- 验证:
  - utils/ 引用: OK
  - 各包 core.py: OK
  - 旧路径失效: OK
  - 依赖反向校验: OK
  - 全包 import: OK
- 改动文件: <list of moved/deleted/created files>
- utils/ 内容清单: <list of utils/ submodules and what they contain>
- 附带 gotchas.md 更新: <是/否>
- 任何 owner 决策争议: <list，如某个类到底该放哪个包>
```

## 9. 父 Agent 收到后

1. 验证 owner 唯一性（每个类型只有一个 home）
2. 验证 utils/ 边界（没放业务模型）
3. 进入 Batch F（Commit 9）
