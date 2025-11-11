#!/bin/bash

# MCP-Flow 快速启动脚本

echo "================================"
echo "  MCP-Flow 环境配置和启动"
echo "================================"

# 检查Python版本
echo "检查Python版本..."
python --version

# 创建虚拟环境(如果不存在)
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python -m venv venv
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null

# 安装依赖
echo "安装Python依赖..."
pip install -r requirements.txt

# 安装Playwright
echo "安装Playwright浏览器..."
python -m playwright install chromium

# 检查配置文件
if [ ! -f "config.yaml" ]; then
    echo "❌ 错误: config.yaml 不存在!"
    echo "请先配置 config.yaml 文件,填入API密钥"
    exit 1
fi

# 检查API密钥
echo "检查API配置..."
if grep -q "your-openai-api-key" config.yaml; then
    echo "⚠️  警告: 请在 config.yaml 中配置你的 OpenAI API 密钥!"
    exit 1
fi

echo ""
echo "✅ 环境配置完成!"
echo ""
echo "现在你可以运行:"
echo "  python src/main.py --step all        # 运行完整pipeline"
echo "  python src/main.py --step collect    # 仅收集服务器"
echo "  python src/main.py --step generate   # 仅生成数据"
echo ""
