# Agent Tasks 索引

> **本目录**是为各 AI Agent 准备的批量化执行任务。每个文件对应 refactor-plan 的一个 Batch。

## 启动顺序

按依赖关系：

```
A → B → C → D → E → F → G
```

## 子任务文档

| Batch | 文件 | 包含 Commit | 风险 | 可并行？ |
|---|---|---|---|---|
| A | [batch-A.md](batch-A.md) | Commit 0, 1 | 低 | 否（前置） |
| B | [batch-B.md](batch-B.md) | Commit 2, 3 | 低 | ✓ 内部并行 |
| C | [batch-C.md](batch-C.md) | Commit 4, 5, 7 | 中 | ✓ 内部并行 |
| D | [batch-D.md](batch-D.md) | Commit 6 | 中高 | 否 |
| E | [batch-E.md](batch-E.md) | Commit 8 | 中 | 否 |
| F | [batch-F.md](batch-F.md) | Commit 9 | 中 | 否 |
| G | [batch-G.md](batch-G.md) | Commit 10 | 高 | 否 |

## 启动 Agent 模板

**必读**：
1. `docs/meta/agent-context.md`（**总览 + 通用规则**）
2. 本目录对应 `batch-{X}.md`（**具体任务**）
3. `docs/meta/refactor-plan.md`（按子任务文档指引读对应章节）

**Agent 启动 prompt**：

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

## 当前进度

> 由父 Agent 在每个 Batch 完成后更新。详见 `agent-context.md` §4。
