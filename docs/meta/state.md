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
| 2026-08-10 | Phase C 清理：删 utils/llms.py 的 VectorStore/NumpyVectorStore/QdrantVectorStore、删 types.py、删 readers.py、inline zotero PDFParserFn | 这 3 个文件只剩 __pycache__ 时是论文库场景的"脚手架"，无任何 in-tree 调用方 |
| 2026-08-10 | Phase D 极简答案合成器：替换 Docs/DocDetails/Text 全套为 lightning.answer_builder | 搜索场景只有 abstract，向量化反而低效；每 paper 一次 LLM 调用同时判断相关性 + 抽取 snippet，复杂度大幅降低 |
| 2026-08-10 | _format_citation 提到 lightning.answer_builder 模块顶层，engine 与 answer_builder 共用 | 原 engine.py 的 _EvidenceAdapter._citation 与 synthesis/builder.py 的 _citation 重复实现；DRY 改进 |

## Current State (WIP)

- branch: `refactor/simplify-no-paper-library`
- last commit: `d302b7b` refactor(lightning): Phase D - 替换 Docs/DocDetails/Text 为极简答案合成
- 项目**当前不可运行**（`from evoscholar import ...` 报 ImportError，因为 __init__.py 还引用 lit_qa，下一 Phase 处理）
- Phase A+B+C+D 完成 ✅（lightning 包就绪 + Provider 切完 + utils 清理 + iterative_search/synthesis 改造）
- Phase E-G 待做（__init__.py + server/ + 删冗余 + 测试）
- WIP 详情见 `docs/meta/HANDOFF-2026-08-10-23-no-paper-library-simplify.md`

## Pending

- Phase C-G 依次推进（见 HANDOFF 文档）
- 每 Phase 完成后单独 commit + 单独测试
