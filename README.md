---
title: DeepAgents Harness
emoji: 🤖
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# DeepAgents Harness

基于 GLM-5.1 的 AI Agent Demo，支持工具调用、长期记忆、知识库等能力。

## 在线访问

项目已部署到 Hugging Face Spaces（Private Space），访问流程：

1. 打开链接：`https://david-qiuwenhui-deepagents-harness.hf.space`
2. 输入访问密码登录
3. 在聊天界面与 Agent 对话

> 空闲一段时间后容器会休眠，首次访问需等待约 30 秒唤醒。

## 本地开发

```bash
# 安装依赖
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 ZHIPUAI_API_KEY

# 启动 Web 服务
uv run uvicorn agent.server:app --host 0.0.0.0 --port 8000

# 或使用 CLI 模式（单轮对话）
uv run python -m agent.main
```

## Agent 能力

| 能力 | 工具 | 说明 |
|------|------|------|
| 时间查询 | `get_current_time` | 获取当前日期时间 |
| 数学计算 | `calculate` | 计算数学表达式 |
| 网络搜索 | `web_search` | 搜索互联网获取实时信息（Tavily） |
| 文件读写 | `read_file`, `write_file` | 在沙箱工作目录中读写文件 |
| 目录浏览 | `list_directory` | 列出工作目录下的文件 |
| 长期记忆 | `save_memory`, `recall_memory`, `list_memories` | 保存和检索对话中的关键信息 |
| 知识库 | `ingest_doc`, `search_wiki`, `list_wiki` | 摄入文档并构建可搜索的 Wiki |

## 技术栈

- **LLM**: Zhipu GLM-5.1（via OpenAI 兼容接口）
- **Agent 框架**: DeepAgents (LangGraph)
- **后端**: FastAPI + SSE 流式传输
- **前端**: 单文件 HTML/CSS/JS（无构建步骤）
- **部署**: Hugging Face Spaces (Docker)

## 自动部署

推送到 `master` 分支时，GitHub Actions 自动同步代码到 HF Spaces。详见 `.github/workflows/deploy.yml`。

详细的部署过程和踩坑记录见 [docs/hf-spaces-deployment.md](docs/hf-spaces-deployment.md)。
