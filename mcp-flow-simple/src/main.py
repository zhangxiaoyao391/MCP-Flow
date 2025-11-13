"""MCP-Flow简化版主入口"""
import logging
import yaml
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from data_generator.generator import DataGenerator
from data_filter.filter import DataFilter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MCPFlowPipeline:
    def __init__(self, config_path: str):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        logger.info("Pipeline初始化完成")

    def load_tools(self, json_path: str) -> Dict:
        logger.info(f"加载工具数据: {json_path}")
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"服务器: {data['server_info']['name']}, 工具数: {len(data['tools'])}")
        return data

    def generate_data(self, tools_data: Dict) -> List[Dict]:
        logger.info("=" * 60)
        logger.info("阶段1: 数据生成")
        logger.info("=" * 60)
        generator = DataGenerator(self.config)
        server_info = tools_data['server_info']
        tools = tools_data['tools']
        samples = []
        for idx, tool in enumerate(tools, 1):
            logger.info(f"[{idx}/{len(tools)}] 处理: {tool.get('name')}")
            try:
                instructions = generator.generate_instructions(tool, server_info)
                logger.info(f"  生成{len(instructions)}条指令")
                for inst in instructions:
                    revised = generator.slot_fill_revision(inst, tool)
                    evolved = generator.wizardlm_evolution(revised, self.config['data_generation'].get('evolution_depth', 1))
                    sample = generator.generate_function_call(evolved, tool, server_info)
                    if sample:
                        samples.append(sample)
            except Exception as e:
                logger.error(f"  处理失败: {e}")
        output_dir = Path(self.config['output_paths']['function_calls'])
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(samples, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ 生成完成: {len(samples)}个样本, 保存至 {output_file}")
        return samples

    def filter_data(self, samples: List[Dict]) -> List[Dict]:
        logger.info("=" * 60)
        logger.info("阶段2: 数据过滤")
        logger.info("=" * 60)
        filter_module = DataFilter(self.config)
        initial = len(samples)
        samples = filter_module.filter_by_tool_invocation(samples)
        logger.info(f"工具验证: {len(samples)}/{initial}")
        samples = filter_module.filter_by_quality_score(samples)
        logger.info(f"质量评分: {len(samples)}/{initial}")
        samples = filter_module.filter_trajectory(samples)
        logger.info(f"轨迹验证: {len(samples)}/{initial}")
        output_dir = Path(self.config['output_paths']['filtered_data'])
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(samples, f, ensure_ascii=False, indent=2)
        percent = (len(samples)/initial*100) if initial > 0 else 0
        logger.info(f"✓ 过滤完成: {len(samples)}个样本({percent:.1f}%), 保存至 {output_file}")
        return samples

    def run(self, tools_json: str):
        start = datetime.now()
        logger.info("=" * 60)
        logger.info("MCP-Flow 简化版 Pipeline")
        logger.info("=" * 60)
        tools_data = self.load_tools(tools_json)
        samples = self.generate_data(tools_data)
        filtered = self.filter_data(samples)
        duration = datetime.now() - start
        logger.info("=" * 60)
        logger.info(f"✓ 完成! 耗时: {duration}")
        logger.info(f"✓ 工具: {len(tools_data['tools'])}, 生成: {len(samples)}, 通过: {len(filtered)}")
        logger.info("=" * 60)

def main():
    parser = argparse.ArgumentParser(description='MCP-Flow简化版')
    parser.add_argument('--tools', required=True, help='工具JSON路径')
    parser.add_argument('--config', default='../config/config.yaml', help='配置文件')
    args = parser.parse_args()
    try:
        pipeline = MCPFlowPipeline(args.config)
        pipeline.run(args.tools)
    except Exception as e:
        logger.error(f"运行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
