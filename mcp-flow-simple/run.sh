#!/bin/bash
# MCP-Flow简化版启动脚本

echo "MCP-Flow 简化版"
echo "==============="

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到python3"
    exit 1
fi

# 检查配置
if [ ! -f "config/config.yaml" ]; then
    echo "警告: config.yaml不存在,使用示例配置"
    cp config/config.example.yaml config/config.yaml
    echo "请编辑 config/config.yaml 填写API密钥"
    exit 1
fi

# 运行
cd src
python3 main.py --tools ../mcp_tools_full_20251113_120436.json --config ../config/config.yaml
