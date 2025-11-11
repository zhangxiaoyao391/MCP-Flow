"""
MCP-Flow Main Pipeline
整合所有模块的完整数据构建和训练流程
"""
import logging
import yaml
import argparse
from pathlib import Path
import json

# 导入各模块
from server_collector.collector import MCPServerCollector
from server_collector.mcp_client import MCPClient
from data_generator.generator import DataGenerator
from data_filter.filter import DataFilter
from model_trainer.trainer import MCPFlowTrainer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MCPFlowPipeline:
    """MCP-Flow完整pipeline"""

    def __init__(self, config_path: str):
        """初始化pipeline"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.output_dir = Path(".")

    def run_server_collection(self):
        """
        步骤1: 服务器收集

        论文Section 3.1和Algorithm 1
        """
        logger.info("=" * 50)
        logger.info("步骤1: 服务器收集")
        logger.info("=" * 50)

        # 初始化收集器
        collector = MCPServerCollector(self.config)

        # 从marketplaces收集服务器
        logger.info("正在从marketplaces收集服务器...")
        servers = collector.collect_from_marketplaces()

        # 服务器去重
        logger.info("正在进行服务器去重...")
        deduplicated = collector.deduplicate_servers()

        # 保存服务器配置
        collector.save_servers(self.config['output_paths']['servers'])

        logger.info(f"服务器收集完成,共收集 {len(deduplicated)} 个唯一服务器")
        return deduplicated

    def run_tool_extraction(self, servers: dict):
        """
        步骤2: 工具提取

        论文Section 3.1 - 本地部署和工具收集
        """
        logger.info("=" * 50)
        logger.info("步骤2: 工具提取")
        logger.info("=" * 50)

        client = MCPClient()
        all_tools = {}

        for server_id, server_config in servers.items():
            logger.info(f"正在部署服务器: {server_config.get('name', server_id)}")
            tools = client.deploy_server(server_config)

            if tools:
                all_tools[server_id] = {
                    'server_config': server_config,
                    'tools': tools
                }

        # 保存工具信息
        client.save_tools(self.config['output_paths']['tools'])

        logger.info(f"工具提取完成,共提取 {sum(len(t['tools']) for t in all_tools.values())} 个工具")
        return all_tools

    def run_data_generation(self, tools_data: dict):
        """
        步骤3: 数据生成

        论文Section 3.2 - Few-shot + Slot-fill + Evolution + Function Call
        """
        logger.info("=" * 50)
        logger.info("步骤3: 数据生成")
        logger.info("=" * 50)

        generator = DataGenerator(self.config)  # 不需要传api_key了

        all_samples = []

        for server_id, server_data in tools_data.items():
            server_info = server_data['server_config']
            tools = server_data['tools']

            for tool in tools:
                logger.info(f"正在为工具 {tool.get('name')} 生成数据...")

                # 1. Few-shot生成指令
                instructions = generator.generate_instructions(tool, server_info)

                for instruction in instructions:
                    # 2. Slot-fill修订
                    revised_instruction = generator.slot_fill_revision(instruction, tool)

                    # 3. WizardLM Evolution
                    evolved_instruction = generator.wizardlm_evolution(
                        revised_instruction,
                        depth=self.config['data_generation'].get('evolution_depth', 2)
                    )

                    # 4. 生成函数调用
                    function_call = generator.generate_function_call(
                        evolved_instruction,
                        tool,
                        server_info
                    )

                    if function_call:
                        sample = {
                            'server_id': server_id,
                            'server_name': server_info.get('name', ''),
                            'tool_name': tool.get('name', ''),
                            'tool_description': tool.get('description', ''),
                            'instruction': evolved_instruction,
                            'function_call': function_call,
                            'original_instruction': instruction,
                            'revised_instruction': revised_instruction
                        }
                        all_samples.append(sample)

        # 保存生成的数据
        output_file = Path(self.config['output_paths']['instructions']) / "generated_data.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_samples, f, ensure_ascii=False, indent=2)

        logger.info(f"数据生成完成,共生成 {len(all_samples)} 个样本")
        return all_samples

    def run_data_filtering(self, samples: list):
        """
        步骤4: 数据过滤

        论文Section 3.3 - 严格的多维度过滤
        """
        logger.info("=" * 50)
        logger.info("步骤4: 数据过滤")
        logger.info("=" * 50)

        filter_module = DataFilter(self.config)  # 不需要传api_keys了

        # 1. 嵌入相似度过滤
        logger.info("执行嵌入相似度过滤...")
        filtered_samples = filter_module.filter_by_embedding_similarity(samples)

        # 2. 工具调用验证过滤（可配置跳过）
        logger.info("执行工具调用验证过滤...")
        filtered_samples = filter_module.filter_by_tool_invocation(filtered_samples)

        # 3. 质量评分过滤
        logger.info("执行质量评分过滤...")
        filtered_samples = filter_module.filter_by_quality_score(filtered_samples)

        # 保存过滤后的数据
        output_file = Path(self.config['output_paths']['filtered_data']) / "filtered_data.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(filtered_samples, f, ensure_ascii=False, indent=2)

        logger.info(f"数据过滤完成: {len(samples)} → {len(filtered_samples)} 个样本")
        return filtered_samples

    def run_model_training(self, filtered_data_path: str):
        """
        步骤5: 模型训练

        论文Section 4.1-4.2 - LoRA微调
        """
        logger.info("=" * 50)
        logger.info("步骤5: 模型训练")
        logger.info("=" * 50)

        trainer = MCPFlowTrainer(self.config)

        # 准备数据集
        train_dataset = trainer.prepare_dataset(filtered_data_path)

        # 对每个backbone模型进行训练
        for model_name in self.config['training']['backbone_models']:
            logger.info(f"正在训练模型: {model_name}")

            output_dir = Path(self.config['output_paths']['models']) / f"mcp-flow-{model_name.split('/')[-1]}"
            trainer.train(train_dataset, str(output_dir), model_name)

        logger.info("所有模型训练完成!")

    def run_full_pipeline(self):
        """运行完整pipeline"""
        logger.info("开始运行MCP-Flow完整pipeline")
        logger.info("=" * 50)

        # 步骤1: 服务器收集
        servers = self.run_server_collection()

        # 步骤2: 工具提取
        tools_data = self.run_tool_extraction(servers)

        # 步骤3: 数据生成
        samples = self.run_data_generation(tools_data)

        # 步骤4: 数据过滤
        filtered_samples = self.run_data_filtering(samples)

        # 步骤5: 模型训练
        filtered_data_path = Path(self.config['output_paths']['filtered_data']) / "filtered_data.json"
        self.run_model_training(str(filtered_data_path))

        logger.info("=" * 50)
        logger.info("MCP-Flow pipeline运行完成!")
        logger.info("=" * 50)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='MCP-Flow数据构建和模型训练pipeline')
    parser.add_argument('--config', type=str, default='config.yaml', help='配置文件路径')
    parser.add_argument('--step', type=str, choices=['collect', 'extract', 'generate', 'filter', 'train', 'all'],
                        default='all', help='要运行的步骤')

    args = parser.parse_args()

    # 初始化pipeline
    pipeline = MCPFlowPipeline(args.config)

    # 根据参数运行指定步骤
    if args.step == 'all':
        pipeline.run_full_pipeline()
    elif args.step == 'collect':
        pipeline.run_server_collection()
    elif args.step == 'extract':
        # 需要先加载已收集的服务器
        with open(Path(pipeline.config['output_paths']['servers']) / "collected_servers.json", 'r', encoding='utf-8') as f:
            servers = json.load(f)
        pipeline.run_tool_extraction(servers)
    elif args.step == 'generate':
        # 需要先加载已提取的工具
        with open(Path(pipeline.config['output_paths']['tools']) / "extracted_tools.json", 'r', encoding='utf-8') as f:
            tools_data = json.load(f)
        pipeline.run_data_generation(tools_data)
    elif args.step == 'filter':
        # 需要先加载已生成的数据
        with open(Path(pipeline.config['output_paths']['instructions']) / "generated_data.json", 'r', encoding='utf-8') as f:
            samples = json.load(f)
        pipeline.run_data_filtering(samples)
    elif args.step == 'train':
        filtered_data_path = Path(pipeline.config['output_paths']['filtered_data']) / "filtered_data.json"
        pipeline.run_model_training(str(filtered_data_path))


if __name__ == "__main__":
    main()
