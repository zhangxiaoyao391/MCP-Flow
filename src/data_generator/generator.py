"""
Data Generation Pipeline
基于论文Section 3.2实现数据生成流程:
Few-shot Generation → Slot-Fill Revision → WizardLM Evolution → Function Call Generation
"""
import json
import logging
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))
from utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


class DataGenerator:
    """数据生成器 - 实现MCP-Flow的核心数据合成pipeline"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = LLMClient(config)  # 使用统一的LLM客户端
        self.generation_config = config.get('data_generation', {})

    def generate_instructions(self, tool_info: Dict[str, Any], server_info: Dict[str, Any]) -> List[str]:
        """
        为指定工具生成指令

        论文Section 3.2 - Few-Shot Generation:
        "对每个工具,模型基于人工策划的示例生成5个不同的指令,
        所有指令都需要使用目标工具"

        Args:
            tool_info: 工具信息 {name, description, input_schema}
            server_info: 服务器信息 {name, description}

        Returns:
            List[str]: 生成的指令列表
        """
        prompt = self._build_few_shot_prompt(tool_info, server_info)

        try:
            # 使用LLMClient进行API调用
            content = self.client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                task_type='generation',
                temperature=self.generation_config.get('temperature', 0.7),
                max_tokens=self.generation_config.get('max_tokens', 4096)
            )

            if not content:
                logger.error("API调用失败，未返回内容")
                return []

            # 解析生成的指令
            instructions = self._parse_instructions(content)

            logger.info(f"为工具 {tool_info['name']} 生成了 {len(instructions)} 条指令")
            return instructions

        except Exception as e:
            logger.error(f"生成指令时出错: {e}")
            return []

    def _build_few_shot_prompt(self, tool_info: Dict, server_info: Dict) -> str:
        """
        构建Few-shot生成的prompt

        参考论文Appendix E.1 - Prompt 3
        """
        num_instructions = self.generation_config.get('instruction_per_tool', 5)

        # 动态生成输出格式
        output_format = "\n".join([f"[Instruction{i+1}] <your generated instruction>" for i in range(num_instructions)])

        prompt = f"""You are given a specific tool from a mcp server. You need to generate an instruction which requires to utilize this tool.
Each instruction needs to use exactly 1 tools belong to the mcp server.

## Input
- **MCP Server information**:
[MCP Server Name] {server_info.get('name', '')}
[MCP Server Description] {server_info.get('description', '')}

- **Tool information**:
[Tool Name] {tool_info.get('name', '')}
[Tool Description] {tool_info.get('description', '')}
[Tool Schema] {json.dumps(tool_info.get('input_schema', {}), indent=2)}

## Requirement
The instruction should not directly include the name of the mcp server or the name of the tools.
The instruction must not look similar to the tool description.
Make sure The tool and instruction in your output are aligned.
Generate EXACTLY {num_instructions} instruction candidates - no more, no less.

## Output Format
{output_format}
"""
        return prompt

    def _parse_instructions(self, content: str) -> List[str]:
        """从模型输出中解析指令"""
        instructions = []
        pattern = r'\[Instruction\d+\]\s*(.+?)(?=\[Instruction\d+\]|$)'
        matches = re.findall(pattern, content, re.DOTALL)

        # 获取配置的指令数量
        max_instructions = self.generation_config.get('instruction_per_tool', 5)

        for match in matches:
            instruction = match.strip()
            if instruction:
                instructions.append(instruction)

            # 只取前N条指令，防止LLM超额生成
            if len(instructions) >= max_instructions:
                break

        return instructions

    def slot_fill_revision(self, instruction: str, tool_info: Dict, env_context: Dict = None) -> str:
        """
        Slot-fill修订 - 填充缺失的必需参数

        论文Section 3.2: "如果原始查询中未提供槽位,则自动生成一个有效值。
        然后修订查询以包含这些新参数以保持流畅性"

        Args:
            instruction: 原始指令
            tool_info: 工具信息
            env_context: 环境上下文(可选)

        Returns:
            str: 修订后的指令
        """
        prompt = self._build_slot_fill_prompt(instruction, tool_info, env_context or {})

        try:
            # 使用LLMClient
            content = self.client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                task_type='generation',
                temperature=0.7
            )

            if not content:
                logger.warning("Slot-fill API调用失败，使用原始指令")
                return instruction

            revised_instruction = content.strip()
            logger.debug(f"Slot-fill修订完成: {instruction[:50]}... → {revised_instruction[:50]}...")
            return revised_instruction

        except Exception as e:
            logger.error(f"Slot-fill修订时出错: {e}")
            return instruction

    def _build_slot_fill_prompt(self, instruction: str, tool_info: Dict, env_context: Dict) -> str:
        """
        构建Slot-fill修订的prompt

        参考论文Appendix E.1 - Prompt 4
        """
        return f"""You are an expert at identifying missing but necessary details.
