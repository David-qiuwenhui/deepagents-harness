# Hugging Face Spaces 部署实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 deepagents_harness 部署到 Hugging Face Spaces，实现会议演示 + GitHub Actions 自动部署。

**Architecture:** 在现有 FastAPI 应用上添加密码保护中间件和 Dockerfile，部署到 HF Spaces (Private Docker Space)。GitHub Actions 监听 master 分支 push，自动同步代码到 HF Space Git 仓库触发重建。

**Tech Stack:** FastAPI, Docker, Hugging Face Spaces, GitHub Actions

---

## File Structure

| Action | File | Responsibility |
|---|---|---|
| Create | `Dockerfile` | HF Spaces 容器构建配置 |
| Create | `.github/workflows/deploy.yml` | GitHub Actions 自动部署 |
| Modify | `src/agent/server.py` | 添加密码保护中间件 + 认证端点 |
| Modify | `src/agent/static/index.html` | 添加密码输入界面 + 认证逻辑 |

不需要改动的文件：`config.py`, `tools.py`, `pyproject.toml`

---

### Task 1: 创建 Dockerfile

**Files:**
- Create: `Dockerfile`

- [ ] **Step 1: 创建 Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir -e .

EXPOSE 7860

CMD ["uvicorn", "agent.server:app", "--host", "0.0.0.0", "--port", "7860"]
```

关键决策：
- `python:3.11-slim` — pip 安装兼容性好，镜像较小
- `--no-cache-dir` — 减小镜像体积
- 不 COPY `.env` — Secrets 通过 HF 环境变量注入
- 不 COPY `workspace/`, `docs/`, `main.py` — 部署不需要

- [ ] **Step 2: Commit**

```bash
git add Dockerfile
git commit -m "feat: add Dockerfile for HF Spaces deployment"
```

---

### Task 2: 添加密码保护中间件和认证端点

**Files:**
- Modify: `src/agent/server.py`

- [ ] **Step 1: 添加导入**

在 `server.py` 第 9 行（`from fastapi.responses import ...`）后追加：

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse, JSONResponse
```

- [ ] **Step 2: 添加中间件和认证端点**

在 `app = FastAPI(title="DeepAgents Chat")`（第 19 行）之后，`ZHIPU_BASE_URL = ...`（第 21 行）之前，插入：

```python
ACCESS_PASSWORD = os.environ.get("ACCESS_PASSWORD", "")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not ACCESS_PASSWORD:
            return await call_next(request)

        if request.url.path == "/api/auth":
            return await call_next(request)

        if request.url.path.startswith("/api/"):
            token = request.cookies.get("auth_token")
            if token != ACCESS_PASSWORD:
                return StarletteResponse(content="Unauthorized", status_code=401)
            return await call_next(request)

        return await call_next(request)


app.add_middleware(AuthMiddleware)


@app.post("/api/auth")
async def authenticate(request: Request):
    body = await request.json()
    password = body.get("password", "")
    if password != ACCESS_PASSWORD:
        return JSONResponse({"success": False, "message": "密码错误"}, status_code=401)
    response = JSONResponse({"success": True})
    response.set_cookie(
        key="auth_token",
        value=ACCESS_PASSWORD,
        httponly=True,
        max_age=86400 * 30,
        samesite="lax",
    )
    return response
```

认证逻辑：
- 未设置 `ACCESS_PASSWORD` → 所有请求放行（本地开发不受影响）
- `POST /api/auth` → 始终放行（这是登录端点）
- 其他 `/api/*` → 检查 cookie 中的 `auth_token`
- 页面请求 (`/`) → 始终放行（前端 JS 自行处理显示逻辑）

- [ ] **Step 3: 本地验证（无密码模式）**

Run: `ZHIPUAI_API_KEY=test uv run uvicorn agent.server:app --port 8000`

用浏览器打开 `http://localhost:8000`，确认：
- 页面正常加载，无密码拦截
- `/api/chat` 正常响应（返回 200 或正常的 SSE 流）

- [ ] **Step 4: 本地验证（有密码模式）**

