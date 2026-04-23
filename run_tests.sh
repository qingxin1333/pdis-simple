#!/bin/bash
# 项目测试运行脚本

# 自动激活环境和设置路径
source /mnt/d/workspaceAI/pyAiTest/.venv/bin/activate
cd /mnt/d/workspaceAI/pyAiTest

echo "🧪 运行 Qdrant 测试..."
python test/test_qdrant_simple.py

echo -e "\n📊 运行 PDIS 测试..."
python test/test_pdis_simple.py

echo -e "\n✅ 所有测试完成"