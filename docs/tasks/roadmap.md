# DeepAgents 进阶路线图

> 基于 deepagents-harness 项目的功能迭代规划。每个阶段在前一阶段基础上构建。

## 阶段一：添加实用工具（当前）

**目标**：让 Agent 具备实际能力，从 demo 工具走向真实场景。

### 工具清单

| # | 工具 | 状态 | 优先级 | 说明 |
|---|------|------|--------|------|
| 1 | `get_current_time` | done | — | 获取当前日期时间（已有） |
| 2 | `calculate` | done | — | 计算数学表达式（已有） |
| 3 | `web_search` | done | P0 | 搜索互联网，获取最新信息（Tavily API） |
| 4 | `read_file` | done | P1 | 读取本地文件内容（沙箱隔离） |
| 5 | `write_file` | done | P1 | 写入/创建本地文件（自动建目录） |
| 6 | `list_directory` | done | P2 | 列出目录结构 |
| 7 | `run_code` | todo | P2 | 在沙箱中执行 Python 代码（安全考虑） |
| 8 | `document_parse` | todo | P1 | 解析 PDF/DOCX/图片等文档，提取结构化文本 |
| 9 | `document_compare` | todo | P1 | 将实际文档内容与期望内容做差异对比 |
| 10 | `report_generate` | todo | P1 | 生成结构化对比报告 |

### 完成标准

- [x] 至少新增 2 个实用工具（web_search + file I/O）
- [x] 每个工具有清晰的 docstring 和输入验证
- [ ] 通过 Chat UI 可实际调用并看到结果（基础工具已验证，业务工具待开发）
- [ ] Inspector 面板正确显示工具调用事件

### 学习要点

- 工具设计模式：命名、描述、参数设计
- API 集成：如何对接第三方服务
- 安全边界：输入验证、沙箱、权限控制

---

## 阶段二：Memory 系统

**目标**：让 Agent 拥有记忆能力，跨会话保持上下文。

### 子任务

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| 1 | 长期记忆工具 | todo | save_memory / recall_memory / list_memories，基于 InMemoryStore |
| 2 | 记忆 UI | todo | Inspector 面板展示记忆读写过程（紫色卡片） |
| 3 | 短期记忆优化 | deferred | 服务端管理对话历史（InMemorySaver + thread_id），待长期记忆完成后建设 |

### 完成标准

- [x] Agent 能记住跨会话的关键信息（长期记忆）
- [ ] 对话历史不会无限增长导致 token 溢出（短期记忆，deferred）
- [ ] Inspector 展示记忆操作过程

### 学习要点

- Agent 状态管理（LangGraph State）
- 向量存储与相似度检索
- 记忆策略：全量 vs 摘要 vs 检索

---

## 阶段三：LLM-Wiki 知识库

**目标**：基于 Karpathy LLM-Wiki 方法论，让 Agent 维护一个结构化的业务知识库，用户通过对话获取业务知识问答。

**方法论**：不使用传统 RAG（每次从原始文档检索），而是让 LLM 持续编译和维护一个结构化 Wiki 中间层。知识"编译一次、持续更新"。

**参考**：[Karpathy LLM-Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)

### 三层架构

```
workspace/raw/       → 原始文档（不可变，业务文档源）
workspace/wiki/      → Wiki 页面（LLM 维护，结构化知识）
Schema (SYSTEM_PROMPT) → Agent 行为规则
```

### Phase 3A: Wiki 基础设施

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| 1 | Wiki 目录结构 | todo | workspace/wiki/ + index.md + log.md |
| 2 | ingest_doc 工具 | todo | 读取 raw/ 文档，提取关键信息，生成/更新 Wiki 页面 |
| 3 | search_wiki 工具 | todo | 搜索 index.md 定位相关页面，读取并合成回答 |
| 4 | Wiki UI | todo | Inspector 展示 Wiki 检索过程 |

