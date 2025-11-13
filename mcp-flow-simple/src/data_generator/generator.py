"""数据生成器 - 4步骤流程(优化版)"""
import logging
import json
import random
import sys
import os
from typing import Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
logger = logging.getLogger(__name__)

class DataGenerator:
    def __init__(self, config: Dict):
        from utils.llm_client import LLMClient
        self.config = config
        self.client = LLMClient(config)
        self.generation_config = config.get('data_generation', {})

    def generate_instructions(self, tool: Dict, server_info: Dict) -> List[str]:
        """步骤1: Few-shot指令生成 - 添加详细上下文"""
        num = self.generation_config.get('instruction_per_tool', 5)
        schema = tool.get('inputSchema', {})
        properties = schema.get('properties', {})
        required = schema.get('required', [])

        prompt = f"""为以下API工具生成{num}条自然语言用户指令。

工具名称: {tool.get('name')}
工具描述: {tool.get('description')}
参数说明: {json.dumps(properties, ensure_ascii=False, indent=2)}
必需参数: {', '.join(required)}

要求:
1. 指令应该是用户的自然语言查询
2. 指令应该明确对应该工具的功能
3. 每条指令一行,用数字编号

只返回{num}条指令,格式如下:
1. 指令1
2. 指令2
..."""

        try:
            response = self.client.chat_completion([{"role": "user", "content": prompt}], 'generation')
            if response:
                import re
                lines = [l.strip() for l in response.split('\n') if l.strip()]
                return [re.sub(r'^\d+[.、]\s*', '', l) for l in lines if re.match(r'^\d+[.、]', l)][:num]
        except Exception as e:
            logger.error(f"生成失败: {e}")
        return []

    def slot_fill_revision(self, instruction: str, tool: Dict) -> str:
        """步骤2: Slot-fill修订 - 使指令更具体"""
        prompt = f"使指令更具体: {instruction}\n只返回修订后的指令:"
        try:
            response = self.client.chat_completion([{"role": "user", "content": prompt}], 'generation')
            return response.strip() if response else instruction
        except:
            return instruction

    def wizardlm_evolution(self, instruction: str, depth: int = 1) -> str:
        """步骤3: WizardLM演化 - 增加复杂度"""
        current = instruction
        for i in range(depth):
            prompt = f"Rewrite to be more complex:\n{current}\nOnly return rewritten:"
            try:
                response = self.client.chat_completion([{"role": "user", "content": prompt}], 'generation')
                if response:
                    current = response.strip()
            except:
                break
        return current

    def generate_function_call(self, instruction: str, tool: Dict, server_info: Dict) -> Optional[Dict]:
        """步骤4: 函数调用生成 - 添加完整上下文和格式说明"""
        schema = tool.get('inputSchema', {})
        properties = schema.get('properties', {})
        required = schema.get('required', [])

        prompt = f"""根据用户指令生成函数调用JSON。

用户指令: {instruction}

工具信息:
- 名称: {tool.get('name')}
- 描述: {tool.get('description')}
- 参数定义: {json.dumps(properties, ensure_ascii=False, indent=2)}
- 必需参数: {', '.join(required)}

返回格式(纯JSON,不要```包裹):
{{
  "name": "{tool.get('name')}",
  "arguments": {{参数字典}}
}}

只返回JSON:"""

        try:
            response = self.client.chat_completion([{"role": "user", "content": prompt}], 'function_call', 0.3)
            if not response:
                return None

            import re
            # 移除可能的```json包裹
            clean_response = re.sub(r'```json?\s*|\s*```', '', response.strip())
            # 匹配嵌套JSON或简单JSON
            match = re.search(r'\{[^{}]*\{[^}]*\}[^{}]*\}|\{[^{}]+\}', clean_response, re.DOTALL)
            if not match:
                logger.debug(f"无法提取JSON: {response[:100]}")
                return None

            function_call = json.loads(match.group())

            # 验证必需字段
            if 'name' not in function_call or 'arguments' not in function_call:
                logger.debug(f"JSON缺少必需字段: name或arguments")
                return None

            # 生成模拟工具响应
            tool_resp = json.dumps({
                "status": "success",
                "data": function_call.get('arguments', {})
            }, ensure_ascii=False)

            # 生成最终用户友好响应
            final_prompt = f"""根据指令和执行结果,生成一句简洁的回复。

用户指令: {instruction}
执行结果: {tool_resp}

只返回回复内容(不要额外解释):"""

            final = self.client.chat_completion([{"role": "user", "content": final_prompt}], 'generation')

            return {
                "instruction": instruction,
                "server_info": {
                    "server_name": server_info.get('name', ''),
                    "server_description": server_info.get('description', '')
                },
                "tool_info": {
                    "tool_name": tool.get('name', ''),
                    "tool_description": tool.get('description', ''),
                    "input_schema": tool.get('inputSchema', {})
                },
                "function_call": function_call,
                "tool_response": {"content": tool_resp},
                "final_response": final.strip() if final else "操作完成"
            }
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"生成失败: {e}")
            return None
