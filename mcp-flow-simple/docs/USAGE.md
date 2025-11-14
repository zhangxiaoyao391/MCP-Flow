# MCP-Flow 简化版使用文档

## 项目概述

MCP-Flow简化版是一个自动化生成高质量Function Calling训练数据的Pipeline。

**核心功能:**
- 数据生成(4步骤): Few-shot → Slot-fill → Evolution → Function Call
- 数据过滤(3步骤): 工具验证 → 质量评分 → 轨迹验证

## 项目结构

```
mcp-flow-simple/
├── src/                          # 源代码
│   ├── main.py                   # 主入口
│   ├── data_generator/           # 数据生成模块
│   │   ├── __init__.py
│   │   └── generator.py          # DataGenerator类(4步骤)
│   ├── data_filter/              # 数据过滤模块
│   │   ├── __init__.py
│   │   └── filter.py             # DataFilter类(3步骤,无嵌入)
│   └── utils/                    # 工具模块
│       ├── __init__.py
│       └── llm_client.py         # LLM统一接口
│
├── wizard_utils/                 # WizardLM Evolution工具
│   ├── breadth.py                # 广度扩展
│   └── depth.py                  # 深度扩展
│
├── config/                       # 配置目录
│   └── config.example.yaml       # 配置模板
│
├── data/                         # 输出数据
│   ├── function_call/            # 生成的原始数据
│   └── filtered/                 # 过滤后的高质量数据
│
├── requirements.txt              # Python依赖
├── README.md                     # 快速指南
└── USAGE.md                      # 本文档
```

## 快速开始

### 1. 环境准备

**要求:** Python 3.10+

```bash
cd mcp-flow-simple
pip install -r requirements.txt
```

### 2. 配置API

```bash
cp config/config.example.yaml config/config.yaml
```

编辑 `config/config.yaml`,填写API密钥:

```yaml
llm_providers:
  primary:
    api_key: "YOUR_API_KEY_HERE"      # 填写你的API密钥
    base_url: "YOUR_BASE_URL_HERE"    # 填写API地址
```

### 3. 准备工具数据

确保有工具JSON文件,格式如下:

```json
{
  "server_info": {
    "name": "服务器名称",
    "description": "服务器描述"
  },
  "tools": [
    {
      "name": "工具名",
      "description": "工具描述",
      "inputSchema": {...}
    }
  ]
}
```

### 4. 运行Pipeline

```bash
cd src
python main.py --tools ../mcp_tools_full_20251113_120436.json
```

## 数据生成流程详解

### 阶段1: 数据生成

#### 步骤1: Few-shot生成
为每个工具生成N条基础指令(默认5条)

**示例:**
- 输入: 工具定义 `get_weather`
- 输出: ["查询北京天气", "获取上海温度", ...]

#### 步骤2: Slot-fill修订
填充参数槽位,增加具体性

**示例:**
- 输入: "查询天气"
- 输出: "查询北京市朝阳区的天气"

#### 步骤3: WizardLM Evolution
增加指令复杂度(默认深度=1)

**示例:**
- 输入: "查询北京市朝阳区的天气"
- 输出: "查询北京市朝阳区未来3天的天气趋势并推荐户外活动"

#### 步骤4: Function Call生成
生成完整样本(符合模板格式)

**输出格式:**
```json
{
  "instruction": "用户指令",
  "server_info": {
    "server_name": "服务器名",
    "server_description": "描述"
  },
  "tool_info": {
    "tool_name": "工具名",
    "tool_description": "描述",
    "input_schema": {...}
  },
  "function_call": {
    "name": "工具名",
    "arguments": {...}
  },
  "tool_response": {
    "content": "模拟响应"
  },
  "final_response": "最终回复"
}
```

### 阶段2: 数据过滤

#### 过滤1: 工具调用验证
验证function_call.name与tool_name一致

#### 过滤2: 质量评分
LLM评分(0-10),淘汰低于阈值的样本(默认6分)

#### 过滤3: 轨迹验证
检查样本完整性(必需字段、回复长度等)

## 配置说明

### 数据生成配置

```yaml
data_generation:
  instruction_per_tool: 5    # 每个工具生成指令数
  evolution_depth: 1         # Evolution深度(1-3)
  temperature: 0.7           # 生成温度
  max_tokens: 4096           # 最大token数
```

**参数说明:**
- `instruction_per_tool`: 数值越大,数据越多,API成本越高
- `evolution_depth`: 1已足够(论文推荐),过高会增加成本
- `temperature`: 0.7平衡创造性和稳定性

### 数据过滤配置

```yaml
data_filtering:
  quality_score_threshold: 6  # 质量评分阈值(0-10)
```

**说明:**
- 阈值越高,数据质量越好,但通过率越低
- 推荐值: 6(平衡质量和数量)

## 输出数据

### 文件命名

- 生成数据: `data/function_call/generated_YYYYMMDD_HHMMSS.json`
- 过滤数据: `data/filtered/filtered_YYYYMMDD_HHMMSS.json`

### 数据统计

运行完成后会显示:

```
============================
✓ 完成! 耗时: 0:05:32
✓ 工具: 14, 生成: 70, 通过: 68
============================
```

## 常见问题

### Q: API调用失败?

**检查:**
1. API密钥是否正确
2. base_url是否可访问
3. 账户余额是否充足

**解决:**
- 配置fallback API
- 查看日志获取详细错误

### Q: 生成质量不高?

**优化:**
1. 提高 `quality_score_threshold` (6→7)
2. 增加 `evolution_depth` (1→2)
3. 降低 `temperature` (0.7→0.5)

### Q: 运行太慢?

**加速:**
1. 减少 `instruction_per_tool` (5→3)
2. 降低 `evolution_depth` (2→1)
3. 使用更快的LLM模型

### Q: 内存不足?

**解决:**
- 分批处理工具(拆分JSON文件)
- 减少单次处理的工具数量

## 技术特点

### 优势

1. **简单**: 无GPU要求,依赖少
2. **快速**: 2阶段流程,运行快
3. **灵活**: 配置简单,易扩展
4. **高质量**: 保留完整4步骤生成+3重过滤

### 对比原项目

| 特性 | 原项目 | 简化版 |
|------|--------|--------|
| 阶段数 | 5 | 2 |
| GPU需求 | 是 | 否 |
| 依赖数 | 28 | 8 |
| 代码行数 | ~5391 | ~800 |


- 📄 论文: https://arxiv.org/abs/2510.24284
