# DeepAgents 框架使用分析报告

> 分析日期：2026-06-09
> 项目：deepagents_harness
> 框架版本：deepagents>=0.6.8

## 总体使用率：约 10-15%

项目目前将 DeepAgents 作为 LangGraph 的便捷初始化器使用，核心逻辑围绕框架手写。框架的中间件架构、子 Agent 系统、声明式配置等深层能力均未触及。

---

## 一、已使用能力（4 项）

| 能力 | 使用方式 | 源文件 |
|------|----------|--------|
| Agent 创建 | `create_deep_agent(model, tools, system_prompt, store)` | `main.py`, `server.py` |
| 流式事件 | `agent.astream_events(version="v2")` → SSE 推送 | `server.py` |
| 自定义工具 | 12 个 `@tool` 装饰器函数 | `tools.py`, `memory_tools.py`, `wiki_tools.py` |
| Store 存储 | `InMemoryStore` + `get_store()` 实现记忆系统 | `memory_tools.py` |

---

## 二、未使用能力（框架核心特性）

### 2.1 Middleware 架构（0/7 使用）

框架提供 7+ 个内置中间件，项目使用了 **0 个**。所有自定义行为都在框架之外手写实现。

| 中间件 | 功能 | 项目现状 | 对应 roadmap |
|--------|------|----------|-------------|
| `FilesystemMiddleware` | 沙箱文件系统 + 权限控制 + 代码编辑 | `tools.py` 手写简化版 | 阶段一 |
| `MemoryMiddleware` | 自动从 AGENTS.md 加载上下文到 system prompt | `memory_tools.py` 手写 save/recall/list | 阶段二 |
| `SkillsMiddleware` | 渐进式技能披露（SKILL.md 驱动） | `skills/loader.py` YAML 实现 | 阶段 3.5 |
| `SubAgentMiddleware` | 声明式子 Agent 定义 + `task` 工具注入 | 未实现 | 阶段四 |
| `AsyncSubAgentMiddleware` | 远程代理协议（Agent Protocol）接入 | 未实现 | — |
| `SummarizationMiddleware` | 自动上下文压缩 | `server.py` 用 `MAX_HISTORY_TURNS=40` 硬截断 | 跨阶段 |
| `RubricMiddleware` | 自评迭代循环（评分器子 Agent） | 未实现 | — |

### 2.2 create_deep_agent 参数使用（4/17+）

```python
# 当前调用（4 个参数）
agent = create_deep_agent(
    model=model,           # ✅ 已用
    tools=TOOLS,           # ✅ 已用
    system_prompt=prompt,  # ✅ 已用
    store=MEMORY_STORE,    # ✅ 已用
)

# 未使用的参数
# checkpointer=None,      # 对话状态持久化 + 断点恢复
# middleware=[],           # 中间件链
# permissions=None,        # 文件系统权限控制
# backend=None,            # 沙箱/远程执行后端
# skills=None,             # 技能配置
# interrupt_on=None,       # Human-in-the-Loop 中断
# response_format=None,    # 结构化输出
# state_schema=None,       # 自定义 State 扩展
# context_schema=None,     # 上下文 schema
```

### 2.3 公共 API 使用（1/17）

框架导出 17 个公共符号，项目仅使用 `create_deep_agent`：

| 符号 | 类型 | 是否使用 |
|------|------|----------|
| `create_deep_agent` | 函数 | ✅ |
| `DeepAgentState` | 类 | ❌ |
| `SubAgent` | TypedDict | ❌ |
| `CompiledSubAgent` | TypedDict | ❌ |
| `SubAgentMiddleware` | 类 | ❌ |
| `AsyncSubAgent` | TypedDict | ❌ |
| `AsyncSubAgentMiddleware` | 类 | ❌ |
| `FilesystemMiddleware` | 类 | ❌ |
| `FilesystemPermission` | dataclass | ❌ |
| `MemoryMiddleware` | 类 | ❌ |
| `RubricMiddleware` | 类 | ❌ |
| `ProviderProfile` | dataclass | ❌ |
| `register_provider_profile` | 函数 | ❌ |
| `HarnessProfile` | dataclass | ❌ |
| `HarnessProfileConfig` | dataclass | ❌ |
| `GeneralPurposeSubagentProfile` | dataclass | ❌ |
| `register_harness_profile` | 函数 | ❌ |

### 2.4 其他未使用能力

| 能力 | 说明 |
|------|------|
| **Checkpointer** | `MemorySaver` / `SqliteSaver` / `PostgresSaver`，对话状态持久化 |
| **Backend 协议** | `FilesystemBackend`, `StateBackend`, `StoreBackend`, `LocalShellBackend` 等 |
| **DeltaChannel** | 减少 checkpoint 增长（O(N²) → O(N)），需配合 Checkpointer 使用 |
| **Command** | 图内跳转控制（`can_jump_to`），RubricMiddleware 内部使用 |
| **声明式配置** | `ProviderProfile` + `HarnessProfile`，YAML/JSON 可序列化配置 |

---

## 三、功能覆盖矩阵

| 功能类别 | 覆盖 | 备注 |
|----------|------|------|
| 基本 Agent 创建 + 调用 | ✅ | 最简单的 ReAct 循环 |
| 流式事件 | ✅ | SSE 推送到前端 |
| 自定义工具 | ✅ | 12 个工具，全部手写 |
| Store / 记忆 | ⚠️ 部分 | 用 LangGraph Store，未用框架 MemoryMiddleware |
| 子 Agent | ❌ | 框架原生 SubAgent 未使用 |
| 文件系统 + 权限 | ❌ | 手写简化版，未用 FilesystemMiddleware |
| 技能系统 | ❌ | 手写 YAML 版，未用 SkillsMiddleware |
| 中间件链 | ❌ | 0 个中间件 |
| 声明式配置 | ❌ | ProviderProfile / HarnessProfile 未使用 |
| Checkpoint 持久化 | ❌ | 无对话状态保存 |
| Backend / 沙盒 | ❌ | 无远程执行 |
| Rubric 自评 | ❌ | 无迭代评估 |
| 上下文压缩 | ❌ | 手写硬截断，未用 SummarizationMiddleware |
| Human-in-the-Loop | ❌ | 无中断机制 |

---

## 四、学习升级路径

每个未使用的框架能力都对应一个清晰的升级方向：

| 优先级 | 学习目标 | 框架能力 | 升级点 |
|--------|----------|----------|--------|
| P0 | 理解中间件架构 | Middleware 系统 | 从手写工具迁移到框架中间件 |
| P0 | 对话状态管理 | Checkpointer + State | 实现多轮对话持久化 |
| P1 | 上下文管理 | SummarizationMiddleware | 替换硬截断为智能压缩 |
| P1 | 文件系统安全 | FilesystemMiddleware + Permission | 替换手写文件工具 |
| P2 | 子 Agent 协作 | SubAgent + SubAgentMiddleware | 实现任务分解 |
| P2 | Human-in-the-Loop | interrupt_on + Command | 实现确认机制 |
| P3 | 声明式配置 | ProviderProfile + HarnessProfile | 配置化模型和行为 |
| P3 | 自评迭代 | RubricMiddleware | 输出质量评估 |

---

## 五、结论

项目以最低成本跑通了 DeepAgents 的 ReAct 循环，这是一个合理的起点。框架真正的核心设计——**中间件架构 + 声明式配置 + 子 Agent 系统**——尚未触及。

通过 roadmap 的后续阶段推进，每个阶段都可以引入对应的框架原生能力来替换手写实现，这是一个渐进式学习框架设计的理想路径。
