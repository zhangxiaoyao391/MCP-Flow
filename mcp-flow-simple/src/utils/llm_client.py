"""
LLM统一调用客户端
支持多provider配置和自动fallback
"""
import logging
from typing import Dict, List, Optional
from openai import OpenAI

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
        
        # 初始化各provider的OpenAI客户端
        self.clients = {}
        for provider_name, provider_config in self.providers.items():
            try:
                self.clients[provider_name] = OpenAI(
                    api_key=provider_config['api_key'],
                    base_url=provider_config['base_url'],
                    timeout=provider_config.get('timeout', 60),
                    max_retries=provider_config.get('max_retries', 3)
                )
                logger.info(f"✓ 初始化LLM provider: {provider_config.get('name', provider_name)}")
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
            logger.warning(f"Primary provider失败,尝试fallback...")
            result = self._call_provider(
                'fallback',
                messages,
                temperature,
                max_tokens
            )
            if result:
                return result
        
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
            return content
            
        except Exception as e:
            logger.error(f"Provider {provider_name} 调用失败: {e}")
            return None

    def get_model_name(self, task_type: str = 'generation') -> str:
        """获取任务对应的模型名称"""
        provider = self.get_provider_for_task(task_type)
        return self.providers.get(provider, {}).get('model', 'unknown')

    def get_provider_info(self) -> Dict:
        """获取所有provider信息"""
        return {name: config.get('name', name) for name, config in self.providers.items()}
