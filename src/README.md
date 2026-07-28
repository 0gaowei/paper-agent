# Paper-Search-Agent-Backend

## 项目简介

Paper-Search-Agent-Backend 是一个基于 Python 和 FastAPI 的论文搜索代理后端。它提供了一个 RESTful API，用于搜索和获取论文信息。

## 项目结构

```
Paper-Search-Agent-Backend
1. API 服务层(scr/paperqa/server/)
    - app.py: FastAPI 应用和Lifespan管理
    - bridge.py & events.py: SSE 流和搜索引擎桥接
    - repository.py & schemas.py: 本地Session存储与JSON schemas
    - routes/: 模块化API endpoints（sessions, papers, settings, etc.)

2. Research & Search Agent(src/paperqa/research/ & /agents/)
    - engine.py: ResearchEngine, Agentic搜索与合成循环
    - query_understanding.py: 

```
