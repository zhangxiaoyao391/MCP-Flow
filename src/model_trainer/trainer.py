"""
Model Training Module using LoRA Fine-tuning
基于论文Section 4.1-4.2实现模型训练流程
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer
)
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset

logger = logging.getLogger(__name__)


class MCPFlowTrainer:
    """MCP-Flow模型训练器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.training_config = config.get('training', {})
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    def prepare_dataset(self, data_path: str) -> Dataset:
        """
        准备训练数据集

        论文Section 4.1: "将训练工具大小设置为10,
        并从seen tool池中随机采样候选工具,
        为每个instruction-function call对形成训练集"

        Args:
            data_path: 数据文件路径

        Returns:
            Dataset: HuggingFace Dataset对象
        """
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 转换为训练格式
        formatted_data = []
        for sample in data:
            formatted_sample = self._format_sample(sample)
            if formatted_sample:
                formatted_data.append(formatted_sample)

        dataset = Dataset.from_list(formatted_data)
        logger.info(f"准备了 {len(dataset)} 条训练样本")

        return dataset

    def _format_sample(self, sample: Dict) -> Dict:
        """
        格式化单个样本为训练格式

        格式: 系统提示 + 用户指令 + 候选工具列表 → 函数调用
        """
        instruction = sample.get('instruction', '')
        candidate_tools = sample.get('candidate_tools', [])
        function_call = sample.get('function_call', {})

        # 构建输入文本
        input_text = f"""Given the following instruction and available tools, generate the appropriate function call.

Instruction: {instruction}

Available Tools:
{json.dumps(candidate_tools, indent=2)}

Generate the function call:"""

        # 构建输出文本
        output_text = json.dumps(function_call, indent=2)

        return {
            'input': input_text,
            'output': output_text
        }

    def train(self, train_dataset: Dataset, output_dir: str, model_name: str):
        """
        训练模型

        论文Section 4.1: "采用LoRA微调,LoRA rank=16, alpha=32"

        Args:
            train_dataset: 训练数据集
            output_dir: 输出目录
            model_name: 基础模型名称
        """
        logger.info(f"开始训练模型: {model_name}")

        # 加载tokenizer和模型
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            trust_remote_code=True,
            device_map="auto",
            torch_dtype=torch.bfloat16
        )

        # 配置LoRA
        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=self.training_config.get('lora_rank', 16),
            lora_alpha=self.training_config.get('lora_alpha', 32),
            lora_dropout=0.1,
            bias="none",
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]
        )

        model = get_peft_model(model, lora_config)
        model.print_trainable_parameters()

        # 定义训练参数
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=self.training_config.get('epochs', 1),
            per_device_train_batch_size=self.training_config.get('batch_size', 2),
            gradient_accumulation_steps=self.training_config.get('gradient_accumulation_steps', 8),
            learning_rate=self.training_config.get('learning_rate', 5e-5),
            lr_scheduler_type="cosine",
            warmup_ratio=0.1,
            logging_steps=10,
            save_strategy="epoch",
            bf16=True,
            gradient_checkpointing=True,
            deepspeed=None,  # 可选: 使用DeepSpeed加速
            report_to="none"
        )

        # 数据处理函数
        def preprocess_function(examples):
            inputs = examples['input']
            outputs = examples['output']

            # Tokenize
            model_inputs = tokenizer(
                inputs,
                max_length=self.training_config.get('max_length', 8192),
                truncation=True,
                padding='max_length'
            )

            labels = tokenizer(
                outputs,
                max_length=self.training_config.get('max_length', 8192),
                truncation=True,
                padding='max_length'
            )

            model_inputs["labels"] = labels["input_ids"]
            return model_inputs

        # 处理数据集
        tokenized_dataset = train_dataset.map(
            preprocess_function,
            batched=True,
            remove_columns=train_dataset.column_names
        )

        # 初始化Trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized_dataset,
            tokenizer=tokenizer
        )

        # 开始训练
        trainer.train()

        # 保存模型
        trainer.save_model(output_dir)
        logger.info(f"模型已保存到: {output_dir}")


if __name__ == "__main__":
    # 测试代码
    import yaml

    logging.basicConfig(level=logging.INFO)

    with open("config.yaml", 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    trainer = MCPFlowTrainer(config)

    # 准备数据
    # train_dataset = trainer.prepare_dataset("data/filtered/train_data.json")

    # 训练模型
    # for model_name in config['training']['backbone_models']:
    #     output_dir = f"models/mcp-flow-{model_name.split('/')[-1]}"
    #     trainer.train(train_dataset, output_dir, model_name)
