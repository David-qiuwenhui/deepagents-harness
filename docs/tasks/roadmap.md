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

| # | 任务 | 说明 |
|---|------|------|
| 1 | 短期记忆优化 | 服务端管理对话历史，支持上下文窗口裁剪 |
| 2 | 长期记忆 | 用户偏好、关键事实的持久化存储 |
| 3 | 记忆检索 | 基于相关性召回历史信息注入上下文 |
| 4 | Memory UI | Inspector 面板展示记忆读写过程 |

### 完成标准

- [ ] Agent 能记住跨会话的关键信息
- [ ] 对话历史不会无限增长导致 token 溢出
- [ ] Inspector 展示记忆操作过程

### 学习要点

- Agent 状态管理（LangGraph State）
- 向量存储与相似度检索
- 记忆策略：全量 vs 摘要 vs 检索

---

## 阶段三：RAG 知识库

**目标**：让 Agent 从特定文档/知识库中检索信息，生成有据可依的回答。

### 子任务

| # | 任务 | 说明 |
|---|------|------|
| 1 | 文档加载 | 支持 txt/md/pdf 等格式的文档导入 |
| 2 | 文本分片 | 将长文档切分为适合检索的 chunk |
| 3 | 向量化存储 | Embedding + 向量数据库 |
| 4 | 检索策略 | 相似度搜索、混合检索、重排序 |
| 5 | RAG 工具 | 封装为 Agent 可调用的工具 |
| 6 | RAG UI | 展示检索来源和相关性分数 |

### 完成标准

- [ ] Agent 能基于知识库回答问题并引用来源
- [ ] 支持增量添加文档
- [ ] Inspector 展示检索过程和来源

### 学习要点

- Embedding 模型与向量数据库
- Chunk 策略对检索质量的影响
- RAG 的局限性与改进方向

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