Run: `ACCESS_PASSWORD=test123 ZHIPUAI_API_KEY=test uv run uvicorn agent.server:app --port 8000`

用 curl 验证：

```bash
# 未认证请求应返回 401
curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{"message":"hello"}'
# Expected: 401 Unauthorized
```

- [ ] **Step 5: Commit**

```bash
git add src/agent/server.py
git commit -m "feat: add password protection middleware for deployment"
```

---

### Task 3: 在前端添加密码输入界面

**Files:**
- Modify: `src/agent/static/index.html`

- [ ] **Step 1: 添加密码界面 CSS**

在 `</style>` 标签之前（约第 1005 行之前）添加：

```css
/* ── Auth overlay ── */
.auth-overlay {
  position: fixed; inset: 0;
  background: var(--bg);
  display: flex; align-items: center; justify-content: center;
  z-index: 9999;
}
.auth-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 40px;
  width: 360px;
  text-align: center;
  box-shadow: 0 4px 24px rgba(0,0,0,0.06);
}
.auth-card .auth-logo {
  font-size: 28px; font-weight: 700;
  color: var(--text);
  margin-bottom: 8px;
  font-family: var(--font-display);
}
.auth-card .auth-sub {
  font-size: 14px; color: var(--text-muted);
  margin-bottom: 24px;
}
.auth-card input {
  width: 100%; padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: 10px; font-size: 15px;
  outline: none; margin-bottom: 16px;
  transition: border-color 0.2s;
  font-family: var(--font-body);
}
.auth-card input:focus { border-color: var(--blue); }
.auth-card .auth-btn {
  width: 100%; padding: 10px;
  background: var(--text); color: var(--bg);
  border: none; border-radius: 10px;
  font-size: 15px; font-weight: 600;
  cursor: pointer; transition: opacity 0.2s;
  font-family: var(--font-display);
}
.auth-card .auth-btn:hover { opacity: 0.85; }
.auth-card .auth-error {
  color: #c0392b; font-size: 13px;
  margin-top: 12px; display: none;
}
.auth-hidden { display: none !important; }
```

- [ ] **Step 2: 添加密码覆盖层 HTML**

在 `<body>` 标签后（第 1006 行），`<div class="app">` 之前（第 1007 行之前），插入：

```html
<div class="auth-overlay auth-hidden" id="authOverlay">
  <div class="auth-card">
    <div class="auth-logo">DeepAgents</div>
    <div class="auth-sub">请输入访问密码</div>
    <form id="authForm">
      <input type="password" id="authInput" placeholder="密码" autocomplete="current-password">
      <button type="submit" class="auth-btn">进入</button>
    </form>
    <div class="auth-error" id="authError">密码错误，请重试</div>
  </div>
</div>
```

注意：默认带 `auth-hidden` 类，通过 JS 检测认证状态后才决定是否显示。

- [ ] **Step 3: 添加认证 JS 逻辑**

在 `<script>` 标签内，`let history = [];`（第 1165 行）之前，插入：

```javascript
/* ── Auth ── */
async function checkAuth() {
  const overlay = document.getElementById('authOverlay');
  if (!overlay) return;
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: '__auth_check__' }),
    });
    if (res.status === 401) {
      overlay.classList.remove('auth-hidden');
      document.querySelector('.app').classList.add('auth-hidden');
    }
  } catch { /* network error, skip auth */ }
}

document.getElementById('authForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const pwd = document.getElementById('authInput').value;
  const errEl = document.getElementById('authError');
  try {
    const res = await fetch('/api/auth', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: pwd }),
    });
    const data = await res.json();
    if (data.success) {
      document.getElementById('authOverlay').classList.add('auth-hidden');
      document.querySelector('.app').classList.remove('auth-hidden');
      errEl.style.display = 'none';
    } else {
      errEl.style.display = 'block';
      document.getElementById('authInput').value = '';
    }
  } catch {
    errEl.style.display = 'block';
  }
});

checkAuth();
```

