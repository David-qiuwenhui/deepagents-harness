import os
from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage

import agent.server as server_module
import agent.tools as tools_module
from agent.server import _auth_sessions, app


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    """直接 patch 模块级变量（它们在 import 时已从环境变量读取）"""
    monkeypatch.setattr(server_module, "ZHIPUAI_API_KEY", "test-key-for-e2e")
    monkeypatch.setattr(server_module, "ACCESS_PASSWORD", "test-password")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    tools_module._tavily_client = None


@pytest.fixture(autouse=True)
def _clear_auth_sessions():
    _auth_sessions.clear()
    yield
    _auth_sessions.clear()


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    raw = tmp_path / "raw"
    wiki = tmp_path / "wiki"
    raw.mkdir()
    wiki.mkdir()
    (wiki / "index.md").write_text("# 知识库索引\n", encoding="utf-8")
    (wiki / "log.md").write_text("# 变更日志\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def workspace_env(workspace: Path, monkeypatch):
    """设置 WORK_DIR 指向临时目录"""
    monkeypatch.setattr(tools_module, "WORK_DIR", workspace)
    return workspace


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def get_auth_token(client: AsyncClient, password: str = "test-password") -> str:
    resp = await client.post("/api/auth", json={"password": password})
    data = resp.json()
    return data["token"]


@pytest_asyncio.fixture
async def authed(client: AsyncClient) -> AsyncClient:
    token = await get_auth_token(client)
    client.headers["x-auth-token"] = token
    return client


def make_agent_events(events: list[dict]):
    """构建 mock astream_events 异步生成器"""

    async def _stream(*args, **kwargs):
        for evt in events:
            t = evt["type"]
            if t == "token":
                chunk = AIMessage(content=evt["content"])
                yield {"event": "on_chat_model_stream", "data": {"chunk": chunk}}
            elif t == "tool_call":
                yield {
                    "event": "on_tool_start",
                    "name": evt["name"],
                    "data": {"input": evt.get("input", {})},
                }
            elif t == "tool_result":
                yield {
                    "event": "on_tool_end",
                    "name": evt["name"],
                    "data": {"output": evt.get("output", "")},
                }

    return _stream


@pytest.fixture
def mock_agent():
    with patch("agent.server.create_deep_agent") as mock_create:
        agent_instance = MagicMock()
        mock_create.return_value = agent_instance
        yield agent_instance
