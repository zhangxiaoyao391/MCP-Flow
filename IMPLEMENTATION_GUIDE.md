# MCP-Flow 实现指南

基于论文"MCP-FLOW: FACILITATING LLM AGENTS TO MASTER REAL-WORLD, DIVERSE AND SCALING MCP TOOLS"的完整实现。

## 📖 项目概述

MCP-Flow是一个自动化的Web Agent驱动pipeline,用于:
1. 🔍 从多个marketplace自动收集MCP服务器
2. 📊 生成高质量的instruction-function call数据集
3. 🎯 训练小型LLM掌握真实MCP工具使用

## 🏗️ 项目结构

```
MCP-Flow/
├── config.yaml                 # 主配置文件
├── requirements.txt            # Python依赖
├── src/
│   ├── main.py                # 主流程脚本
│   ├── server_collector/      # 服务器收集模块
│   │   ├── collector.py       # Web Agent爬虫
│   │   └── mcp_client.py      # MCP客户端
│   ├── data_generator/        # 数据生成模块
│   │   └── generator.py       # Few-shot + Slot-fill + Evolution
│   ├── data_filter/           # 数据过滤模块
│   │   └── filter.py          # 多维度质量控制
│   ├── model_trainer/         # 模型训练模块
│   │   └── trainer.py         # LoRA微调
│   └── utils/                 # 工具函数
├── data/                      # 数据目录
│   ├── servers/               # 服务器配置
│   ├── tools/                 # 工具信息
│   ├── instructions/          # 生成的指令
│   ├── filtered/              # 过滤后的数据
│   ├── function_call/         # 函数调用
│   └── trajectory/            # 轨迹数据
├── models/                    # 训练的模型
└── mcp_config/                # MCP配置文件
```

## 🚀 快速开始

### 1. 环境配置

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 安装Playwright浏览器
playwright install chromium
```

### 2. 配置API密钥

编辑`config.yaml`,填入你的API密钥:

```yaml
api_keys:
  openai_api_key: "sk-..."
  deepseek_api_key: "sk-..."
```

### 3. 运行Pipeline

```bash
# 运行完整pipeline
python src/main.py --step all

# 或分步运行:

# 步骤1: 服务器收集
python src/main.py --step collect

# 步骤2: 工具提取
python src/main.py --step extract

# 步骤3: 数据生成
python src/main.py --step generate

# 步骤4: 数据过滤
python src/main.py --step filter

# 步骤5: 模型训练
python src/main.py --step train
```

## 📊 核心功能详解

### 1. 服务器收集 (Section 3.1)

**实现方式**: 使用Playwright Web Agent自动化爬取

**支持的Marketplaces**:
- ✅ Smithery (https://smithery.ai)
- ✅ Glama (https://glama.ai/mcp/servers)
- ✅ MCP.so (https://mcp.so)
- ✅ MCPHub (https://mcphub.com)
- ✅ PulseMCP (https://pulsemcp.com/servers)
- ✅ PipeDream (https://mcp.pipedream.com)

**去重策略**: 基于工具描述列表的MD5哈希

### 2. 数据生成 (Section 3.2)

**Pipeline流程**:
```
Few-shot生成(5条) → Slot-fill修订 → WizardLM Evolution(depth=2) → 函数调用生成
```

**关键参数**:
- 每个工具生成5条指令
- Evolution深度: 2
- Temperature: 0.7
- 使用GPT-4o生成

### 3. 数据过滤 (Section 3.3)

**四重过滤机制**:

1. **嵌入相似度过滤**
   - 模型: mixedbread-ai/mxbai-embed-large-v1
   - 阈值: 0.8
   - 过滤与工具描述过于相似的指令

2. **工具调用验证**
   - GPT-4o + DeepSeek-V3双重验证
   - 必须两个模型都正确识别工具

3. **质量评分过滤**
   - 使用DeepSeek-V3评分
   - 阈值: 6/10
   - 评估清晰度、具体性、相关性、完整性

4. **Trajectory过滤**
   - 过滤无效的工具响应
   - 检查错误和内容完整性

### 4. 模型训练 (Section 4)

**LoRA配置**:
- Rank: 16
- Alpha: 32
- Learning Rate: 5e-5
- Batch Size: 2
- Gradient Accumulation: 8

**支持的Backbone模型**:
- Qwen/Qwen3-0.6B
- Qwen/Qwen3-4B
- meta-llama/Llama-3.1-8B-Instruct

## 📈 预期结果

根据论文实验结果:

| 模型 | Tool准确率 | Param准确率 | AST准确率 |
|------|-----------|-----------|----------|
| MCP-Flow (Qwen3-0.6B) | 96.8% | 87.2% | 75.4% |
| MCP-Flow (Qwen3-4B) | 99.2% | 91.8% | 81.2% |
| MCP-Flow (Llama3.1-8B) | 98.6% | 91.0% | 81.6% |

对比SOTA模型:
- GPT-4o: 88.6% / 68.2% / 58.8%
- Claude-4-Sonnet: 85.8% / 68.6% / 56.6%

## 🔧 高级配置

### 自定义Evolution方法

在`src/data_generator/generator.py`中修改:

```python
evolution_methods = [
    "你的自定义evolution方法1",
    "你的自定义evolution方法2",
]
```

### 调整过滤阈值

在`config.yaml`中修改:

```yaml
data_filtering:
  similarity_threshold: 0.8  # 嵌入相似度阈值
  quality_score_threshold: 6  # 质量评分阈值(0-10)
```

### 添加新的Marketplace

在`config.yaml`中添加:

```yaml
marketplaces:
  - name: "your_marketplace"
    url: "https://example.com"
    type: "playwright"  # 或 "sdk"
```

## 📝 数据格式

### 生成的数据样本格式

```json
{
  "server_id": "hash_value",
  "server_name": "Weather Server",
  "tool_name": "get_weather",
  "tool_description": "Get current weather information",
  "instruction": "What's the temperature in New York?",
  "function_call": {
    "name": "get_weather",
    "arguments": {
      "location": "New York",
      "unit": "celsius"
    }
  },
  "quality_score": 8
}
```

## 🐛 常见问题

### 1. Playwright安装失败

```bash
# 手动安装
python -m playwright install chromium
```

### 2. CUDA内存不足

- 减小batch_size
- 使用gradient_checkpointing
- 使用8bit量化: `load_in_8bit=True`

### 3. API调用失败

- 检查API密钥是否正确
- 检查网络连接
- 增加重试机制

## 📚 引用

如果使用本实现,请引用原论文:

```bibtex
@article{wang2025mcpflow,
  title={MCP-FLOW: FACILITATING LLM AGENTS TO MASTER REAL-WORLD, DIVERSE AND SCALING MCP TOOLS},
  author={Wang, Wenhao and Niu, Peizhi and Xu, Zhao and Chen, Zhaoyu and Du, Jian and others},
  journal={arXiv preprint arXiv:2510.24284v2},
  year={2025}
}
```

## 🤝 贡献

欢迎提交Issue和Pull Request!

## 📄 许可证

本项目遵循MIT许可证。

## 🔗 相关链接

- 📄 [原始论文](https://arxiv.org/abs/2510.24284v2)
- 💻 [官方仓库](https://github.com/wwh0411/MCP-Flow)
- 📖 [MCP协议文档](https://www.anthropic.com/news/model-context-protocol)
