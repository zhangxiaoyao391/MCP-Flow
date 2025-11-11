"""
小规模测试脚本 - 测试数据生成质量
"""
import json
import yaml
import logging
from pathlib import Path
import sys

# 添加src到路径
sys.path.append(str(Path(__file__).parent / 'src'))

from data_generator.generator import DataGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_tools():
    """创建测试工具数据 - 扩展到20个工具"""
    test_tools = {
        "test_server_1": {
            "server_config": {
                "name": "Weather Server",
                "description": "A server that provides weather information and forecasts"
            },
            "tools": [
                {
                    "name": "get_current_weather",
                    "description": "Get current weather information for a specific location",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "City name or coordinates"},
                            "units": {"type": "string", "enum": ["celsius", "fahrenheit"], "description": "Temperature unit"}
                        },
                        "required": ["location"]
                    }
                },
                {
                    "name": "get_forecast",
                    "description": "Get weather forecast for the next few days",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "City name"},
                            "days": {"type": "integer", "description": "Number of days (1-7)"}
                        },
                        "required": ["location", "days"]
                    }
                }
            ]
        },
        "test_server_2": {
            "server_config": {"name": "Calculator Server", "description": "Mathematical operations server"},
            "tools": [
                {
                    "name": "calculate",
                    "description": "Perform basic mathematical operations",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
                            "a": {"type": "number", "description": "First operand"},
                            "b": {"type": "number", "description": "Second operand"}
                        },
                        "required": ["operation", "a", "b"]
                    }
                }
            ]
        },
        "test_server_3": {
            "server_config": {"name": "File Operations Server"},
            "tools": [
                {
                    "name": "read_file",
                    "description": "Read contents from a file",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Path to the file"},
                            "encoding": {"type": "string", "enum": ["utf-8", "ascii"], "description": "File encoding"}
                        },
                        "required": ["file_path"]
                    }
                },
                {
                    "name": "write_file",
                    "description": "Write content to a file",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string"},
                            "content": {"type": "string"},
                            "mode": {"type": "string", "enum": ["overwrite", "append"]}
                        },
                        "required": ["file_path", "content"]
                    }
                }
            ]
        },
        "test_server_4": {
            "server_config": {"name": "Database Server"},
            "tools": [
                {
                    "name": "query_database",
                    "description": "Execute SQL query on database",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "SQL query"},
                            "database": {"type": "string", "description": "Database name"}
                        },
                        "required": ["query", "database"]
                    }
                },
                {
                    "name": "insert_record",
                    "description": "Insert a new record into database",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "table": {"type": "string"},
                            "data": {"type": "object"}
                        },
                        "required": ["table", "data"]
                    }
                }
            ]
        },
        "test_server_5": {
            "server_config": {"name": "Email Server"},
            "tools": [
                {
                    "name": "send_email",
                    "description": "Send an email message",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "to": {"type": "string", "description": "Recipient email"},
                            "subject": {"type": "string"},
                            "body": {"type": "string"}
                        },
                        "required": ["to", "subject", "body"]
                    }
                }
            ]
        },
        "test_server_6": {
            "server_config": {"name": "Time Server"},
            "tools": [
                {
                    "name": "get_current_time",
                    "description": "Get current time in specific timezone",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "timezone": {"type": "string", "description": "Timezone identifier"},
                            "format": {"type": "string", "enum": ["12h", "24h"]}
                        },
                        "required": ["timezone"]
                    }
                },
                {
                    "name": "convert_timezone",
                    "description": "Convert time between timezones",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "time": {"type": "string"},
                            "from_tz": {"type": "string"},
                            "to_tz": {"type": "string"}
                        },
                        "required": ["time", "from_tz", "to_tz"]
                    }
                }
            ]
        },
        "test_server_7": {
            "server_config": {"name": "Translation Server"},
            "tools": [
                {
                    "name": "translate_text",
                    "description": "Translate text between languages",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "source_lang": {"type": "string"},
                            "target_lang": {"type": "string"}
                        },
                        "required": ["text", "target_lang"]
                    }
                },
                {
                    "name": "detect_language",
                    "description": "Detect the language of text",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"}
                        },
                        "required": ["text"]
                    }
                }
            ]
        },
        "test_server_8": {
            "server_config": {"name": "Image Processing Server"},
            "tools": [
                {
                    "name": "resize_image",
                    "description": "Resize an image to specified dimensions",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "image_path": {"type": "string"},
                            "width": {"type": "integer"},
                            "height": {"type": "integer"}
                        },
                        "required": ["image_path", "width", "height"]
                    }
                }
            ]
        },
        "test_server_9": {
            "server_config": {"name": "Text Analysis Server"},
            "tools": [
                {
                    "name": "summarize_text",
                    "description": "Generate a summary of text",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "max_length": {"type": "integer", "description": "Maximum summary length"}
                        },
                        "required": ["text"]
                    }
                },
                {
                    "name": "extract_keywords",
                    "description": "Extract keywords from text",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "count": {"type": "integer", "description": "Number of keywords"}
                        },
                        "required": ["text"]
                    }
                }
            ]
        },
        "test_server_10": {
            "server_config": {"name": "HTTP Client Server"},
            "tools": [
                {
                    "name": "make_http_request",
                    "description": "Make HTTP request to an API",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string"},
                            "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]},
                            "headers": {"type": "object"},
                            "body": {"type": "string"}
                        },
                        "required": ["url", "method"]
                    }
                }
            ]
        }
    }
    return test_tools


