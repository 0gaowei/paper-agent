# Agent 执行 Context（重构分批执行）

> **本文件用途**：将 `refactor-plan.md` 拆解为多个 batch，分发给不同 AI Agent 并行/串行执行。
> 每个 Agent **只读本文件 + 自己的 batch 子文档**，再交叉引用 `refactor-plan.md` 对应章节。
> **不要连读完整 refactor-plan.md**——那是给人看的，Agent 只需要按本文件 + 子任务文档指引。

---

## 0. 30 秒总览

### 项目

- **包名**：`paperqa` → `evoscholar`（自进化论文搜索代理）
- **当前结构**：单体包（`src/paperqa/`，~1357 行 `settings.py` + 多个子包）
- **目标结构**：7 个功能包 + 1 个 `utils/` 共享层 + 1 个 `server/` 入口
- **总方案**：`docs/meta/refactor-plan.md`（1078 行）

### 关键决策（已固定，不要质疑）

| 决策 | 含义 |
|---|---|
| **每个功能包独立** | `literature_qa/`、`iterative_search/` 等互不直接依赖业务代码，只能引用 `utils/` 或对方的**公开类型**（owner 公开的 models / 入口） |
| **core.py 下沉** | 不存在顶层 `evoscholar/core/`；每个包有自己的 `core.py`，是该包专属核心设施 |
| **settings.py 下沉** | 不存在顶层 `evoscholar/settings/`；每个包有自己的 `settings.py`，是该包专属 Settings |
| **utils/ 共享层** | 仅放 ≥2 个功能包都需要的工具（`utils/paths.py` / `utils/llms.py` / `utils/math_utils.py` 等） |
| **owner 唯一性** | 同一个核心类型（如 `Docs`）只能有一个 owner（`literature_qa`），其他包只能引用 |
| **兼容垫片** | 保留到 Batch G（Commit 10）一起删除 |

### → 详细决策与边界

- 目录结构：`refactor-plan.md` §1
- 各包职责：`refactor-plan.md` §2
- 依赖矩阵：`refactor-plan.md` §6.3（**铁律级别，违反会被 commit hook 拦截**）
- Prompts 边界：`refactor-plan.md` §6.4

---

## 1. Batch 划分（依赖关系）

```
Batch A (串行, 2 commits)
    ├─ Commit 0: 包重命名 paperqa → evoscholar
    └─ Commit 1: 基础设施准备（pyproject 等）
        ↓
Batch B (并行, 2 commits)  ← 互相独立
    ├─ Commit 2: clients/ → metadata_clients/
    └─ Commit 3: query_understanding/
        ↓
Batch C (部分并行, 3 commits)
    ├─ Commit 4: iterative_search/         ← 可与 5/7 并行
    ├─ Commit 5: paper_ranker/             ← 可与 4/7 并行（4 不依赖 5）
    └─ Commit 7: literature_qa/ (原 agents/) ← 完全独立，可与 4/5 任意并
        ↓
Batch D (串行, 1 commit)
    └─ Commit 6: synthesis/ + SSE 拆分（依赖 4，不依赖 7）
        ↓
Batch E (串行, 1 commit)
    └─ Commit 8: 根目录文件 → 各包 core.py + utils/
        ↓
Batch F (串行, 1 commit)
    └─ Commit 9: settings.py → 各包 settings.py（依赖 8）
        ↓
Batch G (串行, 1 commit)
    └─ Commit 10: 清理垫片
```

### 依赖图（精确）

```
0 → 1 → {2, 3} → {4, 5, 7} → 6 → 8 → 9 → 10
                ↑
                └── 4 和 5 互不依赖（可并行）
                └── 7 与 4/5/6 都不依赖（可与 4/5 并行）
                └── 6 仅依赖 4（要从 iterative_search/engine.py 抽 _build_evidence_and_answer）
```

### 每个 Batch 风险

| Batch | 风险 | 配套动作 |
|---|---|---|
| A | 低 | 每个 commit 后跑 §8 基础 import 测试 |
| B | 低 | 任一 commit 失败就回滚 |
| C | 中 | 完成后跑对应包的全部 import 测试 |
| D | 中偏高 | 必须做字段映射校验（roadmap.md §6） |
| E | 中 | 跨包 impact 大，每个旧路径都需更新 |
| F | 中 | 主 Settings 聚合需遍历所有 settings.py |
| G | 高 | 是破坏性变更，必须前置所有测试通过 |

---

## 2. Agent 通用规则（每个 batch 都要遵守）

### 2.1 进入工作前必读

每个 Agent 进入工作前必须熟读：

1. **本文件**（你正在读的）
2. 自己的 **`batch-X.md` 子任务文档**（在 `agent-tasks/` 目录）
3. **`refactor-plan.md` 相关章节**（子任务文档会指明）
4. **`docs/meta/gotchas.md`**（如果有，先扫一遍避免重蹈覆辙）

### 2.2 工作流程

