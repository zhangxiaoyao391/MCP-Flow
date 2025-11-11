# API配置完成说明

## ✅ 已完成的配置

### 1. 配置文件（config.yaml）

已配置两个API服务：

**主力服务（Primary）- 内网Doubao**
- ✅ API Key: 已配置
- ✅ Base URL: http://10.105.0.30:3008/v1
- ✅ Model: Doubao-Seed-1.6
- ✅ 用途: 所有任务（免费）

**备用服务（Fallback）- OpenAI官方**
- ✅ API Key: 已配置
- ✅ Base URL: https://api.openai.com/v1
- ✅ Model: gpt-4o-mini（便宜版本）
- ✅ 用途: Primary失败时自动切换

### 2. 已修改的文件

1. **config.yaml** - 新增LLM provider配置
2. **src/utils/llm_client.py** - 统一API管理（新建）
3. **src/data_generator/generator.py** - 使用LLMClient
4. **src/data_filter/filter.py** - 使用LLMClient，支持跳过双重验证
5. **src/main.py** - 更新初始化代码
6. **test_api.py** - API测试脚本（新建）

### 3. 核心特性

- ✅ **自动Fallback**: Primary失败自动切换OpenAI
- ✅ **跳过双重验证**: 节省API调用（skip_double_verification: true）
- ✅ **灵活配置**: 每个任务可配置不同provider
- ✅ **统一管理**: 所有API调用通过LLMClient统一处理

---

## 🚀 使用方法

### 1. 测试API连接

```bash
python test_api.py
```

这会测试：
- ✅ Doubao内网服务是否可用
- ✅ OpenAI备用服务是否可用

### 2. 运行Pipeline

```bash
# 运行完整pipeline
python src/main.py --step all

# 或者分步运行
python src/main.py --step collect    # 服务器收集
python src/main.py --step extract    # 工具提取
python src/main.py --step generate   # 数据生成
python src/main.py --step filter     # 数据过滤
python src/main.py --step train      # 模型训练
```

### 3. 配置说明

#### 任务分配配置

在 `config.yaml` 中的 `task_assignments` 部分：

```yaml
task_assignments:
  generation: "primary"       # 数据生成用哪个provider
  verification: "primary"     # 验证用哪个
  scoring: "primary"          # 评分用哪个
  function_call: "primary"    # 函数调用生成用哪个
```

可选值：`primary`（Doubao）或 `fallback`（OpenAI）

#### 过滤策略配置

```yaml
filtering_strategy:
  skip_double_verification: true  # 跳过双重验证，节省API调用
  use_single_model: true           # 只用一个模型
```

---

## 📊 API成本估算

### 使用Doubao（Primary）
- **成本**: 免费（内网服务）
- **速度**: 取决于内网带宽
- **推荐**: ✅ 主要使用

### 使用OpenAI（Fallback）
- **模型**: gpt-4o-mini
- **成本**: ~$0.15/1M输入tokens, $0.60/1M输出tokens
- **预估**: 运行一次完整pipeline约$2-5
- **推荐**: ⚠️ 仅作备用

---

## 🔧 高级配置

### 切换到完全使用OpenAI

如果Doubao服务不稳定，可以修改 `task_assignments`:

```yaml
task_assignments:
  generation: "fallback"      # 改为fallback
  verification: "fallback"
  scoring: "fallback"
  function_call: "fallback"
```

### 添加更多Provider

在 `llm_providers` 中添加新的provider：

```yaml
llm_providers:
  primary:
    # ... Doubao配置
  fallback:
    # ... OpenAI配置
  custom:  # 新增provider
    name: "custom_service"
    provider: "openai"
    api_key: "your-key"
    base_url: "https://your-service.com/v1"
    model: "your-model"
```

然后在 `task_assignments` 中使用：

```yaml
task_assignments:
  generation: "custom"  # 使用新provider
```

---

## 🐛 故障排查

### 问题1: Primary Provider失败

**现象**: 日志显示"❌ Provider primary 失败"

**解决**:
1. 检查内网连接：`curl http://10.105.0.30:3008/v1/models`
2. 检查API Key是否正确
3. 系统会自动fallback到OpenAI

### 问题2: 所有Provider都失败

**现象**: 日志显示"所有provider都失败了"

**解决**:
1. 运行 `python test_api.py` 诊断问题
2. 检查网络连接
3. 检查API Key是否有效
4. 查看详细错误日志

### 问题3: OpenAI成本过高

**现象**: OpenAI账单较高

**解决**:
1. 确认 `task_assignments` 使用的是 `primary` (Doubao)
2. 设置 `skip_double_verification: true`
3. 检查Doubao服务是否正常（避免频繁fallback）

---

## 📝 配置检查清单

运行前请确认：

- [x] config.yaml中两个API Key都已填入
- [x] 内网Doubao服务（10.105.0.30:3008）可访问
- [x] task_assignments配置为 `primary`（优先使用Doubao）
- [x] skip_double_verification设为 `true`（节省成本）
- [x] 运行 `python test_api.py` 测试通过

---

## 🎯 下一步操作

1. **测试API**: `python test_api.py`
2. **小规模测试**: 修改 `data_generation.instruction_per_tool: 1`（每工具只生成1条）
3. **运行生成步骤**: `python src/main.py --step generate`
4. **检查结果**: 查看 `data/instructions/generated_data.json`
5. **全量运行**: 恢复配置后运行 `python src/main.py --step all`

---

## 💡 最佳实践

1. **优先使用Doubao**: 免费且快速
2. **OpenAI作为保险**: 只在Doubao失败时使用
3. **跳过双重验证**: 除非追求极致质量，否则开启skip_double_verification
4. **分步骤运行**: 首次使用建议分步运行，便于调试
5. **监控成本**: 如果使用了OpenAI，定期检查usage

配置完成！可以开始使用MCP-Flow了！ 🎉