def test_data_generation():
    """测试数据生成"""
    logger.info("=" * 60)
    logger.info("开始小规模数据生成测试")
    logger.info("=" * 60)

    # 加载配置
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 创建生成器
    generator = DataGenerator(config)

    # 创建测试工具
    test_tools = create_test_tools()

    all_samples = []

    # 对每个服务器的每个工具生成数据
    for server_id, server_data in test_tools.items():
        server_info = server_data['server_config']
        tools = server_data['tools']

        logger.info(f"\n{'='*60}")
        logger.info(f"处理服务器: {server_info['name']}")
        logger.info(f"{'='*60}")

        for tool in tools:
            logger.info(f"\n工具: {tool['name']}")
            logger.info(f"描述: {tool['description']}")
            logger.info("-" * 60)

            try:
                # 1. Few-shot生成指令
                logger.info("步骤1: Few-shot生成指令...")
                instructions = generator.generate_instructions(tool, server_info)
                logger.info(f"✅ 生成了 {len(instructions)} 条原始指令")

                for idx, instruction in enumerate(instructions, 1):
                    logger.info(f"\n📝 指令 {idx} (原始):")
                    logger.info(f"   {instruction}")

                    # 2. Slot-fill修订
                    logger.info(f"   步骤2: Slot-fill修订...")
                    revised_instruction = generator.slot_fill_revision(instruction, tool)
                    logger.info(f"   ✅ 修订后:")
                    logger.info(f"   {revised_instruction}")

                    # 3. WizardLM Evolution
                    logger.info(f"   步骤3: WizardLM Evolution...")
                    evolved_instruction = generator.wizardlm_evolution(
                        revised_instruction,
                        depth=config['data_generation'].get('evolution_depth', 1)
                    )
                    logger.info(f"   ✅ Evolution后:")
                    logger.info(f"   {evolved_instruction}")

                    # 4. 生成函数调用
                    logger.info(f"   步骤4: 生成函数调用...")
                    function_call = generator.generate_function_call(
                        evolved_instruction,
                        tool,
                        server_info
                    )

                    if function_call:
                        logger.info(f"   ✅ 函数调用:")
                        logger.info(f"   {json.dumps(function_call, indent=4, ensure_ascii=False)}")

                        # 保存样本
                        sample = {
                            'server_id': server_id,
                            'server_name': server_info['name'],
                            'tool_name': tool['name'],
                            'tool_description': tool['description'],
                            'instruction_original': instruction,
                            'instruction_revised': revised_instruction,
                            'instruction_evolved': evolved_instruction,
                            'function_call': function_call
                        }
                        all_samples.append(sample)
                        logger.info(f"   ✅ 样本生成成功！")
                    else:
                        logger.warning(f"   ❌ 函数调用生成失败")

                    logger.info("-" * 60)

            except Exception as e:
                logger.error(f"❌ 处理工具 {tool['name']} 时出错: {e}", exc_info=True)
                continue

    # 保存结果
    logger.info(f"\n{'='*60}")
    logger.info("保存测试结果")
    logger.info(f"{'='*60}")

    output_dir = Path("data/test_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "test_generated_data.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_samples, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ 结果已保存到: {output_file}")
    logger.info(f"📊 共生成 {len(all_samples)} 个样本")

    # 打印统计
    logger.info(f"\n{'='*60}")
    logger.info("生成统计")
    logger.info(f"{'='*60}")
    logger.info(f"服务器数量: {len(test_tools)}")
    logger.info(f"工具总数: {sum(len(s['tools']) for s in test_tools.values())}")
    logger.info(f"成功样本数: {len(all_samples)}")
    logger.info(f"每工具平均样本数: {len(all_samples) / sum(len(s['tools']) for s in test_tools.values()):.1f}")

    # 显示样本质量分析
    logger.info(f"\n{'='*60}")
    logger.info("样本质量分析")
    logger.info(f"{'='*60}")

    for idx, sample in enumerate(all_samples[:3], 1):  # 显示前3个样本
        logger.info(f"\n样本 {idx}:")
        logger.info(f"工具: {sample['tool_name']}")
        logger.info(f"原始指令: {sample['instruction_original']}")
        logger.info(f"最终指令: {sample['instruction_evolved']}")
        logger.info(f"函数调用: {json.dumps(sample['function_call'], ensure_ascii=False)}")

    logger.info(f"\n{'='*60}")
    logger.info("✅ 测试完成！")
    logger.info(f"{'='*60}")

    return all_samples


if __name__ == "__main__":
    try:
        samples = test_data_generation()
        print(f"\n\n✅ 测试成功！生成了 {len(samples)} 个样本")
        print(f"📁 查看详细结果: data/test_output/test_generated_data.json")
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
