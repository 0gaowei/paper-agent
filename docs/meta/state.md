# Paper-QA "论文库场景" 删除重构

## Recent Decisions

| 时间 | 决策 | 原因 |
|---|---|---|
| 2026-08-10 | 删除 metadata_clients 论文库 Provider/Processor | 用户不用论文库场景：crossref/unpaywall/journal_quality/retractions 都属此 |
| 2026-08-10 | 删除整个 literature_qa 包 | 该包是 paperqa 上游 Docs/DocDetails/PQASession 的承载，与保留的学术搜索路径不符 |
| 2026-08-10 | 路径选 B：搜索 + 极简总结 | 保留 LLM 总结能力，但用自写轻量版替代 paperqa.Docs |
| 2026-08-10 | 在 refactor/simplify-no-paper-library 分支推进 | 主分支 paper-agent 不受影响，可随时回退 |
| 2026-08-10 | 用 HANDOFF 文档交接 | 单次会话上下文用尽，分 Phase 推进更可靠 |

## Current State (WIP)

- branch: `refactor/simplify-no-paper-library`
- last commit: `6454572` wip: 删除 metadata_clients 论文库 Provider/Processor + literature_qa 全包
- 项目**当前不可运行**（`from evoscholar import ...` 报 ImportError）
- WIP 详情见 `.cursor/HANDOFF-2026-08-10-23-no-paper-library-simplify.md`

## Pending

- Phase A-G 依次推进（见 HANDOFF 文档）
- 每 Phase 完成后单独 commit + 单独测试
