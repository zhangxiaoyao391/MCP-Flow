"""仅运行数据过滤"""
import sys
sys.path.insert(0, 'src')
from main import MCPFlowPipeline
import json

pipeline = MCPFlowPipeline('config/config.yaml')

# 加载已生成的数据
with open('data/function_call/generated_20251114_114803.json', encoding='utf-8') as f:
    samples = json.load(f)

print(f"加载了 {len(samples)} 个样本")

# 仅运行过滤
filtered = pipeline.filter_data(samples)

print(f"过滤完成: {len(filtered)} 个样本通过")
