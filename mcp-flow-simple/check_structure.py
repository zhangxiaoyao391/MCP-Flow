import os
from pathlib import Path

print("=" * 60)
print("MCP-Flow 简化版 - 项目结构检查")
print("=" * 60)

required_files = {
    "核心代码": [
        "src/main.py",
        "src/data_generator/__init__.py",
        "src/data_generator/generator.py",
        "src/data_filter/__init__.py",
        "src/data_filter/filter.py",
        "src/utils/__init__.py",
        "src/utils/llm_client.py",
    ],
    "工具模块": [
        "wizard_utils/breadth.py",
        "wizard_utils/depth.py",
    ],
    "配置文件": [
        "config/config.example.yaml",
        "requirements.txt",
    ],
    "文档": [
        "README.md",
        "USAGE.md",
        "PROJECT_SUMMARY.md",
    ],
    "数据目录": [
        "data/function_call",
        "data/filtered",
    ],
    "输入数据": [
        "mcp_tools_full_20251113_120436.json",
    ]
}

all_ok = True
for category, files in required_files.items():
    print(f"\n【{category}】")
    for file in files:
        exists = Path(file).exists()
        status = "✓" if exists else "✗"
        print(f"  {status} {file}")
        if not exists:
            all_ok = False

print("\n" + "=" * 60)
if all_ok:
    print("✓ 项目结构完整!")
else:
    print("✗ 有文件缺失,请检查")
print("=" * 60)
