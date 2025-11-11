# MCP-Flow 实现

> 基于论文《MCP-FLOW: FACILITATING LLM AGENTS TO MASTER REAL-WORLD, DIVERSE AND SCALING MCP TOOLS》的完整实现

## 🎯 项目简介

MCP-Flow是一个**自动化数据构建pipeline**,用于训练LLM掌握真实世界的MCP工具使用能力。

**核心功能**:
- 🔍 自动从6个marketplace收集1166+个MCP服务器
- 📊 生成60k+高质量instruction-function call数据对
- 🎓 训练小型模型(0.6B-8B)达到超越GPT-4o的MCP工具使用能力
- ✅ 严格的四重过滤机制保证数据质量

## 📦 数据规模

| 指标 | 数量 |
|------|------|
| MCP服务器 | 1,166 |
| 工具数量 | 11,536 |
| 训练样本 | 68,733 |
| 轨迹数据 | 6,439 |

## 🚀 快速开始

### 1. 克隆并配置

```bash
# 1. 进入项目目录
cd MCP-Flow

# 2. 配置API密钥
# 编辑 config.yaml,填入你的 OpenAI 和 DeepSeek API密钥
```

### 2. 一键安装

**Linux/Mac:**
```bash
chmod +x setup.sh
./setup.sh
```

**Windows:**
```cmd
setup.bat
```

### 3. 运行Pipeline

```bash
# 运行完整pipeline (服务器收集 → 工具提取 → 数据生成 → 过滤 → 训练)
python src/main.py --step all

# 或分步运行:
python src/main.py --step collect   # 1. 服务器收集
python src/main.py --step extract   # 2. 工具提取
python src/main.py --step generate  # 3. 数据生成
python src/main.py --step filter    # 4. 数据过滤
python src/main.py --step train     # 5. 模型训练
```

## 📊 核心流程

```
1️⃣ 服务器收集 (Web Agent)
   ↓
2️⃣ 工具提取 (本地部署MCP Client)
   ↓
3️⃣ 数据生成 (Few-shot → Slot-fill → Evolution → Function Call)
   ↓
4️⃣ 数据过滤 (嵌入相似度 → 工具验证 → 质量评分 → Trajectory验证)
   ↓
5️⃣ 模型训练 (LoRA微调 Qwen3/Llama3)
```

## 📈 实验结果

**在10个候选工具的测试中:**

| 模型 | Tool准确率↑ | AST准确率↑ |
|------|-----------|----------|
| **MCP-Flow (Qwen3-4B)** | **99.2%** | **81.2%** |
| **MCP-Flow (Qwen3-0.6B)** | **96.8%** | **75.4%** |
| GPT-4o | 88.6% | 58.8% |
| Claude-4-Sonnet | 85.8% | 56.6% |

✅ **0.6B模型即可超越GPT-4o!**

## 🏗️ 项目结构

```
MCP-Flow/
├── config.yaml              # 主配置文件
├── src/
│   ├── main.py             # 主流程
│   ├── server_collector/   # 服务器收集
│   ├── data_generator/     # 数据生成
│   ├── data_filter/        # 数据过滤
│   └── model_trainer/      # 模型训练
├── data/                   # 数据目录
└── models/                 # 训练模型
```

## 🔑 配置说明

在 `config.yaml` 中配置:

```yaml
# API密钥
api_keys:
  openai_api_key: "sk-xxx"
  deepseek_api_key: "sk-xxx"

# 数据生成参数
data_generation:
  instruction_per_tool: 5    # 每工具生成5条指令
  evolution_depth: 2         # WizardLM evolution深度

# 过滤参数
data_filtering:
  similarity_threshold: 0.8  # 嵌入相似度阈值
  quality_score_threshold: 6 # 质量评分阈值

# 训练参数
training:
  backbone_models:
    - "Qwen/Qwen3-0.6B"
    - "Qwen/Qwen3-4B"
  lora_rank: 16
  learning_rate: 5e-5
```

## 📚 文档

- 📖 [完整实现指南](IMPLEMENTATION_GUIDE.md)
- 📄 [原始论文](https://arxiv.org/abs/2510.24284v2)
- 💻 [官方仓库](https://github.com/wwh0411/MCP-Flow)

## 💡 核心特性

### 1. **自动化服务器收集**
- ✅ 使用Playwright Web Agent自动爬取
- ✅ 支持6个主流marketplace
- ✅ 基于工具描述的智能去重

### 2. **高质量数据生成**
- ✅ Few-shot生成多样化指令
- ✅ Slot-fill自动补全参数
- ✅ WizardLM Evolution增加复杂度
- ✅ GPT-4o生成函数调用

### 3. **严格质量控制**
- ✅ 嵌入相似度过滤(阈值0.8)
- ✅ GPT-4o + DeepSeek-V3双重验证
- ✅ DeepSeek-V3质量评分(≥6/10)
- ✅ Trajectory有效性检查

### 4. **高效模型训练**
- ✅ LoRA微调(Rank=16, Alpha=32)
- ✅ 支持多种backbone模型
- ✅ 内存高效(支持0.6B-8B模型)

## 🔧 高级用法

### 自定义Marketplace

在 `config.yaml` 添加:

```yaml
marketplaces:
  - name: "custom_marketplace"
    url: "https://example.com"
    type: "playwright"
```

### 调整数据质量

```yaml
data_filtering:
  similarity_threshold: 0.9  # 更严格的相似度要求
  quality_score_threshold: 7 # 更高的质量要求
```

### 使用自定义模型

```yaml
training:
  backbone_models:
    - "your-org/your-model"
```

## 🐛 常见问题

**Q: Playwright安装失败?**
```bash
python -m playwright install chromium
```

**Q: CUDA内存不足?**
- 减小 `batch_size`
- 使用 `gradient_checkpointing`

**Q: API调用失败?**
- 检查API密钥是否正确
- 检查网络连接

## 📜 引用

```bibtex
@article{wang2025mcpflow,
  title={MCP-FLOW: FACILITATING LLM AGENTS TO MASTER REAL-WORLD, DIVERSE AND SCALING MCP TOOLS},
  author={Wang, Wenhao and Niu, Peizhi and Xu, Zhao and Chen, Zhaoyu and Du, Jian and others},
  journal={arXiv preprint arXiv:2510.24284v2},
  year={2025}
}
```

## 📄 许可证

MIT License

## 🌟 Star History

如果觉得有用,请给个⭐️!

---

**开发状态**: 🚧 持续开发中

**最后更新**: 2025-11-11
