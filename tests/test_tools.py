"""工具函数集成测试

覆盖: calculate, get_current_time, file I/O, wiki tools, memory tools
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langgraph.store.memory import InMemoryStore

from agent.memory_tools import list_memories, recall_memory, save_memory
from agent.tools import (
    calculate,
    get_current_time,
    list_directory,
    read_file,
    web_search,
    write_file,
)
from agent.wiki_tools import ingest_doc, list_wiki, search_wiki


# --- calculate ---


class TestCalculate:
    def test_addition(self):
        assert "5" in calculate.invoke({"expression": "2 + 3"})

    def test_subtraction(self):
        assert "6" in calculate.invoke({"expression": "10 - 4"})

    def test_multiplication(self):
        assert "21" in calculate.invoke({"expression": "3 * 7"})

    def test_division(self):
        assert "2.5" in calculate.invoke({"expression": "10 / 4"})

    def test_modulo(self):
        assert "1" in calculate.invoke({"expression": "10 % 3"})

    def test_unary_negation(self):
        assert "-5" in calculate.invoke({"expression": "-5"})

    def test_operator_precedence(self):
        assert "14" in calculate.invoke({"expression": "2 + 3 * 4"})

    def test_float_expression(self):
        assert "6.28" in calculate.invoke({"expression": "3.14 * 2"})

    def test_complex_expression(self):
        assert "683" in calculate.invoke({"expression": "15 * 37 + 128"})

    def test_division_by_zero(self):
        assert "计算错误" in calculate.invoke({"expression": "1 / 0"})

    def test_empty_expression(self):
        assert "计算错误" in calculate.invoke({"expression": ""})


# --- get_current_time ---


class TestGetCurrentTime:
    def test_returns_valid_format(self):
        result = get_current_time.invoke({})
        parsed = datetime.strptime(result, "%Y-%m-%d %H:%M:%S")
        assert parsed is not None

    def test_returns_current_date(self):
        result = get_current_time.invoke({})
        assert datetime.now().strftime("%Y-%m-%d") in result


# --- file tools ---


class TestFileTools:
    def test_write_and_read(self, workspace_env):
        write_file.invoke({"filepath": "test.txt", "content": "hello"})
        assert read_file.invoke({"filepath": "test.txt"}) == "hello"

    def test_write_creates_subdirectories(self, workspace_env):
        write_file.invoke({"filepath": "a/b/c.txt", "content": "deep"})
        assert read_file.invoke({"filepath": "a/b/c.txt"}) == "deep"

    def test_write_returns_confirmation(self, workspace_env):
        result = write_file.invoke({"filepath": "note.md", "content": "test content"})
        assert "已写入" in result
        assert "12 字符" in result

    def test_read_nonexistent(self, workspace_env):
        assert "文件不存在" in read_file.invoke({"filepath": "nope.txt"})

    def test_read_directory(self, workspace_env):
        (workspace_env / "adir").mkdir()
        assert "不是文件" in read_file.invoke({"filepath": "adir"})

    def test_list_directory(self, workspace_env):
        (workspace_env / "sub").mkdir()
        (workspace_env / "file1.txt").write_text("a")
        # 排除 workspace fixture 创建的 raw/wiki 目录
        result = list_directory.invoke({"dirpath": "."})
        assert "[DIR]" in result
        assert "[FILE] file1.txt" in result

    def test_list_empty_directory(self, workspace_env):
        (workspace_env / "empty").mkdir()
        assert "目录为空" in list_directory.invoke({"dirpath": "empty"})

    def test_list_nonexistent_directory(self, workspace_env):
        assert "目录不存在" in list_directory.invoke({"dirpath": "nonexistent"})

    def test_write_unicode_content(self, workspace_env):
        content = "你好世界"
        write_file.invoke({"filepath": "unicode.txt", "content": content})
        assert read_file.invoke({"filepath": "unicode.txt"}) == content

    def test_write_overwrites_existing(self, workspace_env):
        write_file.invoke({"filepath": "ow.txt", "content": "old"})
        write_file.invoke({"filepath": "ow.txt", "content": "new"})
        assert read_file.invoke({"filepath": "ow.txt"}) == "new"


# --- wiki tools ---


class TestWikiTools:
    def test_ingest_md_file(self, workspace_env):
        (workspace_env / "raw" / "guide.md").write_text("这是操作指南", encoding="utf-8")
        assert "这是操作指南" in ingest_doc.invoke({"filepath": "guide.md"})

    def test_ingest_txt_file(self, workspace_env):
        (workspace_env / "raw" / "data.txt").write_text("plain text", encoding="utf-8")
        assert "plain text" in ingest_doc.invoke({"filepath": "data.txt"})

    def test_ingest_disallowed_extension(self, workspace_env):
        (workspace_env / "raw" / "script.py").write_text("print('hi')", encoding="utf-8")
        result = ingest_doc.invoke({"filepath": "script.py"})
        assert "不支持的文件类型" in result

    def test_ingest_nonexistent(self, workspace_env):
        assert "文件不存在" in ingest_doc.invoke({"filepath": "missing.md"})

    def test_ingest_case_insensitive_ext(self, workspace_env):
        (workspace_env / "raw" / "doc.MD").write_text("uppercase", encoding="utf-8")
        assert "uppercase" in ingest_doc.invoke({"filepath": "doc.MD"})

    def test_search_wiki_match(self, workspace_env):
        (workspace_env / "wiki" / "login.md").write_text("输入密码即可", encoding="utf-8")
        (workspace_env / "wiki" / "index.md").write_text(
            "- [登录指南](login.md) — 如何登录\n", encoding="utf-8"
        )
        assert "输入密码即可" in search_wiki.invoke({"query": "登录"})

    def test_search_wiki_no_match(self, workspace_env):
        (workspace_env / "wiki" / "index.md").write_text(
            "- [指南](guide.md) — 说明\n", encoding="utf-8"
        )
        assert "未找到" in search_wiki.invoke({"query": "不存在的"})

    def test_search_wiki_no_index(self, workspace_env):
        (workspace_env / "wiki" / "index.md").unlink()
        assert "索引不存在" in search_wiki.invoke({"query": "anything"})

    def test_list_wiki(self, workspace_env):
        (workspace_env / "wiki" / "index.md").write_text("- [页面A](a.md)", encoding="utf-8")
        assert "页面A" in list_wiki.invoke({})

    def test_list_wiki_no_index(self, workspace_env):
        (workspace_env / "wiki" / "index.md").unlink()
        assert "索引不存在" in list_wiki.invoke({})


# --- memory tools ---


class TestMemoryTools:
    @pytest.fixture(autouse=True)
    def _setup_store(self):
        self.store = InMemoryStore()

    def _run(self, tool_func, tool_input: dict) -> str:
        with patch("agent.memory_tools.get_store", return_value=self.store):
            return tool_func.invoke(tool_input)

    def test_save_and_recall(self):
        self._run(save_memory, {"key": "user_name", "content": "小明"})
        assert "小明" in self._run(recall_memory, {"query": "user_name"})

    def test_save_and_list(self):
        self._run(save_memory, {"key": "color", "content": "blue"})
        result = self._run(list_memories, {})
        assert "color" in result
        assert "blue" in result

    def test_recall_no_match(self):
        self._run(save_memory, {"key": "city", "content": "北京"})
        assert "未找到" in self._run(recall_memory, {"query": "food"})

    def test_recall_empty_store(self):
        assert "暂无" in self._run(recall_memory, {"query": "anything"})

    def test_list_empty_store(self):
        assert "暂无" in self._run(list_memories, {})

    def test_save_confirmation(self):
        result = self._run(save_memory, {"key": "k", "content": "v"})
        assert "已保存" in result
        assert "k" in result

    def test_multiple_memories(self):
        for i in range(3):
            self._run(save_memory, {"key": f"m{i}", "content": str(i)})
        assert "共 3 条记忆" in self._run(list_memories, {})


# --- web_search (mocked) ---


class TestWebSearch:
    @pytest.fixture(autouse=True)
    def _reset_client(self):
        import agent.tools
        yield
        agent.tools._tavily_client = None

    def test_search_without_api_key(self, monkeypatch):
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        result = web_search.invoke({"query": "test"})
        assert "未配置" in result

    def test_search_with_mock(self, monkeypatch):
        mock = MagicMock()
        mock.search.return_value = {
            "results": [{"title": "Test", "url": "https://example.com", "content": "ok"}]
        }
        monkeypatch.setenv("TAVILY_API_KEY", "fake-key")

        import agent.tools
        agent.tools._tavily_client = mock

        result = web_search.invoke({"query": "test"})
        assert "Test" in result
        assert "example.com" in result
