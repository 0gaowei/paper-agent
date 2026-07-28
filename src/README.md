# Paper-Search-Agent

基于 PaperQA2 的论文搜索 Agent，支持 Web UI。

## 快速启动

### 1. 后端

```bash
cd /path/to/paper-qa
source env.sh
pqa-serve
```

API 文档: http://localhost:8000/docs

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

访问: http://localhost:5173

## 配置

编辑 `.env` 文件：

- `OPENAI_API_KEY` / `OPENAI_BASE_URL` — LLM API
- `EMBEDDING` — 嵌入模型（默认使用 sentence-transformers 本地模型）
- `PQA_PORT` — 后端端口（默认 8000）
- `PQA_CORS_ORIGINS` — 前端地址（默认 http://localhost:5173）