每个 Agent 严格按以下流程：

```
1. 读 batch-{X}.md → 确认目标 commit
2. 读 refactor-plan.md 中该 commit 的全部内容（子文档会指明行号）
3. git status 查看当前 dirty 状态（必须 clean）
4. git log --oneline -5 确认上一个 commit 已完成
5. 准备工作：创建分支（如果 Batch 跨 commit）
6. 执行 commit 内容（git mv / 文件编辑）
7. 跑该 commit 的 §验证 脚本
8. 如果验证全部通过 → git commit
9. 如果验证失败 → 修复或回滚（不要把失败 commit 提交）
10. 报告完成 → 父 Agent 接到后继续下一批
```

### 2.3 提交规范

- **Commit message 格式**：`refactor: <一句话描述>`（参考 `refactor-plan.md` §7 Commit 标题）
- **Body 引用**：附 `refactor-plan.md §Commit X` + `agent-tasks/batch-{X}.md`
- **粒度**：一个 commit 一次提交，不要把多个 commit 合并成一个 commit
- **失败处理**：commit 失败就回滚，不要 amend 或 force-push

### 2.4 严禁事项

- ❌ **不要执行范围外的操作**：你的 batch 文档只描述少量 commit，不要擅自做其他重构
- ❌ **不要修改 refactor-plan.md**：那是要遵循的圣经，修改它等于改需求
- ❌ **不要删除兼容垫片**（除非 Batch G 文档明确允许）
- ❌ **不要跨包引入反依赖**（违反 §6.3 铁律的 import 会被 commit hook 拦截）
- ❌ **不要在重构 commit 里夹带功能修复**（详见 gotchas.md 习惯）
- ❌ **不要修改其他 batch 的代码**：如果发现其他 batch 负责的代码有问题，记录到 `gotchas.md`，留给对应 batch 的 Agent 修

### 2.5 验证清单

每个 commit 完成后必须跑：

```bash
# 1. 基础 import
python -c "import evoscholar"

# 2. 该 commit 的 §验证 脚本（子任务文档里会列出）

# 3. 依赖反向校验（§6.3 铁律）
rg "from evoscholar\.(query_understanding|iterative_search|paper_ranker|synthesis)" src/evoscholar/literature_qa/
rg "from evoscholar\.(iterative_search|paper_ranker|synthesis|literature_qa)" src/evoscholar/query_understanding/
rg "from evoscholar\.synthesis" src/evoscholar/paper_ranker/
rg "from evoscholar\.metadata_clients" src/evoscholar/synthesis/

# 4. 全量测试（如果改动范围大）
pytest tests/ -x -q --tb=short
```

---

## 3. 子任务文档索引

每个 Batch 的具体工作在 `agent-tasks/batch-{X}.md`：

| Batch | 文件 | 包含 Commit |
|---|---|---|
| A | `agent-tasks/batch-A.md` | Commit 0, 1 |
| B | `agent-tasks/batch-B.md` | Commit 2, 3 |
| C | `agent-tasks/batch-C.md` | Commit 4, 5, 7 |
| D | `agent-tasks/batch-D.md` | Commit 6 |
| E | `agent-tasks/batch-E.md` | Commit 8（core 下沉 + utils/） |
| F | `agent-tasks/batch-F.md` | Commit 9（settings 下沉） |
| G | `agent-tasks/batch-G.md` | Commit 10（清理垫片） |

**Agent 启动 prompt 模板**：

```
你的任务：执行 Batch {X}（docs/meta/agent-tasks/batch-{X}.md）

必读：
1. docs/meta/agent-context.md（总状态 + 规则）
2. docs/meta/agent-tasks/batch-{X}.md（具体任务）
3. refactor-plan.md 中指定章节

完成后输出：
- 改了哪些文件
- 跑过的验证命令 + 结果
- commit hash
- 任何超出的发现（写 gotchas.md）
```

---

## 4. 当前进度

> **本节由父 Agent 在每个 Batch 完成后更新**。子 Agent 进来时先看本节确认上一个 Batch 已经完成。

| Batch | 状态 | commit hash | 备注 |
|---|---|---|---|
| A | 已完成 | c1abafb (Commit 0) / 1ca5bb4 (Commit 1) | 包重命名 + 骨架创建 |
| B | 已完成 | afba223 (Commit 2) / a462e43 (Commit 3) | clients→metadata_clients + query_understanding 提取 |
| C | 已完成 | f453d7c (Commit 4) / a677bc5 (Commit 5) / a38731a (Commit 7) | iterative_search + paper_ranker + literature_qa 提取 |
| D | 已完成 | 716a5c9 (Commit 6) | synthesis 包提取 + SSE 事件拆分 |
| E | 已完成 | 539c8b7 (Commit 8) | 根目录文件 → 各包 core.py + utils/ |
| F | 已完成 | a2b4c50 (Commit 9) | settings 下沉 + Server Settings 合并 |
| G | 已完成 | 41cb9f9 (Commit 10) | 清理所有 compat shim + paperqa alias 保留 |

