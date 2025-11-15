"""
LLM统一调用客户端
支持多provider配置和自动fallback
"""
import logging
from typing import Dict, List, Optional
from openai import OpenAI, APIError, APIConnectionError, APITimeoutError, RateLimitError

logger = logging.getLogger(__name__)


class LLMClient:
    """
    LLM统一调用客户端
    
    功能:
    - 支持多个LLM provider配置
    - 自动fallback机制
    - 统一的调用接口
    """

    def __init__(self, config: Dict):
        """
        初始化LLM客户端

        参数:
            config: 完整配置字典,包含llm_providers
        """
        self.config = config
        self.providers = config.get('llm_providers', {})
        self.task_assignments = config.get('task_assignments', {})

        # API调用统计
        self.api_call_stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'provider_stats': {}
        }
        
        # 初始化各provider的OpenAI客户端
        self.clients = {}
        for provider_name, provider_config in self.providers.items():
            # 初始化provider统计
            self.api_call_stats['provider_stats'][provider_name] = {
                'calls': 0,
                'success': 0,
                'failed': 0
            }

            try:
                self.clients[provider_name] = OpenAI(
                    api_key=provider_config['api_key'],
                    base_url=provider_config['base_url'],
                    timeout=provider_config.get('timeout', 60),
                    max_retries=provider_config.get('max_retries', 3)
                )
                logger.info(f"✓ 初始化LLM provider: {provider_config.get('name', provider_name)}")
            except (ValueError, KeyError) as e:
                logger.error(f"✗ Provider {provider_name} 配置错误: {e}")
            except Exception as e:
                logger.error(f"✗ 初始化provider {provider_name} 失败: {e}")

    def get_provider_for_task(self, task_type: str) -> str:
        """
        获取任务对应的provider名称
        
        参数:
            task_type: 任务类型(generation/verification/scoring等)
            
        返回:
            provider名称
        """
        # 优先使用任务分配配置
        assigned = self.task_assignments.get(task_type, 'primary')
        return assigned if assigned in self.clients else 'primary'

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        task_type: str = 'generation',
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> Optional[str]:
        """
        统一的聊天补全接口
        
        参数:
            messages: 消息列表,格式[{"role": "user", "content": "..."}]
            task_type: 任务类型,用于选择provider
            temperature: 生成温度
            max_tokens: 最大token数
            
        返回:
            生成的文本内容,失败返回None
        """
        # 获取primary provider
        primary_provider = self.get_provider_for_task(task_type)
        
        # 尝试primary provider
        result = self._call_provider(
            primary_provider,
            messages,
            temperature,
            max_tokens
        )
        
        if result:
            return result

        # Primary失败,尝试fallback
        if 'fallback' in self.clients and primary_provider != 'fallback':
            fallback_config = self.providers.get('fallback', {})
            # 检查fallback是否配置了有效的API key
            if fallback_config.get('api_key') and fallback_config['api_key'] != 'sk-placeholder':
                logger.warning(f"Primary provider失败,尝试fallback...")
                result = self._call_provider(
                    'fallback',
                    messages,
                    temperature,
                    max_tokens
                )
                if result:
                    return result
            else:
                logger.debug("Fallback未配置有效API key,跳过")

        logger.error("所有provider均失败")
        return None

    def _call_provider(
        self,
        provider_name: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int
    ) -> Optional[str]:
        """
        调用指定provider
        
        参数:
            provider_name: provider名称
            messages: 消息列表
            temperature: 温度
            max_tokens: 最大token
            
        返回:
            生成内容或None
        """
        if provider_name not in self.clients:
            logger.error(f"Provider {provider_name} 不存在")
            return None

        # 记录调用
        self.api_call_stats['total_calls'] += 1
        self.api_call_stats['provider_stats'][provider_name]['calls'] += 1

        try:
            client = self.clients[provider_name]
            provider_config = self.providers[provider_name]
            model = provider_config['model']

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            content = response.choices[0].message.content

            # 记录成功
            self.api_call_stats['successful_calls'] += 1
            self.api_call_stats['provider_stats'][provider_name]['success'] += 1

            return content

        except RateLimitError as e:
            logger.error(f"Provider {provider_name} 速率限制: {e}")
            self._record_failure(provider_name)
            return None
        except APITimeoutError as e:
            logger.error(f"Provider {provider_name} 请求超时: {e}")
            self._record_failure(provider_name)
            return None
        except APIConnectionError as e:
            logger.error(f"Provider {provider_name} 连接失败: {e}")
            self._record_failure(provider_name)
            return None
        except APIError as e:
            logger.error(f"Provider {provider_name} API错误: {e}")
            self._record_failure(provider_name)
            return None
        except (KeyError, IndexError) as e:
            logger.error(f"Provider {provider_name} 响应格式错误: {e}")
            self._record_failure(provider_name)
            return None
        except Exception as e:
            logger.error(f"Provider {provider_name} 未知错误: {e}")
            self._record_failure(provider_name)
            return None

    def _record_failure(self, provider_name: str):
        """记录失败调用"""
        self.api_call_stats['failed_calls'] += 1
        if provider_name in self.api_call_stats['provider_stats']:
            self.api_call_stats['provider_stats'][provider_name]['failed'] += 1

    def get_model_name(self, task_type: str = 'generation') -> str:
        """获取任务对应的模型名称"""
        provider = self.get_provider_for_task(task_type)
        return self.providers.get(provider, {}).get('model', 'unknown')

    def get_provider_info(self) -> Dict:
        """获取所有provider信息"""
        return {name: config.get('name', name) for name, config in self.providers.items()}

    def get_api_stats(self) -> Dict:
        """获取API调用统计信息"""
        return self.api_call_stats.copy()

    def print_api_stats(self):
        """打印API调用统计"""
        stats = self.api_call_stats
        logger.info("=" * 60)
        logger.info("API调用统计")
        logger.info("=" * 60)
        logger.info(f"总调用次数: {stats['total_calls']}")
        logger.info(f"成功: {stats['successful_calls']} ({stats['successful_calls']/stats['total_calls']*100:.1f}%)" if stats['total_calls'] > 0 else "成功: 0 (0.0%)")
        logger.info(f"失败: {stats['failed_calls']} ({stats['failed_calls']/stats['total_calls']*100:.1f}%)" if stats['total_calls'] > 0 else "失败: 0 (0.0%)")
        logger.info("-" * 60)
        for provider_name, provider_stats in stats['provider_stats'].items():
            if provider_stats['calls'] > 0:
                logger.info(f"{provider_name}:")
                logger.info(f"  调用: {provider_stats['calls']}")
                logger.info(f"  成功: {provider_stats['success']}")
                logger.info(f"  失败: {provider_stats['failed']}")
        logger.info("=" * 60)

    def cross_validate_tool_selection(
        self,
        instruction: str,
        correct_tool: Dict,
        distractor_tools: List[Dict],
        temperature: float = 0.3
    ) -> Dict[str, str]:
        """
        交叉验证工具选择 (完整版新增功能)

        使用两个DeepSeek模型独立验证工具选择的正确性

        参数:
            instruction: 用户指令
            correct_tool: 正确的工具信息
            distractor_tools: 干扰工具列表
            temperature: 生成温度

        返回:
            {"primary": "tool_name", "secondary": "tool_name"}
        """
        import random
        import json

        # 构造候选工具列表
        candidates = [correct_tool] + distractor_tools
        random.shuffle(candidates)

        # 构造提示词
        tools_desc = "\n".join([
            f"{i+1}. {tool['name']}: {tool.get('description', 'No description')}"
            for i, tool in enumerate(candidates)
        ])

        prompt = f"""给定用户指令,从以下工具中选择最合适的一个。

用户指令: {instruction}

可用工具:
{tools_desc}

只返回工具名称,不要其他内容。"""

        messages = [{"role": "user", "content": prompt}]

        # 主模型验证
        primary_provider = self.task_assignments.get('cross_validation_primary', 'deepseek')
        primary_result = self._call_provider(
            primary_provider,
            messages,
            temperature,
            max_tokens=100
        )

        # 备用模型验证
        secondary_provider = self.task_assignments.get('cross_validation_secondary', 'deepseek_backup')
        secondary_result = self._call_provider(
            secondary_provider,
            messages,
            temperature,
            max_tokens=100
        )

        # 清理结果
        def clean_result(result: Optional[str]) -> str:
            if not result:
                return ""
            # 提取工具名称
            result = result.strip()
            # 尝试匹配候选工具名称
            for tool in candidates:
                if tool['name'] in result:
                    return tool['name']
            return result

        return {
            "primary": clean_result(primary_result),
            "secondary": clean_result(secondary_result),
            "correct": correct_tool['name']
        }
