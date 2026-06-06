# 用 Playwright 验证 Agent Chat UI —— 建设思路与实践

> 本文基于 deepagents-harness 项目，分享如何在 AI Agent 项目中引入 Playwright 做前端调试和验证。

## 为什么要用 Playwright？

我们的 Chat UI 是一个单文件前端（`src/agent/static/index.html`，1500+ 行），包含：

- SSE 流式消息渲染
- Markdown 实时解析与展示
- 工具调用事件卡片
- Inspector 调试面板

这些功能用 `curl` 测不了，手动刷新浏览器又慢。Playwright 让我们可以在 Claude Code 会话中直接操作浏览器，做系统化的 UI 调试。

## 架构：Playwright MCP Bridge

传统的 Playwright 需要写测试脚本、启动无头浏览器。但在 Claude Code 中，我们用的是 **Playwright MCP Bridge** 模式：

```
Claude Code  ──调用──▸  Playwright MCP Server  ──控制──▸  你的真实浏览器
```

关键区别：

| 传统 Playwright | MCP Bridge 模式 |
|----------------|----------------|
| 无头浏览器（headless） | 控制你正在使用的真实浏览器 |
| 写测试脚本 | Claude 直接调用工具，像人一样操作 |
| CI/CD 场景 | 开发调试场景 |
| 需要写代码 | 自然语言描述即可 |

### 前置条件

1. 安装 Playwright MCP Bridge 浏览器扩展（Chrome/Edge）
2. 在 Claude Code 中配置 MCP Server（`plugin:everything-claude-code:playwright`）
3. 启动扩展并授权连接

## 可用的 Playwright 工具

Claude Code 通过 MCP 调用 Playwright，核心工具包括：

| 工具 | 用途 | 典型场景 |
|------|------|---------|
| `browser_navigate` | 打开 URL | 导航到 `http://localhost:8000` |
| `browser_snapshot` | 获取页面无障碍树 | 检查 DOM 结构、元素状态 |
| `browser_take_screenshot` | 截图 | 视觉验证 |
| `browser_click` | 点击元素 | 点击发送按钮 |
| `browser_type` | 输入文字 | 在输入框输入消息 |
| `browser_evaluate` | 执行 JS | 检查 DOM 内容、读取变量 |
| `browser_console_messages` | 查看控制台 | 排查 JS 错误 |
| `browser_network_requests` | 查看网络请求 | 验证 SSE 连接 |

## 实战：调试 Markdown 渲染

以下是我们实际使用 Playwright 排查 Markdown 渲染问题的完整流程。

### 第一步：确认基础环境

```
1. 启动服务器: uv run uvicorn agent.server:app --host 0.0.0.0 --port 8000
2. 导航到页面: browser_navigate("http://localhost:8000")
3. 获取快照: browser_snapshot()
```

snapshot 返回的是页面的无障碍树（accessibility tree），不是 HTML。这比读原始 HTML 更高效，因为它只包含语义信息：

```
textbox "输入消息..." [ref=input]
button "发送" [ref=sendBtn]
heading "DeepAgents" [level=1]
```

`ref` 值可以直接传给 `browser_click`、`browser_type` 等工具操作元素。

### 第二步：触发功能

```
1. 输入文字: browser_type(ref=input, text="搜索一下今天的科技新闻")
2. 点击发送: browser_click(ref=sendBtn)
3. 等待响应: browser_wait_for(text="搜索结果")
```

### 第三步：验证渲染结果

这一步是关键。**截图只能看视觉效果，不能确认 DOM 结构是否正确。**

我们用 `browser_evaluate` 检查实际的 DOM：

```javascript
// 检查消息内容区域是否有 Markdown 渲染后的 HTML 标签
() => {
  const msgBody = document.querySelector('.message-body.assistant .md-body');
  if (!msgBody) return 'No .md-body found';
  return {
    hasH2: msgBody.querySelectorAll('h2').length > 0,
    hasStrong: msgBody.querySelectorAll('strong').length > 0,
    hasList: msgBody.querySelectorAll('ul, ol').length > 0,
    innerHTML: msgBody.innerHTML.substring(0, 500)
  };
}
```

在我们的案例中，`browser_evaluate` 证明 Markdown 确实被正确渲染为 HTML（`<h2>`、`<strong>`、`<p>` 等标签都存在），而截图分析误判为"未渲染"。这说明：

> **DOM 检查比截图分析更可靠。** 视觉差异可能来自 CSS 问题（如 `white-space: pre-wrap` 导致间距异常），而非渲染逻辑错误。

