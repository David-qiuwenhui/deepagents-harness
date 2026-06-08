"""安全防护专项测试

覆盖: 路径遍历防护, 表达式注入防护, 认证安全, 输入验证
"""

from datetime import datetime, timedelta, timezone

import pytest

from agent.server import SESSION_TTL, _auth_sessions
from agent.tools import _resolve_safe_path, _safe_eval, calculate, read_file, write_file


# --- 路径遍历防护 ---


class TestPathTraversal:
    def test_parent_directory_escape(self, workspace_env):
        with pytest.raises(ValueError, match="超出允许范围"):
            _resolve_safe_path("../etc/passwd")

    def test_deep_parent_escape(self, workspace_env):
        with pytest.raises(ValueError, match="超出允许范围"):
            _resolve_safe_path("a/../../../etc/passwd")

    def test_absolute_path(self, workspace_env):
        with pytest.raises(ValueError, match="超出允许范围"):
            _resolve_safe_path("/etc/passwd")

    def test_absolute_path_root(self, workspace_env):
        with pytest.raises(ValueError, match="超出允许范围"):
            _resolve_safe_path("/")

    def test_dotdot_after_valid_path(self, workspace_env):
        with pytest.raises(ValueError, match="超出允许范围"):
            _resolve_safe_path("valid/../..")

    def test_normal_relative_path(self, workspace_env):
        path = _resolve_safe_path("test.txt")
        assert path.is_relative_to(workspace_env)

    def test_nested_normal_path(self, workspace_env):
        path = _resolve_safe_path("a/b/c.txt")
        assert path.is_relative_to(workspace_env)

    def test_read_file_blocks_traversal(self, workspace_env):
        assert "错误" in read_file.invoke({"filepath": "../etc/passwd"})

    def test_write_file_blocks_traversal(self, workspace_env):
        assert "错误" in write_file.invoke({"filepath": "../tmp/evil.txt", "content": "hack"})


# --- 表达式注入防护 ---


class TestExpressionInjection:
    def test_import_blocked(self):
        assert "计算错误" in calculate.invoke({"expression": "__import__('os')"})

    def test_attribute_access_blocked(self):
        assert "计算错误" in calculate.invoke({"expression": "().__class__"})

    def test_exponentiation_blocked(self):
        assert "计算错误" in calculate.invoke({"expression": "2 ** 10"})

    def test_string_constant_blocked(self):
        assert "计算错误" in calculate.invoke({"expression": "'hello'"})

    def test_function_call_blocked(self):
        assert "计算错误" in calculate.invoke({"expression": "abs(-1)"})

    def test_variable_blocked(self):
        assert "计算错误" in calculate.invoke({"expression": "x"})

    def test_list_subscript_blocked(self):
        assert "计算错误" in calculate.invoke({"expression": "[1,2,3][0]"})

    def test_dunder_blocked(self):
        assert "计算错误" in calculate.invoke({"expression": "__builtins__"})

    def test_safe_eval_basic_math(self):
        assert _safe_eval("2 + 3") == 5

    def test_safe_eval_division(self):
        assert _safe_eval("10 / 3") == pytest.approx(3.333, rel=0.01)

    def test_safe_eval_negative(self):
        assert _safe_eval("-42") == -42


# --- 认证安全 ---


class TestAuthSecurity:
    async def test_expired_token_rejected(self, client):
        token = "test-expired-token"
        _auth_sessions[token] = datetime.now(timezone.utc) - SESSION_TTL - timedelta(seconds=1)

        resp = await client.get("/api/auth/check", headers={"x-auth-token": token})
        assert resp.status_code == 401

    async def test_valid_token_within_ttl(self, client):
        token = "test-valid-token"
        _auth_sessions[token] = datetime.now(timezone.utc)

        resp = await client.get("/api/auth/check", headers={"x-auth-token": token})
        assert resp.status_code == 200

    async def test_expired_token_cleaned_up(self, client):
        expired_token = "expired"
        valid_token = "valid"
        _auth_sessions[expired_token] = datetime.now(timezone.utc) - timedelta(hours=25)
        _auth_sessions[valid_token] = datetime.now(timezone.utc)

        await client.get("/api/auth/check", headers={"x-auth-token": valid_token})

        assert expired_token not in _auth_sessions
        assert valid_token in _auth_sessions

    async def test_chat_rejects_expired_token(self, client):
        token = "expired-chat-token"
        _auth_sessions[token] = datetime.now(timezone.utc) - timedelta(hours=25)

        resp = await client.post(
            "/api/chat",
            json={"message": "hi"},
            headers={"x-auth-token": token},
        )
        assert resp.status_code == 401

    async def test_no_password_allows_all(self, client, monkeypatch):
        import agent.server as srv
        monkeypatch.setattr(srv, "ACCESS_PASSWORD", "")
        resp = await client.post("/api/chat", json={"message": "hi"})
        assert resp.status_code != 401


# --- 输入验证 ---


class TestInputValidation:
    async def test_history_truncation(self, authed, mock_agent):
        from conftest import make_agent_events

        mock_agent.astream_events.return_value = make_agent_events([{"type": "done"}])()

        history = [{"role": "user", "content": f"msg{i}"} for i in range(50)]
        resp = await authed.post(
            "/api/chat",
            json={"message": "test", "history": history},
        )
        assert resp.status_code == 200

    async def test_history_non_string_content_filtered(self, authed, mock_agent):
        from conftest import make_agent_events

        mock_agent.astream_events.return_value = make_agent_events([{"type": "done"}])()

        history = [
            {"role": "user", "content": "valid"},
            {"role": "assistant", "content": 12345},
            {"role": "user", "content": "also valid"},
        ]
        resp = await authed.post(
            "/api/chat",
            json={"message": "test", "history": history},
        )
        assert resp.status_code == 200
