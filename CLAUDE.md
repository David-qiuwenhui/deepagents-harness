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

Requires `.env` with `ZHIPUAI_API_KEY` and optionally `TAVILY_API_KEY`, `ACCESS_PASSWORD`. Copy from `.env.example`.

## Architecture

**Stack**: DeepAgents (LangGraph) + LangChain OpenAI + FastAPI + Zhipu GLM-5.1

**API endpoint**: Zhipu Coding Plan API at `https://open.bigmodel.cn/api/coding/paas/v4/` (NOT the standard `/api/paas/v4/`). Uses OpenAI-compatible interface via `langchain_openai.ChatOpenAI`.

**Key files**:

- `src/agent/config.py` — Model initialization (GLM-5.1 via ChatOpenAI)
- `src/agent/tools.py` — Core tools: time, calculate, web_search, file I/O (read/write/list), all sandboxed to `workspace/`
- `src/agent/memory_tools.py` — Long-term memory tools: save_memory, recall_memory, list_memories (backed by LangGraph InMemoryStore)
- `src/agent/wiki_tools.py` — Knowledge base tools: ingest_doc, search_wiki, list_wiki (reads from `workspace/raw/`, writes to `workspace/wiki/`)
- `src/agent/server.py` — FastAPI app: auth system, SSE streaming, health endpoint, static file serving
- `src/agent/main.py` — CLI entry point for testing without the web UI
- `src/agent/static/index.html` — Single-file chat UI (Claude-inspired styling, breathing orb loading, stream inspector)

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

## Authentication

Header-based token auth (no cookies — avoids third-party cookie blocking in iframes):

1. `POST /api/auth` with `{password}` → returns `{token}` (stored in `localStorage`)
2. Subsequent requests send `X-Auth-Token` header via `authFetch()`
3. If `ACCESS_PASSWORD` env var is empty, auth is skipped entirely

## Deployment

Deployed to Hugging Face Spaces (Private Docker Space). Auto-deploy via GitHub Actions on push to `master`.

- **Dockerfile** — Python 3.11-slim, `pip install .`, runs uvicorn on port 7860
- **README.md** — HF Spaces YAML front-matter (sdk: docker, app_port: 7860)
- **`.github/workflows/deploy.yml`** — Syncs master → HF Space on push

Key deployment considerations:
- `pyproject.toml` must include `[tool.setuptools.package-data]` for static files
- SSE streaming needs `: ping\n\n` at stream start to flush proxy buffers
- Auth uses header (X-Auth-Token) not cookies (HF Spaces loads in iframe)
- Use `Depends()` for auth, not `BaseHTTPMiddleware` (breaks SSE streaming)

Full deployment guide: `docs/hf-spaces-deployment.md`