You will be provided with a tool's parameters and a user query. Your task is to supplement any missing information required by the tool in the user query.

If the query lacks required details, retrieve them from the provided environmental context. Then, revise the user query by adding the appropriate missing details.
Ensure that your revisions are realistic and reasonable.

## Requirements
1. Be realistic and authentic, stick to the given environmental context if given.
2. For not included details in the environmental context, like place, date and institutions, etc, try to use real-world names.

### Input
- **Tool information**:
[Tool Name] {tool_info.get('name', '')}
[Tool Description] {tool_info.get('description', '')}
[Tool Schema] {json.dumps(tool_info.get('input_schema', {}), indent=2)}

- **User Query**: {instruction}

- **Environmental Context**:
{json.dumps(env_context, indent=2)}

### Output
Return only the revised instruction without any additional explanation.
"""

    def wizardlm_evolution(self, instruction: str, depth: int = 2) -> str:
        """
        WizardLM Evolution - 增加指令复杂度和多样性

        论文Section 3.2: "随机选择一个evolution方向(如具体化或推理),
        设置evolution深度为2以平衡生成成本和输出质量"

        Args:
            instruction: 原始指令
            depth: evolution深度

        Returns:
            str: evolution后的指令
        """
        evolution_methods = [
            "Please add more specific details to make it more complex",
            "Please add reasoning steps to increase complexity",
            "Please replace general concepts with more specific concepts",
            "Please increase the depth and breadth of the inquiry"
        ]

        current_instruction = instruction

        for i in range(depth):
            import random
            method = random.choice(evolution_methods)

            prompt = f"""I want you act as a Prompt Rewriter.
Your objective is to rewrite a given prompt into a more complex version to make those famous AI systems (e.g., chatgpt and GPT4) a bit harder to handle.
But the rewritten prompt must be reasonable and must be understood and responded by humans.

You SHOULD complicate the given prompt using the following method:
{method}

You should try your best not to make the rewritten prompt become verbose, rewritten prompt can only add 10 to 20 words into the given prompt.

#The Given Prompt#:
{current_instruction}

#Rewritten Prompt#:
"""

            try:
                # 使用LLMClient
                content = self.client.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    task_type='generation',
                    temperature=0.7
                )

                if not content:
                    logger.warning(f"Evolution depth {i+1} API调用失败")
                    break

                current_instruction = content.strip()
                logger.debug(f"Evolution depth {i+1}: {current_instruction[:60]}...")

            except Exception as e:
                logger.error(f"Evolution时出错: {e}")
                break

        return current_instruction

    def generate_function_call(self, instruction: str, tool_info: Dict, server_info: Dict) -> Optional[Dict]:
        """
        生成函数调用

        论文Section 3.2: "给定ground-truth工具、其输入模式和相应的指令,
        我们提示GPT-4o生成形式化的函数调用"

        Args:
            instruction: 指令
            tool_info: 工具信息
            server_info: 服务器信息

        Returns:
            Optional[Dict]: 函数调用 {name: str, arguments: Dict}
        """
        prompt = f"""You are an expert at generating MCP function calls.

Given an instruction and tool information, generate a properly formatted function call.

## Input
- **Instruction**: {instruction}

- **MCP Server**: {server_info.get('name', '')}

- **Tool Information**:
Name: {tool_info.get('name', '')}
Description: {tool_info.get('description', '')}
Input Schema: {json.dumps(tool_info.get('input_schema', {}), indent=2)}

## Output Format
Return ONLY a JSON object with the following structure:
{{
  "name": "<tool_name>",
  "arguments": {{
    "<param1>": "<value1>",
    "<param2>": "<value2>"
  }}
}}
"""

        try:
            # 使用LLMClient
            content = self.client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                task_type='function_call',
                temperature=0.7
            )

            if not content:
                logger.warning("函数调用生成API失败")
                return None

            content = content.strip()

            # 提取JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                function_call = json.loads(json_match.group())
                return function_call
            else:
                logger.warning("无法从响应中提取JSON")
                return None

        except Exception as e:
            logger.error(f"生成函数调用时出错: {e}")
            return None


if __name__ == "__main__":
    # 测试代码
    import yaml

    logging.basicConfig(level=logging.INFO)

    with open("config.yaml", 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    generator = DataGenerator(config)  # 不需要传api_key了

    # 示例工具
    test_tool = {
        "name": "search",
        "description": "Search for information",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }
    }

    test_server = {
        "name": "search-server",
        "description": "A search server"
    }

    # 生成指令
    instructions = generator.generate_instructions(test_tool, test_server)
    print(f"生成的指令: {instructions}")
