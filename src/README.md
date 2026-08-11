# Paper-Search-Agent

基于 PaperQA2 的论文搜索 Agent，支持 Web UI。

## 快速启动

### 1. 安装依赖并启动后端

```bash
cd /path/to/paper-qa

# 首次：创建虚拟环境并装好所有依赖
uv sync --all-extras

# 启动后端服务（使用 .venv 中的 Python）
uv run pqa-serve
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
