@echo off
REM MCP-Flow Windows快速启动脚本

echo ================================
echo   MCP-Flow 环境配置和启动
echo ================================

REM 检查Python版本
echo 检查Python版本...
python --version

REM 创建虚拟环境(如果不存在)
if not exist venv (
    echo 创建虚拟环境...
    python -m venv venv
)

REM 激活虚拟环境
echo 激活虚拟环境...
call venv\Scripts\activate

REM 安装依赖
echo 安装Python依赖...
pip install -r requirements.txt

REM 安装Playwright
echo 安装Playwright浏览器...
python -m playwright install chromium

REM 检查配置文件
if not exist config.yaml (
    echo ❌ 错误: config.yaml 不存在!
    echo 请先配置 config.yaml 文件,填入API密钥
    exit /b 1
)

echo.
echo ✅ 环境配置完成!
echo.
echo 现在你可以运行:
echo   python src/main.py --step all        # 运行完整pipeline
echo   python src/main.py --step collect    # 仅收集服务器
echo   python src/main.py --step generate   # 仅生成数据
echo.

pause
