# DeepAgents Harness — Hugging Face Spaces 部署设计

**日期**: 2026-06-06
**状态**: 已批准

## 背景

需要将 deepagents_harness 部署到公网，以便在会议上演示给同事看。内网电脑不便迁移，线上网页访问是最合适的方案。

## 需求

- **受众**: 会议演示为主，同事通过分享链接访问
- **API 费用**: 使用作者的智谱 API Key 承担
- **安全**: 简单密码保护，防止任何人随意访问消耗 API 额度
- **运维**: 零运维，部署后不需要维护服务器
- **部署经验**: 新手友好

## 方案选择

### 评估的方案

| 方案 | 适合度 | 理由 |
|---|---|---|
| **Hugging Face Spaces** (选定) | 非常适合 | 免费、Python 原生支持、零运维、Private Space 提供天然访问控制 |
| Railway | 较适合 | 需要绑卡、免费额度有限 |
| Cloudflare Workers | 不适合 | 不支持完整 Python 运行时，无法运行 langchain/deepagents |
| 云服务器 | 不适合 | 运维负担重、成本高、杀鸡用牛刀 |

### 选择 Hugging Face Spaces 的理由

1. **免费** — 演示场景不需要任何费用
2. **原生 Python 支持** — Docker 类型 Space 支持完整的 Python 环境
3. **SSE 支持** — FastAPI 的 SSE streaming 在 HF Spaces 上完全正常工作
4. **零运维** — 不需要管服务器、SSL 证书、nginx 配置
5. **隐私保护** — 设为 Private 后只有有链接的人能访问
6. **简单部署** — git push 即可触发构建和部署

## 架构

```
同事浏览器 ──HTTPS──→ HF Space (Private)
                       │
                       ├── Nginx (HF 内置, 自动 HTTPS)
                       │
                       ├── FastAPI (uvicorn, port 7860)
                       │   ├── GET /          → 聊天界面 (index.html)
                       │   └── POST /api/chat → SSE streaming
                       │
                       └── Agent (DeepAgents)
                           ├── 智谱 GLM-5.1 API (ZHIPUAI_API_KEY)
                           └── Tavily 搜索 API (TAVILY_API_KEY)
```

前端和后端运行在同一个 FastAPI 进程中，不需要分开部署。

## 需要的改动

### 1. 新增 Dockerfile（必须）

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
COPY src/ src/
RUN pip install -e .
EXPOSE 7860
CMD ["uvicorn", "agent.server:app", "--host", "0.0.0.0", "--port", "7860"]
```

HF Spaces 默认使用 7860 端口。

### 2. 安全性改动（必须）

- Space 设为 Private → 天然的链接级访问控制
- API Key 通过 HF Repository Secrets 注入，不进入代码仓库
- 添加简单的密码保护中间件：
  - `/` 首页正常可访问（展示登录/密码输入界面）
  - `/api/chat` 需要验证密码（通过 header 或 cookie）
  - 密码通过 `ACCESS_PASSWORD` 环境变量配置

### 3. 不需要改动的部分

- 应用核心逻辑（agent、tools、config）
- 前端（index.html）
- 对话和工具功能

### 4. GitHub Actions 自动部署（推荐）

添加一个 GitHub Actions workflow，push 到 master 时自动同步代码到 HF Spaces：

```yaml
# .github/workflows/deploy.yml
name: Deploy to HF Spaces
on:
  push:
    branches: [master]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: git push https://hf-user:${{ secrets.HF_TOKEN }}@huggingface.co/spaces/yourname/space-name main --force
```

需要在 GitHub 仓库的 Settings → Secrets 中添加 `HF_TOKEN`（从 huggingface.co 获取的 Access Token）。

### 改动量

| 改动 | 文件 | 预估行数 |
|---|---|---|
| 新增 Dockerfile | `Dockerfile` | ~10 行 |
| 端口适配 | `server.py` | ~3 行 |
| 密码保护中间件 | `server.py` | ~20 行 |
| GitHub Actions workflow | `.github/workflows/deploy.yml` | ~15 行 |
| .gitignore 更新 | `.gitignore` | ~2 行 |
| **总计** | | **~50 行** |

## 部署流程

### 一次性部署

1. 在 Hugging Face 创建 Private Space（选择 Docker 类型）
2. 在 Space Settings → Repository Secrets 中添加：
   - `ZHIPUAI_API_KEY`
   - `TAVILY_API_KEY`
   - `ACCESS_PASSWORD`
3. 添加 Dockerfile 到项目根目录
4. 将代码 push 到 HF Space 的 Git 仓库
5. 等待自动构建完成（约 2-3 分钟）
6. 访问 Space URL 验证功能正常

### 分享方式

- 分享 HF Space URL（格式: `https://yourname-deepagents.hf.space`）
- 首次使用需输入密码
- 之后正常使用聊天界面

### GitHub Secrets 配置（自动化部署所需）

在 GitHub 仓库 Settings → Secrets and variables → Actions 中添加：

| Secret | 来源 | 用途 |
|---|---|---|
| `HF_TOKEN` | huggingface.co Settings → Access Tokens | 用于 Actions 推送代码到 HF Space |

### 后续更新（自动化）

```
你 push 到 GitHub master
       │
       ▼
GitHub Actions 自动触发
       │
       ▼
代码同步到 HF Space Git 仓库
       │
       ▼
HF Spaces 自动重新构建部署（约 2-3 分钟）
```

你只需要正常 `git push` 到 GitHub，部署全自动完成。

## 成本

| 项目 | 费用 |
|---|---|
| HF Spaces (Free plan) | 0 元 |
| 智谱 API | 按现有用量计费 |
| Tavily API | 免费额度通常够用 |
| **总计** | **基本为 0** |

## 风险和缓解

| 风险 | 缓解措施 |
|---|---|
| HF Spaces 冷启动延迟 | 演示前提前打开预热；免费版通常 5-10 秒启动 |
| API 额度被恶意消耗 | Private Space + 密码保护 |
| HF 服务不可用 | 概率极低，不影响核心需求 |
