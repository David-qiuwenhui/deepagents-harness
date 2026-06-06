# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (uses uv)
uv sync

# Run web server (FastAPI + SSE streaming)
uv run uvicorn agent.server:app --host 0.0.0.0 --port 8000

# Run CLI demo (non-web, single-turn)
uv run python -m agent.main

# Run from project root entry point
uv run python main.py
```

## Environment

Requires `.env` with `ZHIPUAI_API_KEY`. Copy from `.env.example`.

## Architecture

**Stack**: DeepAgents (LangGraph) + LangChain OpenAI + FastAPI + Zhipu GLM-5.1

**API endpoint**: Zhipu Coding Plan API at `https://open.bigmodel.cn/api/coding/paas/v4/` (NOT the standard `/api/paas/v4/`). Uses OpenAI-compatible interface via `langchain_openai.ChatOpenAI`.

**Key files**:

- `src/agent/config.py` — Model initialization (GLM-5.1 via ChatOpenAI)
- `src/agent/tools.py` — `@tool` decorated functions registered with the agent. Add new tools here.
- `src/agent/server.py` — FastAPI app: `GET /` serves the chat UI, `POST /api/chat` handles SSE streaming
- `src/agent/main.py` — CLI entry point for testing without the web UI
- `src/agent/static/index.html` — Single-file chat UI (Claude-inspired styling, stream inspector with timeline/stats/step-through/protocol card)

**Data flow**:

1. Frontend POSTs `{message, history}` to `/api/chat`
2. Server builds `HumanMessage`/`AIMessage` history, creates a fresh `create_deep_agent()` per request
3. Agent streams via `astream_events(version="v2")`, server yields SSE frames: `token`, `tool_call`, `tool_result`, `done`, `error`
4. Frontend `ReadableStream` parses SSE, renders tokens incrementally and tool events as cards

**SSE event types** emitted by server:

- `token` — LLM text chunk (`content` field)
- `tool_call` — Tool invoked (`name`, `args`)
- `tool_result` — Tool output (`name`, `result`)
- `done` — Stream complete
- `error` — Error message

**Package layout**: `src/agent/` is the Python package, installed as editable via setuptools (`[tool.setuptools.packages.find] where = ["src"]`).

## Notes

- GLM-5.1 supports `reasoning_content` (chain-of-thought) but `langchain-openai` drops this field. To surface it, bypass LangChain or parse raw API responses.
- The web UI is a single HTML file with all CSS/JS inline — no build step needed.
- Each chat request creates a new agent instance. Conversation history is managed client-side and sent with each request.
