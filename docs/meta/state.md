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
| 2026-08-11 | Phase E 完成：新建 configs.settings.Settings 替代 lit_qa.settings | 只承载 in-tree 实际使用的字段（llm/llm_config/embedding/research），不做完整功能恢复 |
| 2026-08-11 | Phase F 删除 _ldp_shims.py + iterative_search/core.py | 两个模块均无 in-tree 调用方（LDP agent 框架未用，_TrackedLLMAdapter 已搬到 synthesis/builder.py） |
| 2026-08-11 | **项目恢复运行**：`from evoscholar import ...` + `uvicorn evoscholar.server.app:app` + `curl /health` + `curl /api/settings` 全部 PASS | Phase A-G 全部完成；论文库场景彻底删除，搜索+极简总结路径完整 |
| 2026-08-11 | 清理论文库场景残留：删除 zotero/openreview contrib 与 docs/tutorials/* | 跟上一次重构同步：删除 contrib/zotero.py, contrib/openreview_paper_helper.py, configs/openreview.json；pyproject.toml 移除 zotero/openreview extras；env.sh 改用 uv |
| 2026-08-11 | 删除 Semantic Scholar 搜索源，默认 providers 改为 `["openalex"]` | 用户反馈申请 S2 API key 麻烦；OpenAlex 已覆盖全文搜索/元数据/引用/abstract 反向索引等核心能力，无需 key。建议设置 `OPENALEX_MAILTO` 提升优先级 |
| 2026-08-11 | 删除 S2 后同步移除相关 API 字段（事件/设置/学术论文模型） | 避免前后端 schema 残留死字段：`DocsJsonSchema.s2_id` / `SettingsPayload.s2_configured` / `AcademicPaper.s2_id` / `PaperSource.SEMANTIC_SCHOLAR` / 前端 `s2Id` 类型 + `s2_id/s2_configured` camelCase 映射全部删除 |
| 2026-08-11 | 前端 dataSources 简化为仅 OpenAlex | 与后端搜索 provider 单一化同步：删除 arXiv/Semantic Scholar/PubMed/IEEE Xplore 占位条目，settings 页面只显示 OpenAlex |

## Current State (WIP)

- branch: `refactor/simplify-no-paper-library`
- last commit: `381aaba` 删除 Semantic Scholar：默认搜索源仅 OpenAlex
- **✅ Phase A-G 全部完成**
- **项目可运行**：`python -c "from evoscholar import __version__"` ✅
- **服务器可启动**：`uvicorn evoscholar.server.app:app` + `curl /health` + `curl /api/settings` ✅
- 所有论文库场景（Docs/DocDetails/PQASession/Text/crossref/unpaywall/journal_quality/retractions/AskText/agent_query）均已删除
- 13 个 API 路由全部 wired（sessions/papers/graph/history/settings/usage + SSE events）
- 详细信息见各 Phase commit + `docs/meta/HANDOFF-2026-08-10-23-no-paper-library-simplify.md`

## Pending (next session 可能做的工作)

1. 删除 `tests/` （已被先前的 7dcfaa7 删除，无需做）
2. **回归测试** —— 之前 WIP 状态下 tests 已被删；下一步可以选恢复并适配
3. **删除 `pyproject.toml` 中已不用的依赖**（lmi 用 `fhlmi>=0.45.0` 等；qdrant-client / pybtex 等论文库相关可能要剔除）
4. **二次 PR 给 upstream** —— 论文库场景改造在 0gaowei/paper-agent 单边持有，可考虑贡献到 Future-House/paper-qa（如对方也想要）

## Pending

- ~~Phase C-G 依次推进（见 HANDOFF 文档）~~
- ~~每 Phase 完成后单独 commit + 单独测试~~
- Phase C-G 已全部完成（见 Current State）
