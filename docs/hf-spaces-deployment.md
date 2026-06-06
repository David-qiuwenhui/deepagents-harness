# Hugging Face Spaces 部署实录

> 从本地开发到线上可用的完整过程，包含所有踩坑和解决方案。

## 项目概述

- **项目**：DeepAgents Harness — 基于 GLM-5.1 的 AI Agent Demo
- **技术栈**：FastAPI + DeepAgents (LangGraph) + SSE 流式传输
- **部署目标**：让同事通过浏览器在线体验，无需内网迁移
- **部署平台**：Hugging Face Spaces（Private Docker Space）
- **线上地址**：`https://david-qiuwenhui-deepagents-harness.hf.space`

---

## 架构决策

### 为什么选 HF Spaces

| 方案 | 优点 | 缺点 | 适合度 |
|------|------|------|--------|
| **HF Spaces** | 免费、Docker 支持、自带域名 | 资源有限、构建慢 | ★★★★★ |
| Railway | 部署快、Git 集成 | 付费 | ★★★ |
| Cloudflare Workers | 全球加速 | 不支持长连接/容器 | ★★ |
| 云服务器 | 完全控制 | 需运维、需备案 | ★★ |

选择 HF Spaces 的核心理由：免费、Docker 原生支持、无需域名备案、同事通过链接即可访问。

### 认证方案

采用密码保护 + 随机 session token（不存明文密码），适合内部演示场景。

---

## 部署准备

### 1. 项目文件结构

```
deepagents_harness/
├── Dockerfile              # HF Spaces 容器构建
├── README.md               # HF Spaces 路由配置（关键！）
├── pyproject.toml          # Python 包定义 + package-data
├── .dockerignore
├── .github/workflows/
│   └── deploy.yml          # GitHub Actions 自动部署
├── src/agent/
│   ├── server.py           # FastAPI 应用（含认证、SSE 流）
│   ├── static/index.html   # 单文件聊天 UI
│   ├── tools.py            # Agent 工具
│   ├── config.py           # 模型配置
│   └── ...
└── .env                    # 本地环境变量（不入库）
```

### 2. 关键配置文件

**README.md**（HF Spaces 路由配置 — 没有这个会 404）：

```yaml
---
title: DeepAgents Harness
emoji: 🤖
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---
```

**Dockerfile**：

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir --verbose . 2>&1 | tail -100
EXPOSE 7860
CMD ["uvicorn", "agent.server:app", "--host", "0.0.0.0", "--port", "7860"]
```

**pyproject.toml** 必须包含 package-data（否则静态文件不会被 pip 安装）：

```toml
[tool.setuptools.package-data]
agent = ["static/**/*"]
```

### 3. HF Space 配置

- 创建 **Private** Docker Space
- 在 Settings → Repository secrets 中添加：
  - `ZHIPUAI_API_KEY` — 智谱 API 密钥
  - `ACCESS_PASSWORD` — 访问密码

### 4. GitHub Actions 自动部署

`.github/workflows/deploy.yml` 在每次推送到 master 时自动同步代码到 HF Space 的 Git 仓库。

需要配置的 GitHub Secrets：
- `HF_TOKEN` — Hugging Face 访问令牌（Settings → Access Tokens → Write 权限）
- `HF_SPACE_ID` — 格式为 `用户名/空间名`，如 `david-qiuwenhui/deepagents-harness`

---

## 踩坑记录与解决方案

### 问题 1：GitHub Actions 部署 429 限流

**现象**：`git push hf` 时收到 HTTP 429 错误。

**原因**：HF Git API 有频率限制。

**解决**：等待几秒后重试即可，GitHub Actions 本身有重试机制。

---

### 问题 2：HF Space 构建 404

**现象**：容器构建成功，但访问 URL 返回 404。

**原因**：HF Spaces 的反向代理通过 README.md 的 YAML front-matter 读取路由配置，**不会读取 Dockerfile 的 EXPOSE 或 LABEL**。

**解决**：添加 README.md，包含正确的 YAML 头：

```yaml
---
sdk: docker
app_port: 7860
---
```

> **关键认知**：HF Spaces 的路由层和容器层是分离的。路由层读 README.md，容器层读 Dockerfile。两者都要配置正确。

---

### 问题 3：静态文件 FileNotFoundError

**现象**：容器启动后，访问页面报 `FileNotFoundError: static/index.html`。

**原因**：`pip install .`（非 editable 模式）不会自动复制非 Python 文件。需要通过 `package-data` 显式声明。

**解决**：在 `pyproject.toml` 中添加：

```toml
[tool.setuptools.package-data]
agent = ["static/**/*"]
```

> **教训**：本地 `pip install -e .` 和线上 `pip install .` 的文件复制行为不同。本地能用不代表线上也能用。

---

### 问题 4：BaseHTTPMiddleware 破坏 SSE 流式传输

**现象**：SSE 流被完全缓冲后才一次性返回，失去流式效果。

**原因**：FastAPI 的 `BaseHTTPMiddleware` 会等待整个响应完成后才返回，与 `StreamingResponse` 不兼容。

**解决**：移除 `BaseHTTPMiddleware`，改用 FastAPI 的 `Depends()` 依赖注入方式做认证：

```python
# 错误：会缓冲 SSE
@app.middleware("http")
async def auth_middleware(request, call_next):
    ...

