# 代码重构清单

> 基于 Python 后端 + 前端 HTML/JS 的全面代码审查，梳理出 25 项重构建议。
> 按优先级（P0-P3）分类，标注紧急程度和预计工作量。

---

## P0 — 安全漏洞（立即修复）

> 涉及生产环境安全风险，应在下次部署前全部修复。

### 1. `eval()` 替换为 AST 安全解析

- **文件**: `src/agent/tools.py:33`
- **紧急**: ⚡ 立即
- **工作量**: 小（~20 行）
- **风险**: 即便有字符白名单，`eval()` 在服务端不可接受。白名单允许 `()` 可构造调用表达式
- **方案**: 使用 `ast.parse` + 节点白名单（`Constant`, `BinOp`, `UnaryOp`）遍历求值

### 2. `escapeHtml` 转义不完整

- **文件**: `src/agent/static/index.html:1501-1505`
- **紧急**: ⚡ 立即
- **工作量**: 小（改 1 个函数）
- **风险**: 当前实现用 `textContent → innerHTML` 只转义 `<>&`，缺少 `"` 和 `'`。innerHTML 拼接上下文存在注入风险
- **方案**: 改用正则替换，补全 5 种字符转义（`& < > " '`）

### 3. 服务端错误信息泄露给客户端

- **文件**: `src/agent/server.py:172`
- **紧急**: ⚡ 立即
- **工作量**: 极小（改 1 行）
- **风险**: `str(e)` 直接返回前端，可能泄露 API key 报错、文件路径等内部信息
- **方案**: 前端返回通用消息 `"服务器内部错误，请稍后重试"`，详细错误仅打印到服务端日志

### 4. 启动日志泄露敏感信息

- **文件**: `src/agent/server.py:30, 59`
- **紧急**: ⚡ 立即
- **工作量**: 极小（改 2 行）
- **风险**: 打印 API Key 长度（`len(ZHIPUAI_API_KEY) chars`）和请求头名称，缩小攻击者探测空间
- **方案**: 仅输出 `"configured"` / `"not configured"`，删除调试用日志

---

## P1 — 重要问题（本周修复）

> 影响系统可靠性或代码可维护性，建议本周内修复。

### 5. 认证 Token 无过期机制

- **文件**: `src/agent/server.py:42`
- **紧急**: 🔴 高
- **工作量**: 中（~30 行）
- **风险**: `_auth_sessions` set 只加不删，长期运行内存泄漏；token 永不过期，被盗后无法失效
- **方案**: 改为 `dict[str, datetime]`，登录时记录时间戳，每次验证时清理超过 24h 的 token

### 6. 消除模型创建重复逻辑

- **文件**: `src/agent/server.py:104-111` + `src/agent/config.py:11-20`
- **紧急**: 🟡 中
- **工作量**: 小（删除 + 改 import）
- **风险**: `_get_model()` 和 `get_model()` 重复定义，参数相同但错误类型不同（`RuntimeError` vs `ValueError`），新增配置时极易遗漏
- **方案**: `server.py` 复用 `config.py` 的 `get_model()`，删除 `_get_model()` 和硬编码的 `ZHIPU_BASE_URL`

### 7. 消除工具列表重复定义

- **文件**: `src/agent/server.py:96-101` + `src/agent/main.py:12-17`
- **紧急**: 🟡 中
- **工作量**: 小（提取到 config 模块）
- **风险**: TOOLS 列表在两处完全相同，新增工具时需同步修改，极易遗漏
- **方案**: 在 `config.py` 或新建 `registry.py` 统一定义 TOOLS 列表，`server.py` 和 `main.py` 均 import 使用

### 8. `_resolve_safe_path` 改用 `is_relative_to`

- **文件**: `src/agent/tools.py:15`
- **紧急**: 🟡 中
- **工作量**: 极小（改 1 行）
- **风险**: `startswith` 检查存在理论绕过（如 `/app/workspace_evil` 能通过 `/app/workspace` 的检查）
- **方案**: 替换为 `target.is_relative_to(WORK_DIR.resolve())`（Python 3.9+，项目已满足）

### 9. SSE 流添加 AbortController

- **文件**: `src/agent/static/index.html:1609-1723`
- **紧急**: 🟡 中
- **工作量**: 小（~15 行 JS）
- **风险**: 网络断开时 `reader.read()` 可能永不 resolve，`isStreaming` 卡死，用户无法再发送消息
- **方案**: 添加 `AbortController`，新请求开始时 abort 前一个，设置请求超时

### 10. `history` 数组添加长度限制

- **文件**: `src/agent/static/index.html:1346, 1714-1716`
- **紧急**: 🟡 中
- **工作量**: 极小（加 3 行）
- **风险**: 长时间使用后 history 只增不减，payload 越来越大，可能超时或 token 溢出
- **方案**: 限制最近 20 轮（`history.slice(-40)`）

### 11. TavilyClient 复用

