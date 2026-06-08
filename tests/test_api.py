"""API 端点 e2e 测试

覆盖: health, auth, 首页, chat SSE 流
"""

import json
from unittest.mock import patch

import pytest

from conftest import get_auth_token, make_agent_events


class TestHealthEndpoint:
    async def test_health_returns_ok(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    async def test_health_reflects_api_key(self, client):
        resp = await client.get("/api/health")
        assert resp.json()["api_key_configured"] is True

    async def test_health_no_api_key(self, client, monkeypatch):
        import agent.server as srv
        monkeypatch.setattr(srv, "ZHIPUAI_API_KEY", "")
        resp = await client.get("/api/health")
        assert resp.json()["api_key_configured"] is False

    async def test_health_reflects_password(self, client):
        resp = await client.get("/api/health")
        assert resp.json()["password_configured"] is True

    async def test_health_no_password(self, client, monkeypatch):
        import agent.server as srv
        monkeypatch.setattr(srv, "ACCESS_PASSWORD", "")
        resp = await client.get("/api/health")
        assert resp.json()["password_configured"] is False


class TestAuthFlow:
    async def test_login_success(self, client):
        resp = await client.post("/api/auth", json={"password": "test-password"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["token"]) == 64

    async def test_login_wrong_password(self, client):
        resp = await client.post("/api/auth", json={"password": "wrong"})
        assert resp.status_code == 401
        assert resp.json()["success"] is False

    async def test_login_missing_password(self, client):
        resp = await client.post("/api/auth", json={})
        assert resp.status_code == 401

    async def test_auth_check_with_valid_token(self, client):
        token = await get_auth_token(client)
        resp = await client.get("/api/auth/check", headers={"x-auth-token": token})
        assert resp.status_code == 200
        assert resp.json()["authenticated"] is True

    async def test_auth_check_with_invalid_token(self, client):
        resp = await client.get("/api/auth/check", headers={"x-auth-token": "invalid"})
        assert resp.status_code == 401

    async def test_auth_check_no_token(self, client):
        resp = await client.get("/api/auth/check")
        assert resp.status_code == 401

    async def test_auth_skipped_when_no_password(self, client, monkeypatch):
        import agent.server as srv
        monkeypatch.setattr(srv, "ACCESS_PASSWORD", "")
        resp = await client.get("/api/auth/check")
        assert resp.status_code == 200
        assert resp.json()["authenticated"] is True

    async def test_token_usable_for_chat(self, client):
        token = await get_auth_token(client)
        with patch("agent.server.create_deep_agent") as mock_create:
            mock_agent = mock_create.return_value
            mock_agent.astream_events.return_value = make_agent_events(
                [{"type": "token", "content": "你好"}, {"type": "done"}]
            )()
            resp = await client.post(
                "/api/chat",
                json={"message": "hi", "history": []},
                headers={"x-auth-token": token},
            )
            assert resp.status_code == 200


class TestIndexPage:
    async def test_index_returns_html(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "DeepAgents" in resp.text


class TestChatEndpoint:
    async def test_chat_requires_auth(self, client):
        resp = await client.post("/api/chat", json={"message": "hi"})
        assert resp.status_code == 401

    async def test_chat_empty_message(self, authed):
        resp = await authed.post("/api/chat", json={"message": ""})
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/event-stream; charset=utf-8"

    async def test_chat_sse_format(self, authed, mock_agent):
        mock_agent.astream_events.return_value = make_agent_events(
            [{"type": "token", "content": "你好"}, {"type": "done"}]
        )()

        resp = await authed.post("/api/chat", json={"message": "hello"})
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/event-stream; charset=utf-8"
        assert resp.headers["cache-control"] == "no-cache"

        body = await resp.aread()
        text = body.decode("utf-8")
        assert "data:" in text

    async def test_chat_streams_tokens(self, authed, mock_agent):
        mock_agent.astream_events.return_value = make_agent_events(
            [
                {"type": "token", "content": "你"},
                {"type": "token", "content": "好"},
                {"type": "done"},
            ]
        )()

        resp = await authed.post("/api/chat", json={"message": "hi"})
        body = await resp.aread()
        text = body.decode("utf-8")

        token_events = [line for line in text.split("\n") if line.startswith('data: {"type": "token"')]
        assert len(token_events) == 2

        content_1 = json.loads(token_events[0][6:])
        assert content_1["content"] == "你"
        content_2 = json.loads(token_events[1][6:])
        assert content_2["content"] == "好"

    async def test_chat_streams_tool_events(self, authed, mock_agent):
        mock_agent.astream_events.return_value = make_agent_events(
            [
                {"type": "tool_call", "name": "calculate", "input": {"expression": "1+1"}},
                {"type": "tool_result", "name": "calculate", "output": "1+1 = 2"},
                {"type": "token", "content": "结果是2"},
                {"type": "done"},
            ]
        )()

        resp = await authed.post("/api/chat", json={"message": "算一下1+1"})
        body = await resp.aread()
        text = body.decode("utf-8")

        tool_call_events = [line for line in text.split("\n") if '"tool_call"' in line]
        tool_result_events = [line for line in text.split("\n") if '"tool_result"' in line]
        assert len(tool_call_events) == 1
        assert len(tool_result_events) == 1

        call_data = json.loads(tool_call_events[0][6:])
        assert call_data["name"] == "calculate"

    async def test_chat_done_event(self, authed, mock_agent):
        mock_agent.astream_events.return_value = make_agent_events(
            [{"type": "done"}]
        )()

        resp = await authed.post("/api/chat", json={"message": "hi"})
        body = await resp.aread()
        text = body.decode("utf-8")

        done_events = [line for line in text.split("\n") if '"type": "done"' in line]
        assert len(done_events) >= 1

    async def test_chat_ping_at_start(self, authed, mock_agent):
        mock_agent.astream_events.return_value = make_agent_events(
            [{"type": "done"}]
        )()

        resp = await authed.post("/api/chat", json={"message": "hi"})
        body = await resp.aread()
        text = body.decode("utf-8")

        assert ": ping" in text

    async def test_chat_with_history(self, authed, mock_agent):
        mock_agent.astream_events.return_value = make_agent_events(
            [{"type": "token", "content": "继续"}, {"type": "done"}]
        )()

        history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！"},
        ]
        resp = await authed.post(
            "/api/chat",
            json={"message": "继续聊", "history": history},
        )
        assert resp.status_code == 200

    async def test_chat_history_validation_filters_invalid(self, authed, mock_agent):
        mock_agent.astream_events.return_value = make_agent_events(
            [{"type": "token", "content": "ok"}, {"type": "done"}]
        )()

        history = [
            {"role": "user", "content": "valid"},
            {"role": "system", "content": "should be filtered"},
            "not a dict",
            None,
            {"role": "assistant", "content": 123},
            {"role": "user", "content": "also valid"},
        ]
        resp = await authed.post(
            "/api/chat",
            json={"message": "test", "history": history},
        )
        assert resp.status_code == 200

    async def test_chinese_preserved_in_sse(self, authed, mock_agent):
        mock_agent.astream_events.return_value = make_agent_events(
            [{"type": "token", "content": "你好世界"}, {"type": "done"}]
        )()

        resp = await authed.post("/api/chat", json={"message": "你好"})
        body = await resp.aread()
        text = body.decode("utf-8")
        assert "你好世界" in text

    async def test_chat_error_returns_generic_message(self, authed, mock_agent):
        mock_agent.astream_events.side_effect = RuntimeError("LLM connection failed")

        resp = await authed.post("/api/chat", json={"message": "hi"})
        body = await resp.aread()
        text = body.decode("utf-8")

        assert "服务器内部错误" in text
        assert "LLM connection failed" not in text