**Batch G 子 Agent 报告**：
```
Batch G 完成
- Commit 10: 41cb9f9  refactor: 删除所有兼容垫片（Commit 10）
- 验证:
  - 旧路径失效: OK (17 个旧 import path 全部 ImportError)
  - 新路径正常: OK (literature_qa / iterative_search / paper_ranker / synthesis /
              query_understanding / metadata_clients / server / utils 全部 import OK)
  - 全量测试: 部分失败（19 个 research_engine + 22 个 clients/clinical_trials =
              41 个失败，全部是预存条件：缺少 paper-qa-pypdf/mupdf wheel 或
              journal_quality.csv 数据文件，非 Batch G 引入）
  - 依赖反向校验: OK (literature_qa/settings.py → iterative_search/settings 是
                §3.5.2 文档豁免的聚合器依赖)
- 删除的兼容垫片:
  - 目录: src/evoscholar/agents/, src/evoscholar/research/, src/evoscholar/settings/ (空)
  - 文件: src/evoscholar/clients.py, src/evoscholar/utils_helpers.py
  - re-export: iterative_search/models.py 里 re-export from synthesis.models
- 改动文件: src/evoscholar/__init__.py, contrib/openreview_paper_helper.py,
  iterative_search/{engine.py,models.py}, paper_ranker/{mmr.py,ranker.py},
  server/{app.py,bridge.py,routes/sessions.py}, synthesis/models.py,
  utils/__init__.py + 新建 utils/_helpers.py (utils_helpers.py 重命名),
  7 个测试文件 (conftest + test_{academic_search,agents,cli,clients,configs,
  paperqa,research_engine,server}), README.md, README-zh.md
- 附带 gotchas.md 更新: 是 (新增 3 条: utils_helpers 重定向, paperqa alias
  生效场景, iter↔synth cycle 复活)
- 任何遗留的兼容问题:
  - paperqa sys.modules 别名保留（用户决策 Q3a）。它在 evoscholar 已加载后
    才生效，正好满足 paperqa_pypdf/pymupdf 的使用场景
```

**子 Agent 报告完成时的格式**：

```
Batch {X} 完成
- Commit X: <hash>  <commit message>
- 验证: <全部通过 / 部分失败已修复 / 失败未通过>
- 改动文件: <list>
- 附带 gotchas.md 更新: <是/否>
```

父 Agent 接到后：

1. 更新本节 `当前进度` 表
2. 决定下一个 Batch（参考 §1 依赖图）
3. 按 §3 模板启动下一个 Agent

---

## 5. 应急：失败处理

### 5.1 验证失败

- 仔细看错误日志（不要假设是本 commit 引入的——先 `git status` 确认 dirty 状态）
- 如果是本 commit 引起的 → 修复后 amend（如果未推送）或新 commit
- 如果是历史 dirty 引入的 → 不要管，记录到 gotchas.md

### 5.2 依赖反向校验失败

意味着你的修改违反 §6.3 铁律。检查：

- 没有跨包 import 业务代码
- 只用 `utils/*` 和 owner 公开类型
- 没有 import 其他包的 `_private` helper

### 5.3 跟之前 Agent 的改动冲突

- 不要试图合并
- 让父 Agent 决定是 rebase 还是丢弃你的改动
- 父 Agent 会另起一个 batch 重新执行

### 5.4 超出能力范围

如果发现本 batch 的 commit 描述与现状不一致，**不要猜测**：

```
报告：Batch {X} 无法执行
原因: <commit 描述与现状不一致 / 缺少前置 commit / 等等>
建议: <需要回退到 Batch Y / 需要更新 refactor-plan.md / 需要人工介入>
```

---

## 6. 状态文件维护

### 6.1 子 Agent 维护

每个 commit 完成后：

1. 如果发现 **新坑**（修复过程中遇到、值得记录）→ 追加到 `docs/meta/gotchas.md`
2. **不要**主动修改 `docs/meta/state.md`（那是主 Agent 维护的）

### 6.2 父 Agent 维护

每个 Batch 完成后：

1. 更新本文件 §4 当前进度表
2. 如果有需要全局知会的事 → 更新 `docs/meta/state.md`
3. 启动下一个 Batch 子 Agent

---

## 7. 参考链接

- **总方案**：`docs/meta/refactor-plan.md`（1078 行）
- **当前状态**：`docs/meta/state.md`
- **踩坑记录**：`docs/meta/gotchas.md`
- **roadmap（含字段映射）**：`private-docs/roadmap.md`（**Commit 6 必读**）
- **子任务文档**：`docs/meta/agent-tasks/batch-{A..G}.md`

---

> **最后提醒**：每个 Agent 是 **无状态的**——你不需要继承父 Agent 的上下文，只需要读完本文件 + 自己的 batch 文档 + refactor-plan.md 对应章节，就能开工。
