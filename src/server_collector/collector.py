"""
MCP Server Collector using Playwright Web Agent
基于论文Section 3.1实现自动化服务器收集
"""
import json
import logging
from typing import List, Dict, Any
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


class MCPServerCollector:
    """自动化MCP服务器收集器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.collected_servers = []
        self.deduplicated_servers = {}

    def collect_from_marketplaces(self) -> List[Dict]:
        """
        从多个marketplace收集服务器配置

        优先尝试从本地mcp_config目录读取，如果不存在则使用网络收集

        Returns:
            List[Dict]: 收集到的服务器配置列表
        """
        # 首先尝试从本地配置读取
        local_servers = self._collect_from_local_configs()
        if local_servers:
            logger.info(f"✅ 从本地配置文件读取到 {len(local_servers)} 个服务器")
            self.collected_servers = local_servers
            return local_servers

        # 如果本地没有配置，使用网络收集
        logger.info("本地配置不存在，使用网络收集...")
        all_servers = []

        for marketplace in self.config['marketplaces']:
            logger.info(f"正在收集 {marketplace['name']} 的服务器...")

            if marketplace['type'] == 'playwright':
                servers = self._collect_with_playwright(marketplace)
            elif marketplace['type'] == 'sdk':
                servers = self._collect_with_sdk(marketplace)
            else:
                logger.warning(f"未知的收集类型: {marketplace['type']}")
                continue

            all_servers.extend(servers)
            logger.info(f"从 {marketplace['name']} 收集到 {len(servers)} 个服务器")

        self.collected_servers = all_servers
        return all_servers

    def _collect_with_playwright(self, marketplace: Dict) -> List[Dict]:
        """
        使用Playwright Agent收集服务器

        实现论文中的Algorithm 1: Automated MCP Server Collection

        Args:
            marketplace: marketplace配置

        Returns:
            List[Dict]: 服务器配置列表
        """
        # TODO: 实现Playwright自动化收集
        # 步骤:
        # 1. 初始化Playwright web agent
        # 2. 导航到marketplace主页
        # 3. 提取服务器列表 (使用论文中的Prompt 1)
        # 4. 对每个服务器:
        #    a. 导航到详情页
        #    b. 点击JSON按钮
        #    c. 提取配置 (使用论文中的Prompt 2)
        # 5. 返回收集的配置

        logger.warning("Playwright收集功能待实现")
        return []

    def _collect_with_sdk(self, marketplace: Dict) -> List[Dict]:
        """
        使用Python SDK收集服务器 (用于PulseMCP/DeepNLP)

        Args:
            marketplace: marketplace配置

        Returns:
            List[Dict]: 服务器配置列表
        """
        # TODO: 实现SDK收集
        # 参考论文Section D.1中的代码示例
        logger.warning("SDK收集功能待实现")
        return []

    def _collect_from_local_configs(self) -> List[Dict]:
        """
        从本地mcp_config目录读取预先准备好的配置文件

        Returns:
            List[Dict]: 服务器配置列表
        """
        servers = []
        mcp_config_dir = Path("mcp_config")

        if not mcp_config_dir.exists():
            logger.info("mcp_config目录不存在")
            return []

        # 遍历smithery和glama子目录
        for marketplace_dir in mcp_config_dir.iterdir():
            if not marketplace_dir.is_dir():
                continue

            marketplace_name = marketplace_dir.name
            config_files = list(marketplace_dir.glob("*.json"))

            logger.info(f"正在读取 {marketplace_name} 的配置文件... (共{len(config_files)}个)")

            for config_file in config_files:
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)

                    # 提取服务器配置
                    if 'mcpServers' in config_data:
                        for server_name, server_config in config_data['mcpServers'].items():
                            server_info = {
                                'name': server_name,
                                'display_name': config_file.stem,  # 使用文件名作为显示名称
                                'marketplace': marketplace_name,
                                'command': server_config.get('command', ''),
                                'args': server_config.get('args', []),
                                'config_file': str(config_file)
                            }
                            servers.append(server_info)

                except Exception as e:
                    logger.warning(f"读取配置文件 {config_file} 失败: {e}")
                    continue

            logger.info(f"从 {marketplace_name} 读取到 {len([s for s in servers if s['marketplace'] == marketplace_name])} 个服务器")

        return servers

    def deduplicate_servers(self) -> Dict[str, Dict]:
        """
        服务器去重

        基于论文Section 3.1: "如果两个服务器共享相同的工具描述列表,将它们视为同一实体"
        对于本地配置，使用服务器名称和marketplace组合作为唯一标识

        Returns:
            Dict[str, Dict]: 去重后的服务器字典 {server_id: server_config}
        """
        for server in self.collected_servers:
            # 对于本地配置，使用名称和marketplace组合作为唯一标识
            if 'marketplace' in server:
                server_id = f"{server['marketplace']}_{server['name']}"
            else:
                # 如果是网络收集的，使用工具描述列表的哈希
                tool_descriptions = self._extract_tool_descriptions(server)
                server_id = hashlib.md5(
                    json.dumps(sorted(tool_descriptions), ensure_ascii=False).encode()
                ).hexdigest()

            # 如果已存在相同的服务器,跳过
            if server_id not in self.deduplicated_servers:
                self.deduplicated_servers[server_id] = server
                logger.debug(f"添加服务器: {server.get('display_name', server.get('name', 'unknown'))}")
            else:
                logger.debug(f"跳过重复服务器: {server.get('display_name', server.get('name', 'unknown'))}")

        logger.info(f"去重完成: {len(self.collected_servers)} → {len(self.deduplicated_servers)}")
        return self.deduplicated_servers

    def _extract_tool_descriptions(self, server: Dict) -> List[str]:
        """提取服务器的工具描述列表"""
        # TODO: 从服务器配置中提取工具描述
        return []

    def save_servers(self, output_path: str):
        """保存收集的服务器配置"""
        output_file = Path(output_path) / "collected_servers.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.deduplicated_servers, f, ensure_ascii=False, indent=2)

        logger.info(f"服务器配置已保存到: {output_file}")


if __name__ == "__main__":
    # 测试代码
    import yaml

    logging.basicConfig(level=logging.INFO)

    with open("config.yaml", 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    collector = MCPServerCollector(config)
    servers = collector.collect_from_marketplaces()
    deduplicated = collector.deduplicate_servers()
    collector.save_servers(config['output_paths']['servers'])
