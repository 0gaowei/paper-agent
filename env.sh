#!/bin/bash
# 激活 paper-qa conda 环境并加载 .env 文件

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 激活 conda 环境
eval "$(~/miniconda3/bin/conda shell.bash hook)"
conda activate paper-qa

# 加载 .env 文件（如果存在）
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
    echo "✓ 已加载 .env 文件中的环境变量"
fi

echo "✓ 已激活 conda 环境: paper-qa"
echo "✓ Python 路径: $(which python)"
