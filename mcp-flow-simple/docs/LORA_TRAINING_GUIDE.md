# LoRA微调使用指南

## 📋 概述

本方案采用 **LoRA (Low-Rank Adaptation)** 进行参数高效微调,完全遵循论文配置标准。

### 核心配置 (论文 Table 12)

| 参数 | 值 | 说明 |
|------|-----|------|
| LoRA Rank | 64 | 低秩分解的秩 |
| LoRA Alpha | 128 | 缩放因子 (通常为rank的2倍) |
| Dropout | 0.1 | 防止过拟合 |
| Learning Rate | 2e-4 | 学习率 |
| Batch Size | 128 | 总批大小 (16*8) |
| Optimizer | AdamW | Adam优化器with权重衰减 |
| Epochs | 1 | 训练轮数 (防止过拟合) |
| DeepSpeed | ZeRO-0 | 降低显存占用 |

### 优势

- ✅ **显存高效**: 只训练LoRA参数 (~0.1%模型参数)
- ✅ **快速训练**: 训练速度比全量微调快3-5倍
- ✅ **易于部署**: LoRA权重文件小 (<100MB)
- ✅ **可插拔**: 可随时切换或合并LoRA权重

---

## 🚀 快速开始

### 1. 环境准备

#### 安装依赖

```bash
# 进入项目目录
cd mcp-flow-simple

# 安装基础依赖
pip install -r requirements.txt

# 安装LLaMA-Factory
pip install llmtuner

# 安装DeepSpeed (可选,用于加速)
pip install deepspeed
```

#### 硬件要求

| 模型大小 | 推荐显存 | 最低显存 |
|---------|---------|---------|
| 7B | 24GB | 16GB |
| 14B | 40GB | 32GB |
| 70B | 80GB (多卡) | 80GB |

**注意**: 使用LoRA可大幅降低显存需求 (相比全量微调)

---

### 2. 数据准备

#### 方式1: 使用现有数据

如果您已经运行过数据生成:

```bash
# 查看已生成的数据
ls -lh ../data/filtered/

# 训练脚本会自动使用最新的数据文件
```

#### 方式2: 重新生成数据

```bash
# 使用完整工具列表生成更多数据
python src/main.py \
    --tools mcp_tools_full_20251113_120436.json \
    --config config/config.yaml

# 等待生成完成,会在 ../data/filtered/ 生成数据
```

---

### 3. 配置模型路径

有三种方式指定模型:

#### 方式1: 环境变量 (推荐)

```bash
# Linux/Mac
export MODEL_PATH="/path/to/your/model"

# Windows (PowerShell)
$env:MODEL_PATH="D:\Models\Qwen2.5-7B-Instruct"

# Windows (CMD)
set MODEL_PATH=D:\Models\Qwen2.5-7B-Instruct
```

#### 方式2: 修改配置文件

编辑 `train_configs/lora_config.yaml`:

```yaml
model_name_or_path: /path/to/your/model  # 修改这行
```

#### 方式3: 使用HuggingFace模型ID

```yaml
model_name_or_path: Qwen/Qwen2.5-7B-Instruct  # 自动下载
```

---

### 4. 启动训练

#### Windows系统

```bash
python train_lora.py
```

#### Linux/Mac系统

```bash
chmod +x train_lora.sh
./train_lora.sh
```

#### 使用多GPU训练

```bash
# 自动使用所有可用GPU
CUDA_VISIBLE_DEVICES=0,1,2,3 python train_lora.py

# 或者使用DeepSpeed启动
deepspeed --num_gpus=4 train_lora.py
```

---

## 📊 训练监控

### 查看训练日志

训练过程中会实时输出:
- Loss曲线
- 学习率变化
- 评估指标
- 保存检查点信息

### 训练输出目录结构

```
outputs/mcp_lora/
├── checkpoint-100/          # 检查点100
├── checkpoint-200/          # 检查点200
├── checkpoint-300/          # 检查点300 (最终)
├── training_loss.png        # Loss曲线图
├── training_args.bin        # 训练参数
└── trainer_state.json       # 训练状态
```