流程：
1. 页面加载 → `checkAuth()` 探测 `/api/chat` → 401 则显示密码卡
2. 用户输入密码 → POST `/api/auth` → 成功设 cookie 隐藏密码卡
3. 后续请求 cookie 自动带上，中间件放行
4. 未设置 `ACCESS_PASSWORD` 时中间件不拦截，`checkAuth()` 得到正常响应，密码卡不显示

- [ ] **Step 4: 浏览器验证**

Run: `ACCESS_PASSWORD=test123 ZHIPUAI_API_KEY=test uv run uvicorn agent.server:app --port 8000`

用浏览器打开 `http://localhost:8000`：
- Expected: 显示密码输入界面（DeepAgents logo + 密码框）
- 输入 `test123` → Expected: 密码卡消失，聊天界面出现
- 输入错误密码 → Expected: 显示红色"密码错误"提示

- [ ] **Step 5: Commit**

```bash
git add src/agent/static/index.html
git commit -m "feat: add password protection UI for deployment"
```

---

### Task 4: 创建 GitHub Actions 自动部署 workflow

**Files:**
- Create: `.github/workflows/deploy.yml`

- [ ] **Step 1: 创建 workflow 文件**

```yaml
name: Deploy to HF Spaces

on:
  push:
    branches: [master]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Push to Hugging Face Spaces
        env:
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
        run: |
          git config --global user.email "ci@github.com"
          git config --global user.name "GitHub Actions"
          git remote add hf https://ci-user:${HF_TOKEN}@huggingface.co/spaces/${{ secrets.HF_SPACE_ID }}
          git push hf master:main --force
```

变量说明：
- `HF_TOKEN` — HF Access Token（Write 权限），在 GitHub Secrets 中配置
- `HF_SPACE_ID` — Space 完整 ID（如 `username/space-name`），在 GitHub Secrets 中配置
- `master:main` — GitHub 分支是 master，HF Spaces 要求默认分支是 main
- `--force` — 确保 HF 历史与 GitHub 同步

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/deploy.yml
git commit -m "ci: add GitHub Actions workflow for HF Spaces auto-deploy"
```

---

### Task 5: 更新 .gitignore

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: 添加 workspace/ 到 .gitignore**

在 `.gitignore` 末尾追加：

```
workspace/
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: add workspace/ to gitignore"
```

---

### Task 6: 首次部署（手动操作）

此任务需要你在浏览器中操作，无法自动化。

- [ ] **Step 1: 创建 HF Space**

1. 访问 https://huggingface.co/new-space
2. Space name: `deepagents-harness`
3. SDK: **Docker**
4. Hardware: **Free CPU**
5. Visibility: **Private**
6. 点击 "Create Space"

- [ ] **Step 2: 配置 HF Space Secrets**

在 Space 页面 → Settings → Repository secrets 中添加：

| Key | Value |
|---|---|
| `ZHIPUAI_API_KEY` | 你的智谱 API Key |
| `TAVILY_API_KEY` | 你的 Tavily API Key |
| `ACCESS_PASSWORD` | 你想设置的访问密码 |

- [ ] **Step 3: 配置 GitHub Secrets**

在 GitHub 仓库 `David-qiuwenhui/deepagents-harness` → Settings → Secrets and variables → Actions 中添加：

| Secret | Value |
|---|---|
| `HF_TOKEN` | 从 https://huggingface.co/settings/tokens 创建（需要 Write 权限） |
| `HF_SPACE_ID` | `你的HF用户名/deepagents-harness` |

- [ ] **Step 4: 推送所有改动到 GitHub**

```bash
git push origin master
```

GitHub Actions 自动触发，将代码同步到 HF Space 并触发重建。

- [ ] **Step 5: 验证部署**

1. 等待 HF Space 构建完成（约 2-5 分钟）
2. 访问 Space URL（格式: `https://<你的HF用户名>-deepagents-harness.hf.space`）
3. 确认密码输入界面出现
4. 输入密码 → 确认聊天界面加载
5. 发送一条测试消息 → 确认 LLM 正常响应
