"""
统一的LLM API客户端
支持多provider配置和自动fallback
"""
import logging
import time
from typing import Dict, List, Optional, Any
from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    """统一的LLM客户端，支持多provider和自动fallback"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化LLM客户端

        Args:
            config: 完整的配置字典，包含llm_providers等配置
        """
        self.config = config
        self.providers = config.get('llm_providers', {})
        self.task_assignments = config.get('task_assignments', {})

        # 初始化OpenAI客户端
        self.clients = {}
        for provider_name, provider_config in self.providers.items():
            if provider_config.get('provider') == 'openai':
                self.clients[provider_name] = OpenAI(
                    api_key=provider_config['api_key'],
                    base_url=provider_config['base_url'],
                    timeout=provider_config.get('timeout', 60),
                    max_retries=provider_config.get('max_retries', 3)
                )
                logger.info(f"初始化LLM provider: {provider_name} ({provider_config['name']})")

    def get_provider_for_task(self, task_type: str) -> str:
        """
        根据任务类型获取应该使用的provider

        Args:
            task_type: 任务类型 (generation/verification/scoring/function_call)

        Returns:
            provider名称 (primary/fallback)
        """
        return self.task_assignments.get(task_type, 'primary')

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        task_type: str = 'generation',
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> Optional[str]:
        """
        调用LLM生成回复，支持自动fallback

        Args:
            messages: 消息列表
            task_type: 任务类型
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数

        Returns:
            生成的文本，失败返回None
        """
        # 获取主provider
        primary_provider = self.get_provider_for_task(task_type)
        providers_to_try = [primary_provider]

        # 如果primary失败，尝试fallback
        if 'fallback' in self.clients and primary_provider != 'fallback':
            providers_to_try.append('fallback')

        last_error = None
        for provider_name in providers_to_try:
            try:
                provider_config = self.providers[provider_name]
                client = self.clients[provider_name]

                logger.info(f"使用provider: {provider_config['name']} (model: {provider_config['model']})")

                # 调用API
                response = client.chat.completions.create(
                    model=provider_config['model'],
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )

                # 提取回复内容
                content = response.choices[0].message.content

                logger.info(f"✅ API调用成功 (provider: {provider_config['name']})")
                return content

            except Exception as e:
                last_error = e
                logger.warning(f"❌ Provider {provider_name} 失败: {str(e)}")

                # 如果还有fallback，继续尝试
                if provider_name != providers_to_try[-1]:
                    logger.info(f"尝试切换到fallback provider...")
                    time.sleep(1)
                    continue
                else:
                    # 所有provider都失败了
                    logger.error(f"所有provider都失败了，最后错误: {str(last_error)}")
                    return None

        return None

    def get_model_name(self, task_type: str = 'generation') -> str:
        """获取当前任务使用的模型名称"""
        provider_name = self.get_provider_for_task(task_type)
        return self.providers[provider_name]['model']

    def get_provider_info(self, provider_name: str = 'primary') -> Dict[str, Any]:
        """获取provider的详细信息"""
        return self.providers.get(provider_name, {})
