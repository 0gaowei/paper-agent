#!/bin/bash
# 使用 uv 运行命令（自动激活 .venv）
# 用法: uv run <command> 或直接运行已安装的工具

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 加载 .env 文件（如果存在）
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
    echo "✓ 已加载 .env 文件中的环境变量"
fi

echo "✓ 使用 uv 运行命令，示例:"
echo "  uv run pqa-serve       # 启动后端服务"
echo "  uv run pytest          # 运行测试"
echo "  uv sync               # 同步依赖"
