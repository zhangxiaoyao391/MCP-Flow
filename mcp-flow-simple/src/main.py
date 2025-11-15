"""MCP-Flow完整版主入口"""
import logging
import yaml
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from data_generator.generator import DataGenerator
from data_filter.filter import DataFilter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MCPFlowPipeline:
    def __init__(self, config_path: str):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        self._validate_config()
        logger.info("Pipeline初始化完成")

    def _validate_config(self):
        """验证配置文件完整性"""
        required_keys = ['llm_providers', 'data_generation', 'data_filtering', 'output_paths']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"配置文件缺少必需字段: {key}")

        # 验证provider配置
        providers = self.config.get('llm_providers', {})
        if 'primary' not in providers:
            raise ValueError("配置文件必须包含primary provider")

        for provider_name, provider_config in providers.items():
            required_provider_keys = ['api_key', 'base_url', 'model']
            for k in required_provider_keys:
                if k not in provider_config:
                    raise ValueError(f"Provider {provider_name} 缺少配置: {k}")

        # 验证生成配置参数范围
        gen_config = self.config['data_generation']
        if gen_config.get('instruction_per_tool', 5) <= 0:
            raise ValueError("instruction_per_tool 必须大于0")
        if not 0 <= gen_config.get('temperature', 0.7) <= 2:
            raise ValueError("temperature 必须在 0-2 之间")

        # 验证过滤配置
        filter_config = self.config['data_filtering']
        threshold = filter_config.get('quality_score_threshold', 6)
        if not 0 <= threshold <= 10:
            raise ValueError("quality_score_threshold 必须在 0-10 之间")

    def load_tools(self, json_path: str) -> Dict:
        logger.info(f"加载工具数据: {json_path}")
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 验证工具JSON格式
        self._validate_tools_data(data)
        logger.info(f"服务器: {data['server_info']['name']}, 工具数: {len(data['tools'])}")
        return data

    def _validate_tools_data(self, data: Dict):
        """验证工具JSON格式"""
        if 'server_info' not in data:
            raise ValueError("工具JSON缺少 'server_info' 字段")
        if 'tools' not in data or not isinstance(data['tools'], list):
            raise ValueError("工具JSON缺少 'tools' 字段或格式错误")

        server_info = data['server_info']
        if 'name' not in server_info or 'description' not in server_info:
            raise ValueError("server_info 必须包含 'name' 和 'description'")

        for idx, tool in enumerate(data['tools']):
            if 'name' not in tool:
                raise ValueError(f"工具 #{idx+1} 缺少 'name' 字段")
            if 'description' not in tool:
                raise ValueError(f"工具 '{tool.get('name', '#'+str(idx+1))}' 缺少 'description' 字段")
            if 'inputSchema' not in tool:
                logger.warning(f"工具 '{tool['name']}' 缺少 'inputSchema' 字段")

    def generate_data(self, tools_data: Dict) -> List[Dict]:
        logger.info("=" * 60)
        logger.info("阶段1: 数据生成 (并行处理)")
        logger.info("=" * 60)
        generator = DataGenerator(self.config)
        server_info = tools_data['server_info']
        tools = tools_data['tools']

        # 预估API调用次数
        estimated_calls = len(tools) * self.config['data_generation'].get('instruction_per_tool', 5) * 5
        logger.info(f"预估API调用次数: ~{estimated_calls} (每工具约5-10次)")
        logger.info(f"并行线程数: 5")

        def process_tool(tool_data):
            """处理单个工具"""
            idx, tool = tool_data
            results = []
            try:
                logger.info(f"[{idx}/{len(tools)}] 处理: {tool.get('name')}")
                instructions = generator.generate_instructions(tool, server_info)
                logger.info(f"  [{tool.get('name')}] 生成{len(instructions)}条指令")
                for inst in instructions:
                    revised = generator.slot_fill_revision(inst, tool)
                    evolved = generator.wizardlm_evolution(revised, self.config['data_generation'].get('evolution_depth', 1))
                    sample = generator.generate_function_call(evolved, tool, server_info)
                    if sample:
                        results.append(sample)
                logger.info(f"  [{tool.get('name')}] 完成: {len(results)}个样本")
            except Exception as e:
                logger.error(f"  [{tool.get('name')}] 处理失败: {e}")
            return results

        # 并行处理,最多5个线程
        samples = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(process_tool, (idx, tool)): tool
                       for idx, tool in enumerate(tools, 1)}

            for future in as_completed(futures):
                samples.extend(future.result())

        output_dir = Path(self.config['output_paths']['function_calls'])
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(samples, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ 生成完成: {len(samples)}个样本, 保存至 {output_file}")

        # 打印API调用统计
        generator.client.print_api_stats()

        return samples

    def filter_data(self, samples: List[Dict], all_tools: List[Dict]) -> List[Dict]:
        """
        数据过滤 (完整版)

        参数:
            samples: 待过滤样本
            all_tools: 所有工具列表(用于生成干扰工具)
        """
        logger.info("=" * 60)
        logger.info("阶段2: 数据过滤 (完整版)")
        logger.info("=" * 60)

        # 初始化过滤器,传入工具池
        filter_module = DataFilter(self.config, all_tools)
        initial = len(samples)

        # 显示配置信息
        filter_config = self.config.get('data_filtering', {})
        if filter_config.get('enable_cross_validation', False):
            logger.info(f"✓ 交叉验证: 启用 (双模型 + {filter_config.get('num_distractor_tools', 2)}个干扰工具)")
        else:
            logger.info("⚠ 交叉验证: 禁用 (简化模式)")

        if filter_config.get('enable_error_detection', False):
            logger.info("✓ 错误检测: 启用 (HTTP/API错误识别)")
        else:
            logger.info("⚠ 错误检测: 禁用 (简化模式)")

        # 过滤步骤
        samples = filter_module.filter_by_tool_invocation(samples)
        logger.info(f"工具验证: {len(samples)}/{initial}")

        samples = filter_module.filter_by_quality_score(samples)
        logger.info(f"质量评分: {len(samples)}/{initial}")

        samples = filter_module.filter_trajectory(samples)
        logger.info(f"轨迹验证: {len(samples)}/{initial}")

        # 保存结果
        output_dir = Path(self.config['output_paths']['filtered_data'])
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(samples, f, ensure_ascii=False, indent=2)

        percent = (len(samples)/initial*100) if initial > 0 else 0
        logger.info(f"✓ 过滤完成: {len(samples)}个样本({percent:.1f}%), 保存至 {output_file}")

        # 打印API调用统计
        filter_module.llm_client.print_api_stats()

        return samples

    def run(self, tools_json: str):
        start = datetime.now()
        logger.info("=" * 60)
        logger.info("MCP-Flow 完整版 Pipeline")
        logger.info("=" * 60)

        # 加载工具
        tools_data = self.load_tools(tools_json)
        all_tools = tools_data['tools']

        # 数据生成
        samples = self.generate_data(tools_data)

        # 数据过滤 (传入工具池)
        filtered = self.filter_data(samples, all_tools)

        # 统计
        duration = datetime.now() - start
        logger.info("=" * 60)
        logger.info(f"✓ 完成! 耗时: {duration}")
        logger.info(f"✓ 工具: {len(all_tools)}, 生成: {len(samples)}, 通过: {len(filtered)}")
        logger.info("=" * 60)

def main():
    parser = argparse.ArgumentParser(description='MCP-Flow完整版')
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
