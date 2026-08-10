# Paper-QA "论文库场景" 删除重构

## Recent Decisions

| 时间 | 决策 | 原因 |
|---|---|---|
| 2026-08-10 | 删除 metadata_clients 论文库 Provider/Processor | 用户不用论文库场景：crossref/unpaywall/journal_quality/retractions 都属此 |
| 2026-08-10 | 删除整个 literature_qa 包 | 该包是 paperqa 上游 Docs/DocDetails/PQASession 的承载，与保留的学术搜索路径不符 |
| 2026-08-10 | 路径选 B：搜索 + 极简总结 | 保留 LLM 总结能力，但用自写轻量版替代 paperqa.Docs |
| 2026-08-10 | 在 refactor/simplify-no-paper-library 分支推进 | 主分支 paper-agent 不受影响，可随时回退 |
| 2026-08-10 | 用 HANDOFF 文档交接 | 单次会话上下文用尽，分 Phase 推进更可靠 |
| 2026-08-10 | Phase A+B 落地：新建 lightning.PaperDetail + metadata_clients Provider 切到轻量模型 | HANDOFF Phase A+B 推进完毕，已 commit 9d885c1。项目仍不可运行（__init__ 还引用 lit_qa，Phase E 处理） |
| 2026-08-10 | 局部复活 exceptions.py / client_models.py（仅搜索 Provider 需要的最小集） | HANDOFF 漏掉的事实：crossref/client_models 是 Provider 仍依赖的脚手架。最小复活而非全量复活 crossref，避免重新引入 lit_qa 引用 |
| 2026-08-10 | 删除 Semantic Scholar 的 Crossref bibtex 兜底路径 | bibtex 是论文库场景功能；S2 自带 citationStyles.bibtex 已覆盖 90%+ 场景；继续走 crossref 会被强制重新引入 lit_qa |

## Current State (WIP)

- branch: `refactor/simplify-no-paper-library`
- last commit: `9d885c1` refactor(lightning): Phase A+B - PaperDetail 模型 + 3 个 Provider 切到轻量模型
- 项目**当前不可运行**（`from evoscholar import ...` 报 ImportError，因为 __init__.py 还引用 lit_qa，下一 Phase 处理）
- Phase A+B 完成 ✅（lightning.PaperDetail + 3 个 Provider 切完）
- Phase C-G 待做（utils.llms/types/readers/contrib → iterative_search.engine/synthesis.builder → __init__/server → 清理冗余模块 → 测试）
- WIP 详情见 `docs/meta/HANDOFF-2026-08-10-23-no-paper-library-simplify.md`

## Pending

- Phase C-G 依次推进（见 HANDOFF 文档）
- 每 Phase 完成后单独 commit + 单独测试
