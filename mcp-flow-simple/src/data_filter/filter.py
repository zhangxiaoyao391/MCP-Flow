"""数据过滤器 - 完整版(包含交叉验证和增强错误检测)"""
import logging
import json
import random
import re
from typing import Dict, List

logger = logging.getLogger(__name__)

class DataFilter:
    def __init__(self, config: Dict, all_tools: List[Dict] = None):
        from utils.llm_client import LLMClient
        self.config = config
        self.filter_config = config.get('data_filtering', {})
        self.llm_client = LLMClient(config)
        self.all_tools = all_tools or []  # 用于生成干扰工具
        logger.info("数据过滤器初始化(完整版)")

    def filter_by_tool_invocation(self, samples: List[Dict]) -> List[Dict]:
        """
        过滤1: 工具调用验证 (完整版 - 增加交叉验证)

        简化版: 仅检查名称匹配
        完整版: 使用双模型交叉验证 + 干扰工具测试
        """
        if not self.filter_config.get('enable_cross_validation', False):
            # 简化版逻辑
            return self._simple_tool_validation(samples)

        # 完整版逻辑
        return self._cross_validate_tool_selection(samples)

    def _simple_tool_validation(self, samples: List[Dict]) -> List[Dict]:
        """简化版工具验证 - 仅检查名称匹配"""
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
        logger.info(f"✓ 简化验证: {len(filtered)}/{len(samples)} 通过")
        return filtered

    def _cross_validate_tool_selection(self, samples: List[Dict]) -> List[Dict]:
        """
        完整版工具验证 - 双模型交叉验证

        流程:
        1. 为每个样本生成N个干扰工具
        2. 使用DeepSeek-V3.1和DeepSeek-V3独立选择
        3. 只有两个模型都选错才丢弃样本
        """
        if not self.all_tools or len(self.all_tools) < 3:
            logger.warning("工具池不足,退化为简化验证")
            return self._simple_tool_validation(samples)

        num_distractors = self.filter_config.get('num_distractor_tools', 2)
        filtered = []

        for idx, sample in enumerate(samples):
            try:
                # 获取正确工具
                correct_tool = {
                    'name': sample['tool_info']['tool_name'],
                    'description': sample['tool_info'].get('tool_description', '')
                }

                # 随机选择干扰工具
                distractors = self._generate_distractor_tools(
                    correct_tool['name'],
                    num_distractors
                )

                if not distractors:
                    # 无法生成干扰工具,保留样本
                    filtered.append(sample)
                    continue

                # 交叉验证
                validation_result = self.llm_client.cross_validate_tool_selection(
                    instruction=sample.get('instruction', ''),
                    correct_tool=correct_tool,
                    distractor_tools=distractors
                )

                primary_correct = validation_result['primary'] == validation_result['correct']
                secondary_correct = validation_result['secondary'] == validation_result['correct']

                # 至少一个模型选对就保留
                if primary_correct or secondary_correct:
                    filtered.append(sample)
                    logger.debug(f"[{idx+1}] 验证通过 (主:{primary_correct}, 备:{secondary_correct})")
                else:
                    logger.debug(f"[{idx+1}] 验证失败 - 两个模型都选错")

            except Exception as e:
                logger.error(f"交叉验证失败: {e}, 保留样本")
                filtered.append(sample)

        logger.info(f"✓ 交叉验证: {len(filtered)}/{len(samples)} 通过")
        return filtered

    def _generate_distractor_tools(self, correct_tool_name: str, num: int) -> List[Dict]:
        """生成干扰工具"""
        available = [t for t in self.all_tools if t.get('name') != correct_tool_name]
        if len(available) < num:
            return []

        selected = random.sample(available, num)
        return [
            {
                'name': t.get('name', ''),
                'description': t.get('description', '')
            }
            for t in selected
        ]

    def filter_by_quality_score(self, samples: List[Dict]) -> List[Dict]:
        """
        过滤2: 质量评分

        使用DeepSeek-V3.1进行质量评分
        """
        threshold = self.filter_config.get('quality_score_threshold', 6)
        filtered = []

        for idx, sample in enumerate(samples):
            prompt = f"""评估以下Function Calling样本的质量(0-10分):

指令: {sample.get('instruction', '')}
工具: {sample.get('tool_info', {}).get('tool_name', '')}
函数调用: {json.dumps(sample.get('function_call', {}), ensure_ascii=False)}

评分标准:
- 指令是否清晰明确
- 函数调用是否正确匹配指令
- 参数是否合理

只返回一个数字分数(0-10):"""

            try:
                response = self.llm_client.chat_completion(
                    [{"role": "user", "content": prompt}],
                    'scoring',
                    temperature=0.3
                )

                if response:
                    match = re.search(r'\d+', response)
                    if match:
                        score = int(match.group())
                        if score >= threshold:
                            filtered.append(sample)
                            logger.debug(f"[{idx+1}] 质量分数: {score} ✓")
                        else:
                            logger.debug(f"[{idx+1}] 质量分数不足: {score} < {threshold}")
                    else:
                        logger.debug(f"[{idx+1}] 无法解析分数,保留样本")
                        filtered.append(sample)
                else:
                    logger.debug(f"[{idx+1}] 评分失败,保留样本")
                    filtered.append(sample)

            except Exception as e:
                logger.error(f"评分失败: {e}, 保留样本")
                filtered.append(sample)

        logger.info(f"✓ 质量评分: {len(filtered)}/{len(samples)} 通过")
        return filtered

    def filter_trajectory(self, samples: List[Dict]) -> List[Dict]:
        """
        过滤3: 轨迹验证 (完整版 - 增强错误检测)

        简化版: 仅检查字段完整性
        完整版: 增加错误类型识别
        """
        if not self.filter_config.get('enable_error_detection', False):
            # 简化版逻辑
            return self._simple_trajectory_validation(samples)

        # 完整版逻辑
        return self._enhanced_trajectory_validation(samples)

    def _simple_trajectory_validation(self, samples: List[Dict]) -> List[Dict]:
        """简化版轨迹验证"""
        filtered = []
        required_keys = ['instruction', 'function_call', 'tool_response', 'final_response']

        for sample in samples:
            if all(k in sample for k in required_keys):
                if sample.get('final_response') and len(sample['final_response']) > 5:
                    filtered.append(sample)
                else:
                    logger.debug("final_response为空或过短")
            else:
                logger.debug("样本缺少必需字段")

        logger.info(f"✓ 简化轨迹验证: {len(filtered)}/{len(samples)} 通过")
        return filtered

    def _enhanced_trajectory_validation(self, samples: List[Dict]) -> List[Dict]:
        """
        完整版轨迹验证 - 增强错误检测

        检测内容:
        1. 字段完整性
        2. HTTP错误 (503, 429, 401, 403等)
        3. API错误消息
        4. 空响应/截断响应
        5. 格式错误
        """
        filtered = []
        required_keys = ['instruction', 'function_call', 'tool_response', 'final_response']

        # 错误模式
        http_error_patterns = [
            r'503\s+Service\s+Unavailable',
            r'429\s+Too\s+Many\s+Requests',
            r'401\s+Unauthorized',
            r'403\s+Forbidden',
            r'500\s+Internal\s+Server\s+Error',
            r'502\s+Bad\s+Gateway',
            r'504\s+Gateway\s+Timeout',
        ] if self.filter_config.get('check_http_errors', True) else []

        api_error_patterns = [
            r'API\s+key\s+(invalid|missing|expired)',
            r'(rate\s+limit|quota)\s+exceeded',
            r'server\s+(unavailable|down|error)',
            r'connection\s+(timeout|refused|failed)',
            r'invalid\s+(request|response)',
        ] if self.filter_config.get('check_api_errors', True) else []

        all_error_patterns = http_error_patterns + api_error_patterns

        for idx, sample in enumerate(samples):
            # 1. 检查字段完整性
            if not all(k in sample for k in required_keys):
                logger.debug(f"[{idx+1}] 缺少必需字段")
                continue

            # 2. 检查响应内容
            tool_response = sample.get('tool_response', {})
            final_response = sample.get('final_response', '')

            # 转换为字符串检查
            response_text = ''
            if isinstance(tool_response, dict):
                response_text = json.dumps(tool_response, ensure_ascii=False)
            elif isinstance(tool_response, str):
                response_text = tool_response

            combined_text = response_text + ' ' + final_response

            # 3. 检查错误模式
            has_error = False
            for pattern in all_error_patterns:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    logger.debug(f"[{idx+1}] 检测到错误: {pattern}")
                    has_error = True
                    break

            if has_error:
                continue

            # 4. 检查响应长度
            if not final_response or len(final_response) < 5:
                logger.debug(f"[{idx+1}] final_response过短")
                continue

            # 5. 检查是否为空/无效响应
            invalid_responses = [
                'error', 'failed', 'unavailable',
                'null', 'none', 'n/a',
                '服务器错误', '请求失败', '不可用'
            ]

            if any(inv in final_response.lower() for inv in invalid_responses):
                # 进一步检查是否真的是错误
                if len(final_response) < 20:  # 太短的包含错误关键词的响应
                    logger.debug(f"[{idx+1}] 检测到无效响应: {final_response[:50]}")
                    continue

            # 通过所有检查
            filtered.append(sample)

        logger.info(f"✓ 增强轨迹验证: {len(filtered)}/{len(samples)} 通过")
        return filtered