# 正确：不缓冲
@app.post("/api/chat", dependencies=[Depends(_check_auth)])
async def chat(request: Request):
    ...
```

---

### 问题 5：LLM 对话无响应（SSE 代理缓冲）

**现象**：页面正常加载、登录成功，但发送聊天消息后模型不回答。

**原因**：HF Spaces 反向代理缓冲 SSE 流，等待足够数据后才转发。

**解决**：在 SSE 流开头发送 ping 注释行，触发代理立即建立流式连接：

```python
async def generate():
    yield ": ping\n\n"  # SSE 注释行，客户端忽略但代理会刷新缓冲
    # ... 正常的 SSE 数据 ...
```

> **原理**：SSE 协议中，以冒号开头的行是注释（`: comment`），浏览器会忽略。但它能触发反向代理刷新缓冲区，建立流式连接。

---

### 问题 6：Cookie 认证在 HF Spaces 上失效（核心问题）

**现象**：登录成功，但发送聊天消息时被 401 拦截，页面跳回登录。

**原因**：HF Spaces 的页面在 `huggingface.co` 的 **iframe** 中加载。浏览器将 cookie 视为第三方 cookie 并静默拦截：

- `samesite="lax"` 在跨站 POST 场景下不发送 cookie
- Chrome/Safari 默认拦截第三方 cookie
- `secure=True` 的 cookie 在某些代理配置下也可能失效

**解决**：从 Cookie 方案切换到 Header + localStorage 方案：

```
登录流程（旧）：Server → Set-Cookie → Browser 自动附加
登录流程（新）：Server → JSON{token} → localStorage → X-Auth-Token Header
```

服务端改动：

```python
# 登录：返回 token 在 JSON body 中（不再用 set_cookie）
@app.post("/api/auth")
async def authenticate(request):
    token = secrets.token_hex(32)
    _auth_sessions.add(token)
    return JSONResponse({"success": True, "token": token})

# 认证：优先检查 header，回退到 cookie
def _get_auth_token(request):
    token = request.headers.get("x-auth-token")
    if token and token in _auth_sessions:
        return token
    token = request.cookies.get("auth_token")
    if token and token in _auth_sessions:
        return token
    return None
```

前端改动：

```javascript
// 存储 token
localStorage.setItem('auth_token', data.token);

// 统一请求函数
async function authFetch(url, opts = {}) {
  const token = localStorage.getItem('auth_token');
  const headers = { ...(opts.headers || {}) };
  if (token) headers['X-Auth-Token'] = token;
  return fetch(url, { ...opts, headers });
}
```

> **核心教训**：在 iframe 场景下，不要依赖 cookie 做认证。用 header + localStorage 更可靠。

---

## 最终认证架构

```
┌─────────┐     POST /api/auth {password}     ┌──────────┐
│ Browser │ ──────────────────────────────────→ │  Server  │
│         │ ←─── {success:true, token:"abc"} ── │          │
│         │     (token 存入 localStorage)        │          │
│         │                                      │          │
│         │     POST /api/chat                   │          │
│         │     Header: X-Auth-Token: abc        │          │
│         │ ──────────────────────────────────→ │          │
│         │ ←─── SSE stream (token chunks) ──── │          │
└─────────┘                                      └──────────┘
```

**安全措施**：
- 服务端存储随机 session token（`secrets.token_hex(32)`），不存明文密码
- 每个 token 64 字符十六进制，不可预测
- Session 存储在进程内存中（`_auth_sessions: set`），容器重启自动失效

---

## 运维命令速查

```bash
# 本地开发
uv run uvicorn agent.server:app --host 0.0.0.0 --port 8000

# 手动部署（不用 GitHub Actions）
git remote add hf https://ci-user:${HF_TOKEN}@huggingface.co/spaces/${HF_SPACE_ID}
git push hf master:main --force

# 检查线上健康状态（浏览器访问）
https://<space-url>/api/health
# 返回 {"status":"ok","api_key_configured":true,"password_configured":true}

# 查看 HF Space 日志
# 在 Space 页面 → Logs 标签页
```

---

## 文件变更清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `Dockerfile` | 新建 | HF Spaces 容器构建配置 |
| `README.md` | 修改 | 添加 HF Spaces YAML 路由头 |
| `pyproject.toml` | 修改 | 添加 package-data 声明 |
| `.dockerignore` | 新建 | 排除无关文件 |
| `.github/workflows/deploy.yml` | 新建 | GitHub Actions 自动部署 |
| `src/agent/server.py` | 修改 | 认证系统、SSE ping、健康端点 |
| `src/agent/static/index.html` | 修改 | localStorage token、错误提示 UI |
| `.env` | 修改 | 添加 ACCESS_PASSWORD |
