# MCP-Flow 简化版

自动化生成高质量Function Calling训练数据

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置API
cp config/config.example.yaml config/config.yaml
# 编辑config.yaml填写API密钥

# 3. 运行
cd src
python main.py --tools ../mcp_tools_full_20251113_120436.json
```

## 项目结构

```
mcp-flow-simple/
├── src/
│   ├── main.py                  # 主入口
│   ├── data_generator/          # 数据生成模块
│   ├── data_filter/             # 数据过滤模块
│   └── utils/                   # 工具模块
├── wizard_utils/                # Evolution工具
├── config/                      # 配置目录
├── data/                        # 输出数据
└── README.md
```

## 数据生成流程

1. **Few-shot生成** - 生成基础指令
2. **Slot-fill修订** - 填充参数
3. **WizardLM Evolution** - 增加复杂度
4. **Function Call生成** - 生成完整样本

## 数据过滤

1. 工具调用验证
2. 质量评分(LLM)
3. 轨迹验证

详细文档请查看 USAGE.md