### Phase 3B: 文档管理

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| 5 | 文档上传 | todo | 前端支持上传 txt/md 文档到 raw/ |
| 6 | PDF/DOCX 解析 | deferred | 支持更多格式的文档导入 |
| 7 | Lint 巡检 | deferred | 定期检查 Wiki 矛盾、过时信息、孤立页面 |
| 8 | 语义搜索升级 | deferred | 当 Wiki 规模超过 ~100 篇时，引入向量检索 |

### 完成标准

- [ ] Agent 能基于 Wiki 回答业务问题并引用来源
- [ ] 支持通过工具摄入新文档到 Wiki
- [ ] index.md 索引机制正常工作
- [ ] Inspector 展示 Wiki 检索过程

### 学习要点

- Embedding 模型与向量数据库
- Chunk 策略对检索质量的影响
- RAG 的局限性与改进方向

---

## 阶段 3.5：Skills 系统

**目标**：为 Agent 引入可插拔的 Skills（技能）系统，让 Agent 能力可以按需加载、组合和扩展。

**灵感**：类似 Claude Code 的 Skills 机制 —— 每个 Skill 是一个独立的能力模块，包含指令、工具和上下文。用户可以通过自然语言触发特定 Skill，或者让 Agent 自动匹配合适的 Skill。

### 子任务

| # | 任务 | 说明 |
|---|------|------|
| 1 | Skill 定义规范 | 设计 Skill 的元数据格式（名称、描述、触发条件、指令模板） |
| 2 | Skill 加载机制 | 从配置文件或目录动态加载 Skill，注入到 System Prompt |
| 3 | Skill 匹配 | 根据用户意图自动选择合适的 Skill |
| 4 | Skill 管理 UI | 前端展示已激活的 Skills，支持启用/禁用 |
| 5 | 内置 Skills | 开发几个示例 Skill（如"文档对比"、"周报生成"、"代码审查"） |

### 学习要点

- Prompt 工程中的模块化设计
- 技能路由与意图识别
- 可插拔架构的扩展性设计

---

## 阶段四：多 Agent 协作

**目标**：引入子 Agent 模式，实现任务分解与专业化处理。

### 子任务

| # | 任务 | 说明 |
|---|------|------|
| 1 | Agent 角色定义 | Planner / Researcher / Coder 等角色 |
| 2 | 任务分解 | 主 Agent 将复杂任务拆解为子任务 |
| 3 | Agent 间通信 | 子 Agent 间传递上下文和结果 |
| 4 | 编排策略 | 串行、并行、条件分支 |
| 5 | 协作 UI | 展示多 Agent 工作流 |

### 学习要点

- Agent 编排模式（Supervisor / Swarm / Hierarchical）
- 任务分解的策略和粒度
- 多 Agent 上下文共享与隔离

---

## 阶段五：Human-in-the-Loop

**目标**：让 Agent 在关键节点请求人类确认，增强安全性和可控性。

### 子任务

| # | 任务 | 说明 |
|---|------|------|
| 1 | 工具确认机制 | 敏感工具执行前请求用户确认 |
| 2 | 可视化审批 | UI 展示待确认操作及详情 |
| 3 | 人工纠正 | 允许用户修改 Agent 的中间结果 |
| 4 | 中断与恢复 | LangGraph interrupt 机制 |

### 学习要点

- LangGraph 的 interrupt 和断点机制
- Agent 安全模式（确认、审计、回滚）
- 人机协作的 UX 设计

---

## 跨阶段改进

这些改进可以穿插在任意阶段：

- **GLM-5.1 reasoning_content 支持**：绕过 langchain-openai，展示思维链
- **前端体验优化**：Markdown 渲染、代码高亮、文件上传
- **测试覆盖**：每个新功能配套单元测试和集成测试
- **错误处理**：工具调用失败时的优雅降级和重试

---

## 参考资源

- [DeepAgents 文档](https://github.com/anthropics/deepagents)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [LangChain Tools 指南](https://python.langchain.com/docs/concepts/tools/)
- 项目内文章：`docs/articles/2026-06-06-how-agent-knows-which-tool-to-use.md`