- **文件**: `src/agent/tools.py:48`
- **紧急**: 🟢 低
- **工作量**: 极小（改 3 行）
- **风险**: 每次 `web_search` 调用都创建新 HTTP 客户端，浪费连接资源
- **方案**: 模块级创建一次，函数内复用

---

## P2 — 中等问题（本月改进）

> 影响代码质量和用户体验，建议本月内逐步改进。

### 12. `print()` 替换为 `logging`

- **文件**: `server.py` + `main.py`
- **紧急**: 🟢 低
- **工作量**: 中（全局替换）
- **说明**: 统一使用 `logging.getLogger(__name__)`，可控制级别，避免 uvicorn 日志交错

### 13. 清理 `root main.py`

- **文件**: `main.py`
- **紧急**: 🟢 低
- **工作量**: 极小
- **说明**: 当前只是 setuptools 默认脚手架输出 `print("Hello from ...")`，应替换为调用实际入口或删除

### 14. 移除 `_get_auth_token` 中 cookie 死代码

- **文件**: `src/agent/server.py:49-51`
- **紧急**: 🟢 低
- **工作量**: 极小（删 2 行）
- **说明**: `authenticate` 端点从不设置 cookie，cookie 检查分支永远不会命中

### 15. `ingest_doc` 添加文件扩展名白名单

- **文件**: `src/agent/wiki_tools.py:13`
- **紧急**: 🟢 低
- **工作量**: 极小（加 2 行）
- **说明**: 当前可读取 `raw/` 下任意文件（包括 `.env` 等），LLM 可能被诱导泄露内容

### 16. 服务端 `history` 输入验证

- **文件**: `src/agent/server.py:124`
- **紧急**: 🟢 低
- **工作量**: 小
- **说明**: `history` 直接从请求体读取，无长度限制和格式校验，恶意用户可发送巨大 payload

### 17. CDN 添加 SRI

- **文件**: `src/agent/static/index.html:10-13`
- **紧急**: 🟢 低
- **工作量**: 小（查版本号 + 生成 hash）
- **说明**: `marked`、`DOMPurify`、`highlight.js` 通过 CDN 加载但无 `integrity` 属性

### 18. `processFrame` 全量重渲染优化

- **文件**: `src/agent/static/index.html:1579-1606`
- **紧急**: 🟢 低
- **工作量**: 中（需设计增量策略）
- **说明**: 每次 rAF 对完整累积文本重做 markdown 解析 + innerHTML，长对话性能下降。短期可加防抖间隔

---

## P3 — 低优先级（后续迭代）

> 代码风格和可维护性改进，不阻塞功能开发。

### 19. `marked` v15 的 `highlight` 选项已弃用

- **文件**: `index.html:1255-1264`
- **说明**: 改用 `marked-highlight` 插件或渲染后调用 `hljs.highlightAll()`

### 20. CSS 硬编码颜色值统一为变量

- **文件**: `index.html` 多处（`#d97757`, `#c0392b`, `#27ae60`, `#1e1e2e` 等）
- **说明**: 定义 `--error`, `--success`, `--code-bg`, `--accent-dark` 等变量

### 21. `addToolCall`/`addToolResult` 提取分类逻辑

- **文件**: `index.html:1539-1564`
- **说明**: 两处重复的 `MEMORY_TOOLS.includes` / `WIKI_TOOLS.includes` 判断，提取为 `getToolCategory(name)`

### 22. `handleKey` 直接调用 `handleSubmit`

- **文件**: `index.html:1490-1495`
- **说明**: `dispatchEvent(new Event('submit'))` 可能不触发表单处理器，直接调用更可靠

### 23. 全局变量集中为 state 对象

- **文件**: `index.html:1346-1356`
- **说明**: 10+ 个全局变量分散管理，集中为 `const state = { history, isStreaming, ... }` 降低维护难度

### 24. `prefers-reduced-motion` 降级

- **文件**: `index.html`
- **说明**: 动画（`msgIn`、`thinking-dots`、`typing-indicator`）对运动敏感用户无降级处理

### 25. `list_directory` emoji 改文本标记

- **文件**: `src/agent/tools.py:104`
- **说明**: emoji 消耗额外 token 且对 LLM 无帮助，改为 `[DIR]`/`[FILE]`

---

## 统计

| 优先级 | 数量 | 定位 |
|--------|------|------|
| P0 安全漏洞 | 4 | 下次部署前 |
| P1 重要问题 | 7 | 本周内 |
| P2 中等问题 | 7 | 本月内 |
| P3 低优先级 | 7 | 后续迭代 |
| **合计** | **25** | |

## 建议执行顺序

```
第一轮（P0，~1h）：  #1 eval替换 → #2 escapeHtml → #3 错误信息 → #4 日志清理
第二轮（P1，~2h）：  #5 token过期 → #6+#7 去重 → #8 is_relative_to → #9 AbortController → #10 history限制 → #11 TavilyClient
第三轮（P2，按需）： #12-#18 逐项改进
第四轮（P3，有空）： #19-#25 不阻塞功能开发
```
