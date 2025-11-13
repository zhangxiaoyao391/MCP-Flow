"""
LoRA微调训练脚本 (Python版本)
完全遵循论文配置: LoRA + DeepSpeed ZeRO-0
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from glob import glob


def check_llamafactory():
    """检查LLaMA-Factory是否安装"""
    try:
        subprocess.run(['llamafactory-cli', '--version'],
                      capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def convert_data():
    """转换数据格式"""
    print("\n步骤1: 转换数据格式")
    print("-" * 40)

    # 查找最新的过滤数据文件
    filtered_files = glob("../data/filtered/filtered_*.json")
    if not filtered_files:
        print("❌ 错误: 未找到过滤后的数据文件")
        print("请先运行数据生成: python src/main.py --tools mcp_tools_test.json")
        return False

    latest_file = max(filtered_files, key=os.path.getmtime)
    print(f"找到数据文件: {latest_file}")

    # 创建输出目录
    data_dir = Path("./data/llama_factory")
    data_dir.mkdir(parents=True, exist_ok=True)

    output_file = data_dir / "mcp_train_data.json"

    # 运行转换脚本
    cmd = [
        sys.executable,
        "scripts/convert_to_llama_factory.py",
        "--input", latest_file,
        "--output", str(output_file),
        "--verbose"
    ]

    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("❌ 数据转换失败")
        return False

    print("✓ 数据转换完成")
    return True


def start_training():
    """启动LoRA训练"""
    print("\n步骤2: 启动LoRA训练")
    print("-" * 40)

    model_path = os.environ.get('MODEL_PATH', 'Qwen/Qwen2.5-7B-Instruct')
    data_dir = "./data/llama_factory"
    config_dir = "./train_configs"
    output_dir = "./outputs/mcp_lora"

    print(f"模型: {model_path}")
    print("训练配置: 论文Table 12标准配置")
    print("  - LoRA Rank: 64")
    print("  - LoRA Alpha: 128")
    print("  - Learning Rate: 2e-4")
    print("  - Batch Size: 128 (16*8)")
    print("  - Epochs: 1")
    print("  - Optimizer: AdamW")
    print("  - DeepSpeed: ZeRO-0")
    print("-" * 40)

    # 构建训练命令
    cmd = [
        'llamafactory-cli', 'train',
        '--model_name_or_path', model_path,
        '--stage', 'sft',
        '--do_train', 'true',
        '--finetuning_type', 'lora',
        '--lora_rank', '64',
        '--lora_alpha', '128',
        '--lora_dropout', '0.1',
        '--lora_target', 'all',
        '--dataset', 'mcp_function_calling',
        '--dataset_dir', data_dir,
        '--template', 'qwen',
        '--cutoff_len', '4096',
        '--per_device_train_batch_size', '16',
        '--gradient_accumulation_steps', '8',
        '--learning_rate', '2e-4',
        '--num_train_epochs', '1.0',
        '--lr_scheduler_type', 'cosine',
        '--warmup_ratio', '0.1',
        '--optim', 'adamw_torch',
        '--deepspeed', f'{config_dir}/ds_z0_config.json',
        '--output_dir', output_dir,
        '--logging_steps', '10',
        '--save_steps', '100',
        '--save_total_limit', '3',
        '--bf16', 'true',
        '--val_size', '0.1',
        '--evaluation_strategy', 'steps',
        '--eval_steps', '50',
        '--overwrite_output_dir', 'true',
        '--plot_loss', 'true'
    ]

    # 启动训练
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("\n" + "=" * 40)
        print("✓ 训练完成!")
        print(f"输出目录: {output_dir}")
        print("=" * 40)
        return True
    else:
        print("\n❌ 训练失败")
        return False


def main():
    print("=" * 40)
    print("MCP Function Calling LoRA微调训练")
    print("=" * 40)

    # 检查LLaMA-Factory
    if not check_llamafactory():
        print("❌ 错误: LLaMA-Factory未安装")
        print("请运行: pip install llmtuner")
        sys.exit(1)

    print("✓ LLaMA-Factory已安装")

    # 转换数据
    if not convert_data():
        sys.exit(1)

    # 启动训练
    if not start_training():
        sys.exit(1)


if __name__ == '__main__':
    main()