---

## 🔧 高级配置

### 调整批大小 (根据显存)

编辑 `train_configs/lora_config.yaml`:

```yaml
# 如果显存不足,减小批大小
per_device_train_batch_size: 8   # 从16改为8
gradient_accumulation_steps: 16  # 从8改为16 (保持总batch=128)

# 如果显存充足,可增大批大小
per_device_train_batch_size: 32  # 从16改为32
gradient_accumulation_steps: 4   # 从8改为4
```

### 调整序列长度

```yaml
# 如果您的数据较短,可以减小以提高速度
cutoff_len: 2048  # 从4096改为2048
```

### 调整LoRA参数

```yaml
# 增加LoRA容量 (提高性能,增加显存)
lora_rank: 128
lora_alpha: 256

# 减小LoRA容量 (降低显存,可能影响性能)
lora_rank: 32
lora_alpha: 64
```

---

## 💾 使用训练后的模型

### 方式1: 使用LLaMA-Factory推理

```bash
llamafactory-cli chat \
    --model_name_or_path /path/to/base/model \
    --adapter_name_or_path outputs/mcp_lora/checkpoint-300 \
    --template qwen
```

### 方式2: 合并LoRA权重

```bash
llamafactory-cli export \
    --model_name_or_path /path/to/base/model \
    --adapter_name_or_path outputs/mcp_lora/checkpoint-300 \
    --export_dir outputs/merged_model \
    --export_size 1 \
    --export_legacy_format false
```

### 方式3: Python代码加载

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# 加载基础模型
base_model = AutoModelForCausalLM.from_pretrained(
    "/path/to/base/model",
    torch_dtype="auto",
    device_map="auto"
)

# 加载LoRA权重
model = PeftModel.from_pretrained(
    base_model,
    "outputs/mcp_lora/checkpoint-300"
)

# 加载tokenizer
tokenizer = AutoTokenizer.from_pretrained("/path/to/base/model")

# 推理
messages = [
    {"role": "user", "content": "查询所有部门列表"}
]
text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True
)
model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
generated_ids = model.generate(**model_inputs, max_new_tokens=512)
response = tokenizer.batch_decode(generated_ids)[0]
print(response)
```

---

## ❓ 常见问题

### Q1: 显存不足 (OOM)

**解决方案:**
1. 减小 `per_device_train_batch_size`
2. 增大 `gradient_accumulation_steps` (保持总batch不变)
3. 减小 `cutoff_len`
4. 使用更小的 `lora_rank`

### Q2: 训练速度慢

**解决方案:**
1. 检查是否使用了GPU: `nvidia-smi`
2. 启用DeepSpeed: 确保 `ds_z0_config.json` 配置正确
3. 使用多GPU训练
4. 减小 `cutoff_len` 或数据量

### Q3: Loss不下降

**解决方案:**
1. 检查数据质量和格式
2. 调整学习率: 尝试 `1e-4` 或 `5e-5`
3. 增加训练轮数: 改为 `num_train_epochs: 2.0`
4. 检查数据是否足够 (建议>100条)

### Q4: 模型输出格式不正确

**解决方案:**
1. 检查 `template` 参数是否匹配模型
2. 查看训练数据转换是否正确
3. 尝试增加训练数据量
4. 调整 `lora_rank` 增加模型容量

---

## 📚 参考资料

- **论文**: [原始论文链接]
- **LLaMA-Factory**: https://github.com/hiyouga/LLaMA-Factory
- **LoRA论文**: Hu et al., 2022 - "LoRA: Low-Rank Adaptation of Large Language Models"
- **DeepSpeed**: https://www.deepspeed.ai/

---

## 📞 支持

如有问题,请:
1. 查看训练日志: `outputs/mcp_lora/`
2. 检查数据格式: `data/llama_factory/mcp_train_data.json`
3. 提交Issue到项目仓库

---

**祝训练顺利! 🎉**
