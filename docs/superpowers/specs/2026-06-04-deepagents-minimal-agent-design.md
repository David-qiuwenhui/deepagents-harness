# DeepAgents 最小化 Agent Demo 设计

## 目标

用 DeepAgents 框架 + 智谱 GLM-5.1 跑通最小化 agent，验证：
1. LLM 连接正常（智谱 API via OpenAI 兼容接口）
2. Agent 能规划任务、调用工具、返回结果
3. 子 agent 生成能力正常

## 技术选型

| 项目 | 选择 |
|------|------|
| 框架 | DeepAgents (langchain-ai/deepagents) |
| LLM | 智谱 GLM-5.1 |
| 接入方式 | OpenAI 兼容接口 (`ChatOpenAI` + `base_url`) |
| 包管理 | uv |
| Python | 3.11+ |

## 模型接入配置

通过 `langchain-openai.ChatOpenAI` 配置智谱 API：

```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="glm-5.1",
    base_url="https://open.bigmodel.cn/api/paas/v4/",
    api_key=os.environ["ZHIPUAI_API_KEY"],
)
```

## 项目结构

```
deepagents_harness/
├── pyproject.toml
├── .env.example
├── .gitignore
├── src/
│   └── agent/
│       ├── __init__.py
│       ├── config.py
│       ├── tools.py
│       └── main.py
└── tests/
    └── test_agent.py
```

## 依赖

```
deepagents
langchain-openai
python-dotenv
```

## 模块设计

### config.py

集中管理模型配置：从 `.env` 读取 `ZHIPUAI_API_KEY`，构建 `ChatOpenAI` 实例，暴露 `get_model()` 工厂函数。

### tools.py

提供 2 个示例自定义工具：`get_current_time` 和 `calculate`。

### main.py

程序入口：创建 agent 并运行多步骤任务验证。

## 验收标准

1. `uv run python src/agent/main.py` 能正常执行
2. Agent 能调用自定义工具并返回正确结果
3. Agent 使用内置 `write_todos` 工具进行任务规划
4. 无硬编码密钥，全部通过 `.env` 管理

## 不包含（后续迭代）

- 业务特定工具、自定义子 agent、长期记忆、流式输出 UI、生产部署、LangSmith 集成
