# Skill 系统设计：Prompt 模块化

## 目标

将当前硬编码的 `SYSTEM_PROMPT` 拆分为多个可插拔的 Skill 模块。每个 Skill 是独立的 YAML 文件，包含指令模板和触发关键词。Agent 根据用户消息动态匹配 Skill，拼接出针对性的 system prompt。

**本次范围**：Prompt 模块化 + 关键词匹配。不含工作流编排（方案 2），不含前端 UI。

## Skill 定义规范

每个 Skill 是一个目录，包含一个 `skill.yaml` 文件：

```yaml
name: "记忆助手"
description: "管理和检索用户的长期记忆"
enabled: true
triggers:
  - "记住"
  - "回忆"
instructions: |
  你拥有长期记忆能力：
  - 当用户告诉你重要信息时，主动使用 save_memory 工具保存
```

字段说明：

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | 是 | 人类可读名称 |
| `description` | 是 | 一句话描述，用于日志和 UI |
| `enabled` | 否 | 是否启用，默认 true |
| `triggers` | 否 | 关键词列表，消息中出现任一即匹配。无 triggers 的 Skill 始终加载 |
| `instructions` | 是 | 注入到 system prompt 的指令文本 |

## 目录结构

```
src/agent/skills/
├── __init__.py
├── loader.py          # 加载、匹配、拼接逻辑
├── general/
│   └── skill.yaml     # 基础行为，始终加载
├── memory/
│   └── skill.yaml     # 记忆能力
└── wiki/
    └── skill.yaml     # 知识库能力
```

## SkillLoader 核心逻辑

```python
class SkillLoader:
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self._skills: list[Skill] = []

    def load_all(self) -> None:
        """扫描 skills_dir 下所有 skill.yaml，解析为 Skill 对象"""

    def match(self, user_message: str) -> list[Skill]:
        """关键词子串匹配，返回命中的 Skill 列表"""

    def build_system_prompt(self, user_message: str) -> str:
        """
        1. 始终包含无 triggers 的 Skill（如 general）
        2. 匹配用户消息，追加命中 Skill 的指令
        3. 返回拼接后的完整 system prompt
        """
```

匹配规则：
- 关键词做子串匹配（`"记忆" in "帮我记住这个"` → 命中）
- 可同时命中多个 Skill
- 无 triggers 的 Skill 始终注入，不参与匹配

拼接结果：

```
[general instructions]        ← 始终加载
[skill A instructions]        ← 关键词命中
[skill B instructions]        ← 关键词命中
```

## 初始 Skill 拆分

将当前 `SYSTEM_PROMPT` 拆为 3 个 Skill：

### general（始终加载）

- triggers: `[]`（无触发词）
- instructions: "你是一个有用的助手。你可以使用工具来完成任务。请用中文回答。"

### memory

- triggers: `["记住", "回忆", "记忆", "记得", "忘记", "保存信息"]`
- instructions: 当前 `SYSTEM_PROMPT` 中"你拥有长期记忆能力"段落

### wiki

- triggers: `["知识库", "文档", "wiki", "指南", "操作手册", "学习文档"]`
- instructions: 当前 `SYSTEM_PROMPT` 中"你拥有知识库能力"段落

## 与 server.py 的集成

### 当前

```python
SYSTEM_PROMPT = "你是一个有用的助手..."  # 硬编码

agent = create_deep_agent(
    model=model,
    tools=TOOLS,
    system_prompt=SYSTEM_PROMPT,
    store=MEMORY_STORE,
)
```

### 改为

```python
# 启动时初始化（模块级别）
SKILL_LOADER = SkillLoader(Path(__file__).parent / "skills")
SKILL_LOADER.load_all()

# 每次请求时
system_prompt = SKILL_LOADER.build_system_prompt(user_message)
agent = create_deep_agent(
    model=model,
    tools=TOOLS,               # 工具始终全部可用
    system_prompt=system_prompt,
    store=MEMORY_STORE,
)
```

工具集始终全部可用，Skill 只影响 system prompt 指令部分。

## 错误处理

| 场景 | 处理 |
|------|------|
| YAML 解析失败 | 打印 warning，跳过该 Skill，不阻塞启动 |
| `skills/` 目录不存在 | fallback 到最小 prompt |
| 所有 Skill 被 disabled | fallback 到最小 prompt |
| Skill instructions 为空 | 跳过，不注入空段落 |

## 文件变更清单

### 新建

| 文件 | 说明 |
|------|------|
| `src/agent/skills/__init__.py` | 导出 SkillLoader |
| `src/agent/skills/loader.py` | 核心逻辑 |
| `src/agent/skills/general/skill.yaml` | 通用助手 |
| `src/agent/skills/memory/skill.yaml` | 记忆助手 |
| `src/agent/skills/wiki/skill.yaml` | 知识库 |

### 修改

| 文件 | 变更 |
|------|------|
| `src/agent/server.py` | 删除硬编码 SYSTEM_PROMPT，用 SkillLoader 替代 |
| `tests/conftest.py` | 适配 Skill 加载逻辑 |

### 新增测试

| 文件 | 覆盖 |
|------|------|
| `tests/test_skills.py` | Skill 解析、匹配、拼接、错误处理 |

## 不在本次范围

- 前端 UI 展示已激活 Skill
- Skill 启用/禁用 API
- 工作流编排（方案 2，记为后续 task）
- 动态安装/卸载 Skill
- LLM 意图识别匹配（替代关键词匹配）

## 验收标准

1. Agent 启动后自动加载 `skills/` 下所有 Skill
2. 用户消息包含关键词时，对应 Skill 指令被注入 system prompt
3. 无关键词匹配时，只有 general 指令
4. 现有 e2e 测试全部通过（行为不变）
5. 新增 Skill 系统单元测试覆盖：加载、匹配、拼接、错误场景
