"""
数据格式转换脚本
将MCP-Flow生成的训练数据转换为LLaMA-Factory标准格式

标准格式:
{
    "instruction": "用户指令",
    "input": "输入上下文(可选)",
    "output": "期望输出"
}
"""
import json
import argparse
from pathlib import Path
from typing import List, Dict


def convert_mcp_to_llama_factory(mcp_data: List[Dict]) -> List[Dict]:
    """
    转换MCP-Flow数据为LLaMA-Factory格式

    Args:
        mcp_data: MCP-Flow生成的数据列表

    Returns:
        LLaMA-Factory格式的数据列表
    """
    llama_factory_data = []

    for item in mcp_data:
        # 构建工具上下文信息
        tool_context = f"""工具名称: {item['tool_info']['tool_name']}
工具描述: {item['tool_info']['tool_description']}
输入参数: {json.dumps(item['tool_info']['input_schema'], ensure_ascii=False, indent=2)}

服务器: {item['server_info']['server_name']}
服务器描述: {item['server_info']['server_description']}"""

        # 构建期望的函数调用输出
        function_call_output = json.dumps(item['function_call'], ensure_ascii=False, indent=2)

        # 转换为LLaMA-Factory格式
        llama_item = {
            "instruction": item['instruction'],
            "input": tool_context,
            "output": function_call_output
        }

        llama_factory_data.append(llama_item)

    return llama_factory_data


def main():
    parser = argparse.ArgumentParser(description='转换MCP-Flow数据为LLaMA-Factory格式')
    parser.add_argument('--input', '-i', required=True, help='输入的MCP-Flow数据文件路径')
    parser.add_argument('--output', '-o', required=True, help='输出的LLaMA-Factory数据文件路径')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细信息')

    args = parser.parse_args()

    # 读取输入数据
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ 错误: 输入文件不存在: {input_path}")
        return

    print(f"📖 读取输入文件: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        mcp_data = json.load(f)

    print(f"✓ 加载了 {len(mcp_data)} 条数据")

    # 转换数据
    print("🔄 转换数据格式...")
    llama_factory_data = convert_mcp_to_llama_factory(mcp_data)

    # 保存输出数据
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"💾 保存输出文件: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(llama_factory_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 转换完成! 共 {len(llama_factory_data)} 条数据")

    # 显示样本
    if args.verbose and llama_factory_data:
        print("\n📋 第一条数据样本:")
        print(json.dumps(llama_factory_data[0], ensure_ascii=False, indent=2)[:500] + "...")


if __name__ == '__main__':
    main()