### 第四步：定位 CSS 问题

通过 `browser_evaluate` 读取计算样式：

```javascript
(element) => {
  const style = getComputedStyle(element);
  return {
    whiteSpace: style.whiteSpace,
    fontFamily: style.fontFamily,
    fontSize: style.fontSize
  };
}
```

这正是我们发现 `.message-body` 的 `white-space: pre-wrap` 覆盖了 `.md-body` 的渲染效果的过程。

## 调试模式 vs 测试模式

在当前项目中，我们用 Playwright 做**调试**而非自动化测试。两者的区别：

### 调试模式（当前用法）

- 手动触发：需要时才启动浏览器
- 即时反馈：改了 CSS → 刷新页面 → 检查结果
- 灵活探索：可以随时检查任意 DOM 元素
- 不写测试代码：Claude 直接调用工具

### 测试模式（未来方向）

如果你想要自动化 E2E 测试，可以这样建设：

```
tests/
├── e2e/
│   ├── conftest.py          # Playwright fixtures
│   ├── test_chat.py         # 基础对话流程
│   ├── test_tool_events.py  # 工具调用展示
│   └── test_markdown.py     # Markdown 渲染
```

示例测试用例：

```python
# tests/e2e/test_chat.py
import pytest
from playwright.sync_api import Page, expect


@pytest.fixture
def base_url():
    return "http://localhost:8000"


def test_send_message_and_receive_response(page: Page, base_url: str):
    """验证基本对话流程：发送消息 → 收到回复"""
    page.goto(base_url)

    # 输入消息
    page.fill('input[placeholder*="输入消息"]', "现在是几点？")
    page.click('button:has-text("发送")')

    # 等待助手消息出现
    assistant_msg = page.locator('.message-body.assistant')
    expect(assistant_msg).to_be_visible(timeout=30000)

    # 验证消息不为空
    assert assistant_msg.inner_text().strip() != ""


def test_tool_call_displayed(page: Page, base_url: str):
    """验证工具调用事件在 UI 中展示"""
    page.goto(base_url)

    # 发送会触发工具调用的消息
    page.fill('input[placeholder*="输入消息"]', "帮我算 15 * 37 + 128")
    page.click('button:has-text("发送")')

    # 等待工具调用卡片出现
    tool_card = page.locator('.tool-event')
    expect(tool_card).to_be_visible(timeout=30000)
    expect(tool_card).to_contain_text("calculate")


def test_markdown_rendering(page: Page, base_url: str):
    """验证 Markdown 被渲染为 HTML，而非纯文本"""
    page.goto(base_url)

    # 假设有一条已渲染的助手消息
    page.fill('input[placeholder*="输入消息"]', "搜索一下 Python 最新版本")
    page.click('button:has-text("发送")')

    # 等待响应完成
    page.wait_for_selector('.md-body', timeout=30000)

    # 验证 Markdown 渲染产物
    md_body = page.locator('.md-body')
    # 不应该看到原始 Markdown 语法
    expect(md_body).not_to_contain_text('##')  # 标题应被渲染为 <h2>
    # 应该有 HTML 标签
    assert md_body.locator('h2, h3, p, strong, ul, ol').count() > 0
```

## 在 Claude Code 中的使用建议

### 适合用 Playwright 的场景

- **CSS 调试**：改了样式后验证视觉效果
- **DOM 结构验证**：确认组件渲染正确
- **流式渲染调试**：检查 SSE 事件是否正确解析
- **控制台排查**：读取 JS 错误信息

### 不适合用 Playwright 的场景

- **快速冒烟测试**：`curl http://localhost:8000` 足够
- **API 逻辑验证**：用 pytest 测后端即可
- **每次改代码都启动浏览器**：太慢，改完一批再统一验证

### 高效的调试节奏

```
1. 改代码 → 2. curl 验证服务器存活 → 3. Playwright 做关键路径验证 → 4. 截图给用户看
```

## 总结

Playwright MCP Bridge 让 Claude Code 拥有了"看见"浏览器的能力。它不是替代人工测试，而是在开发过程中提供一种系统化的 UI 调试手段。

关键经验：

1. **snapshot 比 screenshot 更高效** — 无障碍树直接展示语义结构
2. **evaluate 比截图更准确** — DOM 检查不受视觉干扰
3. **调试优先，测试后续** — 先用 Playwright 把功能调通，再考虑写自动化测试
4. **不要每次改代码都启动浏览器** — 在关键节点验证即可
