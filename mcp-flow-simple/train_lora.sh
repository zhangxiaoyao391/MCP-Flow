#!/bin/bash
# LoRA微调训练脚本
# 完全遵循论文配置: LoRA + DeepSpeed ZeRO-0

set -e

echo "=========================================="
echo "MCP Function Calling LoRA微调训练"
echo "=========================================="

# 配置参数
MODEL_PATH="${MODEL_PATH:-Qwen/Qwen2.5-7B-Instruct}"  # 可通过环境变量自定义
DATA_DIR="./data/llama_factory"
CONFIG_DIR="./train_configs"
OUTPUT_DIR="./outputs/mcp_lora"

# 检查LLaMA-Factory是否安装
if ! command -v llamafactory-cli &> /dev/null; then
    echo "❌ 错误: LLaMA-Factory未安装"
    echo "请运行: pip install llmtuner"
    exit 1
fi

echo "✓ LLaMA-Factory已安装"

# 步骤1: 转换数据格式
echo ""
echo "步骤1: 转换数据格式"
echo "----------------------------------------"

FILTERED_DATA="../data/filtered/filtered_*.json"
LATEST_FILTERED=$(ls -t $FILTERED_DATA 2>/dev/null | head -1)

if [ -z "$LATEST_FILTERED" ]; then
    echo "❌ 错误: 未找到过滤后的数据文件"
    echo "请先运行数据生成: python src/main.py --tools mcp_tools_test.json"
    exit 1
fi

echo "找到数据文件: $LATEST_FILTERED"

mkdir -p "$DATA_DIR"
python scripts/convert_to_llama_factory.py \
    --input "$LATEST_FILTERED" \
    --output "$DATA_DIR/mcp_train_data.json" \
    --verbose

if [ $? -ne 0 ]; then
    echo "❌ 数据转换失败"
    exit 1
fi

echo "✓ 数据转换完成"

# 步骤2: 启动训练
echo ""
echo "步骤2: 启动LoRA训练"
echo "----------------------------------------"
echo "模型: $MODEL_PATH"
echo "训练配置: 论文Table 12标准配置"
echo "  - LoRA Rank: 64"
echo "  - LoRA Alpha: 128"
echo "  - Learning Rate: 2e-4"
echo "  - Batch Size: 128 (16*8)"
echo "  - Epochs: 1"
echo "  - Optimizer: AdamW"
echo "  - DeepSpeed: ZeRO-0"
echo "----------------------------------------"

# 启动训练
llamafactory-cli train \
    --model_name_or_path "$MODEL_PATH" \
    --stage sft \
    --do_train true \
    --finetuning_type lora \
    --lora_rank 64 \
    --lora_alpha 128 \
    --lora_dropout 0.1 \
    --lora_target all \
    --dataset mcp_function_calling \
    --dataset_dir "$DATA_DIR" \
    --template qwen \
    --cutoff_len 4096 \
    --per_device_train_batch_size 16 \
    --gradient_accumulation_steps 8 \
    --learning_rate 2e-4 \
    --num_train_epochs 1.0 \
    --lr_scheduler_type cosine \
    --warmup_ratio 0.1 \
    --optim adamw_torch \
    --deepspeed "$CONFIG_DIR/ds_z0_config.json" \
    --output_dir "$OUTPUT_DIR" \
    --logging_steps 10 \
    --save_steps 100 \
    --save_total_limit 3 \
    --bf16 true \
    --val_size 0.1 \
    --evaluation_strategy steps \
    --eval_steps 50 \
    --overwrite_output_dir true \
    --plot_loss true

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✓ 训练完成!"
    echo "输出目录: $OUTPUT_DIR"
    echo "=========================================="
else
    echo ""
    echo "❌ 训练失败"
    exit 1
fi
