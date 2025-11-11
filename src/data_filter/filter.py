"""
Data Filtration Module
基于论文Section 3.3实现严格的数据过滤机制
"""
import json
import logging
from typing import List, Dict, Any, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


class DataFilter:
    """数据过滤器 - 实现多维度的质量控制"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.filter_config = config.get('data_filtering', {})
        self.filtering_strategy = config.get('filtering_strategy', {})

        # 使用统一的LLM客户端
        self.llm_client = LLMClient(config)

        # 加载嵌入模型
        self.embedding_model = None
        self._load_embedding_model()

    def _load_embedding_model(self):
        """加载嵌入模型用于相似度计算"""
        model_name = self.filter_config.get('embedding_model', 'mixedbread-ai/mxbai-embed-large-v1')
        try:
            self.embedding_model = SentenceTransformer(model_name, device='cuda', trust_remote_code=True)
            logger.info(f"成功加载嵌入模型: {model_name}")
        except Exception as e:
            logger.error(f"加载嵌入模型失败: {e}")

    def filter_by_embedding_similarity(self, samples: List[Dict]) -> List[Dict]:
        """
        基于嵌入相似度过滤

        论文Section 3.3: "计算指令-描述嵌入相似度,
        设置阈值为0.8并丢弃超过此值的指令"

        Args:
            samples: 数据样本列表,每个包含 {instruction, tool_description}

        Returns:
            List[Dict]: 过滤后的样本
        """
        if not self.embedding_model:
            logger.warning("嵌入模型未加载,跳过相似度过滤")
            return samples

        threshold = self.filter_config.get('similarity_threshold', 0.8)
        filtered_samples = []

        logger.info(f"开始嵌入相似度过滤,阈值={threshold}")

        for sample in samples:
            instruction = sample.get('instruction', '')
            tool_description = sample.get('tool_description', '')

            # 计算嵌入
            emb1 = self.embedding_model.encode(instruction, max_length=512, task="text-matching")
            emb2 = self.embedding_model.encode(tool_description, max_length=512, task="text-matching")

            # 计算余弦相似度
            similarity = cosine_similarity([emb1], [emb2])[0][0]

            if similarity < threshold:
                filtered_samples.append(sample)
            else:
                logger.debug(f"过滤高相似度样本 (sim={similarity:.3f}): {instruction[:50]}...")

        logger.info(f"嵌入相似度过滤: {len(samples)} → {len(filtered_samples)}")
        return filtered_samples

    def filter_by_tool_invocation(self, samples: List[Dict]) -> List[Dict]:
        """
        工具调用验证过滤

        论文Section 3.3: "指示GPT-4o和DeepSeek-V3从标记的工具和两个随机采样的候选项中选择正确的工具。
        对于两个模型都无法识别预期工具的指令将被丢弃"

        注意：可通过filtering_strategy.skip_double_verification跳过此步骤

        Args:
            samples: 数据样本列表,每个包含 {instruction, tool_name, candidate_tools}

        Returns:
            List[Dict]: 验证通过的样本
        """
        # 检查是否跳过双重验证
        if self.filtering_strategy.get('skip_double_verification', False):
            logger.info("配置为跳过双重验证，直接返回所有样本")
            return samples

        filtered_samples = []

        logger.info("开始工具调用验证过滤（单模型验证）")

        for sample in samples:
            # 只使用primary模型验证
            result = self._verify_tool_selection(sample)

            if result:
                filtered_samples.append(sample)
            else:
                logger.debug(f"过滤工具调用失败样本: {sample.get('instruction', '')[:50]}...")

        logger.info(f"工具调用验证过滤: {len(samples)} → {len(filtered_samples)}")
        return filtered_samples

    def _verify_tool_selection(self, sample: Dict) -> bool:
        """验证模型是否能正确选择工具"""
        instruction = sample.get('instruction', '')
        correct_tool = sample.get('tool_name', '')
        candidate_tools = sample.get('candidate_tools', [])

        prompt = f"""Given the following instruction and tool options, select the most appropriate tool.

Instruction: {instruction}

Available Tools:
{json.dumps(candidate_tools, indent=2)}

