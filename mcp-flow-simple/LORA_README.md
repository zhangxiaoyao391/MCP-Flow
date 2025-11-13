# LoRA微调方案 - 快速参考

## 📁 项目结构

```
mcp-flow-simple/
├── scripts/
│   └── convert_to_llama_factory.py    # 数据格式转换脚本
├── train_configs/
│   ├── lora_config.yaml               # LoRA训练配置
│   ├── ds_z0_config.json              # DeepSpeed ZeRO-0配置
│   └── dataset_info.json              # 数据集配置
├── data/
│   └── llama_factory/                 # 转换后的训练数据
├── outputs/
│   └── mcp_lora/                      # 训练输出目录
├── train_lora.py                      # Python训练脚本 (Windows)
├── train_lora.sh                      # Bash训练脚本 (Linux/Mac)
├── requirements_lora.txt              # LoRA训练依赖
└── LORA_TRAINING_GUIDE.md            # 完整使用指南
```

## 🚀 快速开始 (3步)

### 1. 安装依赖
```bash
pip install -r requirements_lora.txt
```

### 2. 设置模型路径
```bash
# Windows PowerShell
$env:MODEL_PATH="D:\Models\Qwen2.5-7B-Instruct"

# Linux/Mac
export MODEL_PATH="/path/to/model"
```

### 3. 启动训练
```bash
# Windows
python train_lora.py

# Linux/Mac
./train_lora.sh
```

## 📊 训练配置 (论文标准)

| 参数 | 值 |
|------|-----|
| LoRA Rank | 64 |
| LoRA Alpha | 128 |
| Learning Rate | 2e-4 |
| Batch Size | 128 |
| Epochs | 1 |
| Optimizer | AdamW |
| DeepSpeed | ZeRO-0 |

## 💡 显存需求

| 模型 | 全量微调 | LoRA微调 | 节省 |
|------|---------|---------|------|
| 7B | ~40GB | ~16GB | 60% |
| 14B | ~80GB | ~32GB | 60% |

## 📖 详细文档

请查看完整指南: [LORA_TRAINING_GUIDE.md](LORA_TRAINING_GUIDE.md)
