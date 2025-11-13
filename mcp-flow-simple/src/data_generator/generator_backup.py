"""数据生成器 - 4步骤流程"""
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
        num = self.generation_config.get('instruction_per_tool', 5)
        prompt = f"为工具生成{num}条指令:\n工具: {tool.get('name')}\n描述: {tool.get('description')}"
        try:
            response = self.client.chat_completion([{"role": "user", "content": prompt}], 'generation')
            if response:
                import re
                lines = [l.strip() for l in response.split('\n') if l.strip()]
                return [re.sub(r'^\d+[.、]\s*', '', l) for l in lines][:num]
        except Exception as e:
            logger.error(f"生成失败: {e}")
        return []

    def slot_fill_revision(self, instruction: str, tool: Dict) -> str:
        prompt = f"使指令更具体: {instruction}\n只返回修订后的指令:"
        try:
            response = self.client.chat_completion([{"role": "user", "content": prompt}], 'generation')
            return response.strip() if response else instruction
        except:
            return instruction

    def wizardlm_evolution(self, instruction: str, depth: int = 1) -> str:
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
        prompt = f"生成JSON函数调用:\n指令: {instruction}\n工具: {tool.get('name')}\n只返回JSON:"
        try:
            response = self.client.chat_completion([{"role": "user", "content": prompt}], 'function_call', 0.3)
            if not response:
                return None
            import re
            match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if not match:
                return None
            function_call = json.loads(match.group())
            tool_resp = json.dumps({"status": "success", "data": function_call.get('arguments', {})}, ensure_ascii=False)
            final_prompt = f"简洁回复:\n指令: {instruction}\n结果: {tool_resp}"
            final = self.client.chat_completion([{"role": "user", "content": final_prompt}], 'generation')
            return {
                "instruction": instruction,
                "server_info": {"server_name": server_info.get('name', ''), "server_description": server_info.get('description', '')},
                "tool_info": {"tool_name": tool.get('name', ''), "tool_description": tool.get('description', ''), "input_schema": tool.get('inputSchema', {})},
                "function_call": function_call,
                "tool_response": {"content": tool_resp},
                "final_response": final.strip() if final else "操作完成"
            }
        except Exception as e:
            logger.error(f"生成失败: {e}")
            return None
