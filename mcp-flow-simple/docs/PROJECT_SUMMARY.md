# MCP-Flow 简化版 - 项目总结

## 项目信息

- **项目名称**: MCP-Flow 简化版
- **创建日期**: 2025-11-13
- **版本**: 1.0
- **目的**: 独立的、简化的Function Calling数据生成工具

## 项目结构

```
mcp-flow-simple/
│
├── src/                               # 源代码目录
│   ├── main.py                        # 主入口 (约150行)
│   ├── data_generator/
│   │   ├── __init__.py
│   │   └── generator.py               # 数据生成器 (约120行)
│   ├── data_filter/
│   │   ├── __init__.py
│   │   └── filter.py                  # 数据过滤器 (约80行)
│   └── utils/
│       ├── __init__.py
│       └── llm_client.py              # LLM客户端 (约150行)
│
├── wizard_utils/                      # WizardLM工具(复制自原项目)
│   ├── breadth.py
│   └── depth.py
│
├── config/
│   └── config.example.yaml            # 配置模板
│
├── data/                              # 输出目录
│   ├── function_call/                 # 原始生成数据
│   └── filtered/                      # 过滤后数据
│
├── requirements.txt                   # 依赖清单 (8个)
├── README.md                          # 快速指南
├── USAGE.md                           # 详细使用文档
└── PROJECT_SUMMARY.md                 # 本文档
```

**代码统计:**
- 总代码行数: ~500行
- 模块数: 4个
- 依赖数: 8个

## 核心功能

### 1. 数据生成 (src/data_generator/generator.py)

**DataGenerator类 - 完整的4步骤流程:**

1. **generate_instructions()** - Few-shot生成
   - 为每个工具生成N条基础指令
   - 使用LLM few-shot学习

2. **slot_fill_revision()** - Slot-fill修订
   - 填充参数槽位
   - 增加指令具体性

3. **wizardlm_evolution()** - WizardLM Evolution
   - 增加指令复杂度
   - 支持可配置深度

4. **generate_function_call()** - Function Call生成
   - 生成完整样本
   - **严格符合模板格式**:
     * instruction
     * server_info
     * tool_info
     * function_call
     * tool_response
     * final_response

### 2. 数据过滤 (src/data_filter/filter.py)

**DataFilter类 - 3重过滤机制:**

1. **filter_by_tool_invocation()** - 工具调用验证
   - 验证tool_name与call_name一致性

2. **filter_by_quality_score()** - 质量评分
   - LLM打分(0-10)
   - 淘汰低于阈值的样本

3. **filter_trajectory()** - 轨迹验证
   - 检查必需字段完整性
   - 验证回复有效性

**注意**: 已移除嵌入相似度过滤,无需GPU

### 3. LLM统一接口 (src/utils/llm_client.py)

**LLMClient类:**
- 支持多provider配置
- 自动fallback机制
- OpenAI兼容接口
- 统一的调用方法

### 4. 主流程编排 (src/main.py)

**MCPFlowPipeline类:**
- load_tools() - 加载JSON
- generate_data() - 数据生成
- filter_data() - 数据过滤
- run() - 完整流程

## 使用方法

### 基本用法

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置API
cp config/config.example.yaml config/config.yaml
# 编辑config.yaml

# 3. 运行
cd src
python main.py --tools ../mcp_tools_full_20251113_120436.json
```

### 输入要求

**工具JSON格式:**
```json
{
  "server_info": {
    "name": "服务器名",
    "description": "描述"
  },
  "tools": [
    {
      "name": "工具名",
      "description": "描述",
      "inputSchema": {...}
    }
  ]
}
```

### 输出格式

**符合模板的样本格式:**
```json
{
  "instruction": "查询北京现在的温度是多少摄氏度?",
  "server_info": {
    "server_name": "Weather API Server",
    "server_description": "提供全球天气查询服务"
  },
  "tool_info": {
    "tool_name": "get_current_weather",
    "tool_description": "获取指定位置的当前天气信息",
    "input_schema": {...}
  },
  "function_call": {
    "name": "get_current_weather",
    "arguments": {
      "location": "北京",
      "unit": "celsius"
    }
  },
  "tool_response": {
    "content": "{\"temperature\": 15, \"condition\": \"晴朗\"}"
  },
  "final_response": "北京现在的温度是15摄氏度,天气晴朗"
}
```

## 配置说明

### config.yaml关键配置

```yaml
# LLM配置
llm_providers:
  primary:                    # 主力API
    api_key: "YOUR_KEY"
    base_url: "YOUR_URL"
  fallback:                   # 备用API
    api_key: "BACKUP_KEY"

# 数据生成
data_generation:
  instruction_per_tool: 5     # 每工具指令数
  evolution_depth: 1          # Evolution深度
  temperature: 0.7            # 生成温度

# 数据过滤
data_filtering:
  quality_score_threshold: 6  # 质量阈值
```

## 技术特点

### 优势

1. **独立性**: 完全独立于原项目,可单独使用
2. **简洁性**: 代码精简,易于理解和修改
3. **实用性**: 保留核心功能,去除冗余
4. **模块化**: 清晰的模块划分,易于扩展
5. **无GPU**: 移除嵌入模型,降低硬件要求

### 保留的核心算法

✅ **完整保留:**
- Few-shot指令生成
- Slot-fill参数修订
- WizardLM Evolution复杂化
- Function Call生成
- 工具调用验证
- LLM质量评分
- 轨迹完整性验证


### 核心代码文件

1. **src/main.py** (150行)
   - MCPFlowPipeline类
   - 主流程编排
   - 命令行接口

2. **src/data_generator/generator.py** (120行)
   - DataGenerator类
   - 4步骤数据生成

3. **src/data_filter/filter.py** (80行)
   - DataFilter类
   - 3步骤数据过滤

4. **src/utils/llm_client.py** (150行)
   - LLMClient类
   - 统一LLM接口

### 配置和文档

5. **config/config.example.yaml**
   - 配置模板

6. **requirements.txt**
   - Python依赖

7. **README.md**
   - 快速开始指南

8. **USAGE.md**
   - 详细使用文档

9. **PROJECT_SUMMARY.md** (本文档)
   - 项目总结

## 快速参考

### 运行命令

```bash

### 目录说明

- `src/` - 源代码
- `config/` - 配置文件
- `data/function_call/` - 生成的原始数据
- `data/filtered/` - 过滤后的高质量数据
- `wizard_utils/` - Evolution工具

### 配置要点

1. 必须配置API密钥
2. 推荐配置fallback API
3. 根据需求调整生成参数
4. 根据质量要求调整过滤阈值

## 注意事项

### 安全

⚠️ **config.yaml包含API密钥,请勿提交到git**

建议:
```bash
echo "config/config.yaml" >> .gitignore
```

### API成本

根据配置估算:
- 每个工具: ~10-15次API调用
- 14个工具: ~140-210次调用
- 建议先用少量工具测试

### 数据质量

影响因素:
1. LLM模型质量
2. 工具描述完整性
3. 过滤阈值设置
4. Evolution深度

## 联系信息

- 📧 Email: 12321254@zju.edu.cn  
- 📄 论文: https://arxiv.org/abs/2510.24284
- 💻 原项目: MCP-Flow

## 许可证

与原MCP-Flow项目相同

---

**创建日期**: 2025-11-13  
**版本**: 1.0  
**状态**: ✅ 已完成
