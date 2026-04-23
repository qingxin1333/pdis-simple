#!/bin/bash
# PyCharm 终端自动设置脚本

# 激活虚拟环境
source /mnt/d/workspaceAI/pyAiTest/.venv/bin/activate

# 切换到项目根目录
cd /mnt/d/workspaceAI/pyAiTest

# 显示当前环境信息
echo "🚀 已激活虚拟环境: $(which python)"
echo "📁 当前工作目录: $(pwd)"
echo "🔧 Python 版本: $(python --version)"

# 可选：设置项目特定的环境变量
export PROJECT_ROOT="/mnt/d/workspaceAI/pyAiTest"
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH}"

echo "✅ 环境设置完成"