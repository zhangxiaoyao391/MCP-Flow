"""数据过滤器 - 3重过滤(无嵌入)"""
import logging
import json
from typing import Dict, List

logger = logging.getLogger(__name__)

class DataFilter:
    def __init__(self, config: Dict):
        from utils.llm_client import LLMClient
        self.config = config
        self.filter_config = config.get('data_filtering', {})
        self.llm_client = LLMClient(config)
        logger.info("数据过滤器初始化(简化版,无嵌入)")

    def filter_by_tool_invocation(self, samples: List[Dict]) -> List[Dict]:
        """过滤1: 工具调用验证"""
        filtered = []
        for sample in samples:
            try:
                tool_name = sample['tool_info']['tool_name']
                call_name = sample['function_call']['name']
                if tool_name == call_name:
                    filtered.append(sample)
                else:
                    logger.debug(f"工具名不匹配: {tool_name} != {call_name}")
            except KeyError:
                logger.warning("样本缺少必需字段")
        return filtered

    def filter_by_quality_score(self, samples: List[Dict]) -> List[Dict]:
        """过滤2: 质量评分"""
        threshold = self.filter_config.get('quality_score_threshold', 6)
        filtered = []
        for sample in samples:
            prompt = f"""评估样本质量(0-10分):
指令: {sample.get('instruction', '')}
函数调用: {json.dumps(sample.get('function_call', {}), ensure_ascii=False)}
只返回分数:"""
            try:
                response = self.llm_client.chat_completion([{"role": "user", "content": prompt}], 'scoring', 0.3)
                if response:
                    import re
                    match = re.search(r'\d+', response)
                    if match:
                        score = int(match.group())
                        if score >= threshold:
                            filtered.append(sample)
                        else:
                            logger.debug(f"质量分数不足: {score} < {threshold}")
            except Exception as e:
                logger.error(f"评分失败: {e}")
        return filtered

    def filter_trajectory(self, samples: List[Dict]) -> List[Dict]:
        """过滤3: 轨迹验证"""
        filtered = []
        for sample in samples:
            required_keys = ['instruction', 'function_call', 'tool_response', 'final_response']
            if all(k in sample for k in required_keys):
                if sample.get('final_response') and len(sample['final_response']) > 5:
                    filtered.append(sample)
                else:
                    logger.debug("final_response为空或过短")
            else:
                logger.debug("样本缺少必需字段")
        return filtered