Return ONLY the tool name that best matches the instruction.
"""

        try:
            # 使用LLMClient进行验证
            content = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                task_type='verification',
                temperature=0
            )

            if not content:
                return False

            selected_tool = content.strip()
            return correct_tool in selected_tool

        except Exception as e:
            logger.error(f"工具选择验证时出错: {e}")
            return False

    def filter_by_quality_score(self, samples: List[Dict]) -> List[Dict]:
        """
        质量评分过滤

        论文Section 3.3: "使用DeepSeek-V3作为判断模型。
        丢弃质量评分低于6/10阈值的指令和函数调用"

        Args:
            samples: 数据样本列表,每个包含 {instruction, function_call}

        Returns:
            List[Dict]: 高质量样本
        """
        threshold = self.filter_config.get('quality_score_threshold', 6)
        filtered_samples = []

        logger.info(f"开始质量评分过滤,阈值={threshold}")

        for sample in samples:
            score = self._evaluate_quality(sample)

            if score >= threshold:
                sample['quality_score'] = score
                filtered_samples.append(sample)
            else:
                logger.debug(f"过滤低质量样本 (score={score}): {sample.get('instruction', '')[:50]}...")

        logger.info(f"质量评分过滤: {len(samples)} → {len(filtered_samples)}")
        return filtered_samples

    def _evaluate_quality(self, sample: Dict) -> int:
        """
        评估样本质量

        参考论文Appendix E.1 - Prompt 6
        """
        instruction = sample.get('instruction', '')
        function_call = sample.get('function_call', {})

        prompt = f"""You are an expert in information retrieval and query optimization. Your task is to evaluate the quality of the following query and function call:

**Instruction**: "{instruction}"

**Function Call**: {json.dumps(function_call, indent=2)}

When assessing, consider:
1. **Clarity** – Is the query unambiguous and easy to understand?
2. **Specificity** – Does it include enough detail to retrieve relevant results?
3. **Relevance** – Is it likely to produce results aligned with the user's intent?
4. **Completeness** – Does it provide all necessary context or constraints?
5. **Function Call Correctness** – Does the function call match the instruction?

## Output Format
[Score]: 1–10 (10 = excellent)

Return ONLY the score number, nothing else.
"""

        try:
            # 使用LLMClient进行评分
            content = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                task_type='scoring',
                temperature=0
            )

            if not content:
                logger.warning("质量评分API调用失败")
                return 0

            content = content.strip()

            # 提取分数
            import re
            score_match = re.search(r'\d+', content)
            if score_match:
                score = int(score_match.group())
                return min(max(score, 0), 10)  # 限制在0-10范围
            else:
                logger.warning("无法从响应中提取分数")
                return 0

        except Exception as e:
            logger.error(f"质量评分时出错: {e}")
            return 0

    def filter_trajectory(self, trajectories: List[Dict]) -> List[Dict]:
        """
        Trajectory过滤

        论文Section 3.3: "许多服务器需要特定设置(例如API密钥、个人工作区或软件依赖),
        而其他服务器可能暂时不可用。我们过滤掉在这种条件下收集的无效工具响应的轨迹"

        Args:
            trajectories: 轨迹列表,每个包含 {instruction, function_call, tool_response}

        Returns:
            List[Dict]: 有效的轨迹
        """
        filtered_trajectories = []

        logger.info("开始Trajectory过滤")

        for traj in trajectories:
            tool_response = traj.get('tool_response', {})

            # 检查响应是否有效
            if self._is_valid_response(tool_response):
                filtered_trajectories.append(traj)
            else:
                logger.debug(f"过滤无效响应轨迹: {traj.get('instruction', '')[:50]}...")

        logger.info(f"Trajectory过滤: {len(trajectories)} → {len(filtered_trajectories)}")
        return filtered_trajectories

    def _is_valid_response(self, tool_response: Dict) -> bool:
        """检查工具响应是否有效"""
        # 检查是否包含错误
        if 'error' in tool_response or 'Error' in str(tool_response):
            return False

        # 检查是否有实际内容
        content = tool_response.get('content', '')
        if not content or len(content) < 10:
            return False

        return True


if __name__ == "__main__":
    # 测试代码
    import yaml

    logging.basicConfig(level=logging.INFO)

    with open("config.yaml", 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    filter_module = DataFilter(config)  # 不需要传api_keys了

    # 测试嵌入相似度过滤
    test_samples = [
        {
            "instruction": "Search for information about Python",
            "tool_description": "Search for information"
        },
        {
            "instruction": "Find details about machine learning",
            "tool_description": "Search for information"
        }
    ]

    filtered = filter_module.filter_by_embedding_similarity(test_samples)
    print(f"过滤后样本数: {len(filtered)}")
