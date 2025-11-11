"""
快速测试API配置是否正确
"""
import yaml
import logging
import sys
from pathlib import Path

# 添加src到路径
sys.path.append(str(Path(__file__).parent / 'src'))

from utils.llm_client import LLMClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_api_connection():
    """测试API连接"""
    # 加载配置
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 创建LLM客户端
    client = LLMClient(config)

    # 测试primary provider
    logger.info("=" * 50)
    logger.info("测试Primary Provider（Doubao）")
    logger.info("=" * 50)

    messages = [{"role": "user", "content": "你好！请用一句话介绍你自己。"}]

    response = client.chat_completion(
        messages=messages,
        task_type='generation',
        temperature=0.7,
        max_tokens=100
    )

    if response:
        logger.info(f"✅ Primary Provider测试成功！")
        logger.info(f"回复: {response}")
    else:
        logger.error("❌ Primary Provider测试失败！")

    # 测试fallback provider
    logger.info("\n" + "=" * 50)
    logger.info("测试Fallback Provider（OpenAI）")
    logger.info("=" * 50)

    # 临时修改配置使用fallback
    original_task_assignments = config['task_assignments'].copy()
    config['task_assignments']['generation'] = 'fallback'
    client_fallback = LLMClient(config)

    response = client_fallback.chat_completion(
        messages=messages,
        task_type='generation',
        temperature=0.7,
        max_tokens=100
    )

    if response:
        logger.info(f"✅ Fallback Provider测试成功！")
        logger.info(f"回复: {response}")
    else:
        logger.error("❌ Fallback Provider测试失败！")

    # 恢复配置
    config['task_assignments'] = original_task_assignments

    logger.info("\n" + "=" * 50)
    logger.info("API配置测试完成！")
    logger.info("=" * 50)


if __name__ == "__main__":
    try:
        test_api_connection()
    except Exception as e:
        logger.error(f"测试过程中出错: {e}", exc_info=True)
