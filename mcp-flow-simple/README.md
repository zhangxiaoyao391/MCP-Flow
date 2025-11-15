# MCP-Flow 完整版

自动化生成高质量Function Calling训练数据 - **完整版 (增强过滤)**

## ✨ 完整版新特性

### 🔄 双模型交叉验证
- 使用 **DeepSeek-V3.1** 和 **DeepSeek-V3** 双模型验证工具选择
- 自动生成干扰工具测试样本质量
- 只有两个模型都选错才丢弃样本

### 🛡️ 增强错误检测
- HTTP错误识别 (503, 429, 401, 403等)
- API错误消息检测
- 空响应/截断响应过滤
- 格式错误自动识别

### 🚀 火山方舟免费模型
- **主力**: Doubao-1.5-thinking-pro (数据生成/函数调用)
- **评分**: DeepSeek-V3.1 (质量评分/交叉验证)
- **备用**: DeepSeek-V3 (DeepSeek备用)
- **Fallback**: Doubao-Seed-1.6-lite (通用备用)

---

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置API
cp config/config.example.yaml config/config.yaml
# 编辑config.yaml填写火山方舟API密钥

# 3. 运行 (完整版)
cd src
python main.py --tools ../mcp_tools_full_20251113_120436.json
```

---

## 项目结构

```
mcp-flow-simple/
├── src/
│   ├── main.py                  # 主入口 (完整版)
│   ├── data_generator/          # 数据生成模块
│   ├── data_filter/             # 数据过滤模块 (增强版)
│   └── utils/
│       └── llm_client.py        # LLM客户端 (支持交叉验证)
├── wizard_utils/                # Evolution工具
├── config/                      # 配置目录
├── data/                        # 输出数据
└── README.md
```

---

## 数据生成流程

### 4步骤生成 (保持不变)
1. **Few-shot生成** - 生成基础指令
2. **Slot-fill修订** - 填充参数
3. **WizardLM Evolution** - 增加复杂度
4. **Function Call生成** - 生成完整样本

---

## 数据过滤 (完整版)

### 过滤1: 工具调用可靠性验证 ✅
**简化版**: 仅检查名称匹配
**完整版**: 双模型交叉验证 + 干扰工具测试

```python
# 流程:
1. 为每个样本生成2个随机干扰工具
2. DeepSeek-V3.1 独立选择工具
3. DeepSeek-V3 独立选择工具
4. 至少一个模型选对 → 保留样本
5. 两个模型都选错 → 丢弃样本
```

### 过滤2: 质量评分 ✅
使用 **DeepSeek-V3.1** 进行质量评分 (0-10分)
- 默认阈值: 6分
- 可配置阈值

### 过滤3: 轨迹验证 (增强版) ✅
**简化版**: 仅检查字段完整性
**完整版**: 增强错误检测

```python
检测内容:
✓ 字段完整性
✓ HTTP错误 (503, 429, 401, 403, 500, 502, 504)
✓ API错误 (key invalid, rate limit, timeout等)
✓ 空响应/截断响应
✓ 无效响应格式
```

---

## 配置说明

### 火山方舟模型配置

```yaml
llm_providers:
  primary:
    model: "ep-20251115142804-lg9km"  # Doubao-thinking-pro
    api_key: "YOUR_API_KEY"
    base_url: "https://ark.cn-beijing.volces.com/api/v3"

  deepseek:
    model: "ep-20251115143356-zmsxn"  # DeepSeek-V3.1

  deepseek_backup:
    model: "ep-20251115142837-h8j76"  # DeepSeek-V3

  fallback:
    model: "ep-20251115142650-pjvst"  # Doubao-lite
```

### 完整版过滤配置

```yaml
data_filtering:
  quality_score_threshold: 6

  # 启用交叉验证 (完整版新增)
  enable_cross_validation: true
  cross_validation_mode: "dual_model"
  num_distractor_tools: 2

  # 启用错误检测 (完整版新增)
  enable_error_detection: true
  check_http_errors: true
  check_api_errors: true
```

**切换简化模式**: 将 `enable_cross_validation` 和 `enable_error_detection` 设为 `false`

---

## 运行示例

### 完整版模式 (推荐)
```bash
cd src
python main.py --tools ../mcp_tools_full_20251113_120436.json
```

**预期输出**:
```
============================================================
MCP-Flow 完整版 Pipeline
============================================================
✓ 交叉验证: 启用 (双模型 + 2个干扰工具)
✓ 错误检测: 启用 (HTTP/API错误识别)

阶段1: 数据生成
[1/14] 处理: bussiness_llm_api
...
✓ 生成完成: 70个样本

阶段2: 数据过滤 (完整版)
✓ 交叉验证: 68/70 通过
✓ 质量评分: 65/68 通过
✓ 增强轨迹验证: 63/65 通过

✓ 完成! 耗时: 0:06:25
✓ 工具: 14, 生成: 70, 通过: 63
============================================================
```

---

## 简化版 vs 完整版对比

| 功能 | 简化版 | 完整版 |
|------|--------|--------|
| 数据生成 | ✅ 4步骤流程 | ✅ 4步骤流程 |
| 工具调用验证 | ⚠️ 名称匹配 | ✅ 双模型交叉验证 |
| 质量评分 | ✅ LLM打分 | ✅ DeepSeek-V3.1打分 |
| 轨迹验证 | ⚠️ 字段检查 | ✅ 增强错误检测 |
| GPU要求 | ❌ 无 | ❌ 无 |
| API成本 | 💰 低 | 💰💰 中等 (多2x交叉验证调用) |
| 数据质量 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 技术特点

### 完整版优势
1. **高质量**: 双模型验证确保样本准确性
2. **鲁棒性**: 增强错误检测过滤无效样本
3. **灵活性**: 可配置启用/禁用高级功能
4. **成本可控**: 使用火山方舟免费模型
5. **无GPU**: 纯API调用,无硬件要求

### 核心算法 (保持不变)
✅ Few-shot指令生成
✅ Slot-fill参数修订
✅ WizardLM Evolution复杂化
✅ Function Call生成

### 新增算法 (完整版)
✅ 双模型交叉验证
✅ 干扰工具生成
✅ HTTP/API错误检测
✅ 响应质量深度分析

---

## 输出格式

### 生成数据示例

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

---

## 注意事项

### API成本估算

**完整版** (启用交叉验证):
- 每工具: ~15-20次API调用
- 14工具: ~210-280次调用
- 成本: 约为简化版的 **1.5-2倍**

**简化版** (禁用交叉验证):
- 每工具: ~10-15次API调用
- 14工具: ~140-210次调用

**建议**: 首次运行先用2-3个工具测试

### 配置安全

⚠️ **config.yaml包含API密钥,请勿提交到git**

```bash
echo "config/config.yaml" >> .gitignore
```

---

## 分支说明

- `dev` - 简化版 (基础功能)
- `feature/full-version` - 完整版 (增强过滤) ← **当前分支**
- `main` - 主分支

---

## 详细文档

- **快速指南**: 本文档 (README.md)
- **详细使用**: USAGE.md
- **项目总结**: docs/PROJECT_SUMMARY.md
- **测试报告**: docs/TEST_REPORT.md

---

## 联系信息

- 📧 Email: 12321254@zju.edu.cn
- 📄 论文: https://arxiv.org/abs/2510.24284
- 💻 原项目: MCP-Flow

---

**版本**: 2.0 (完整版)
**状态**: ✅ 完成
**分支**: feature/full-version
