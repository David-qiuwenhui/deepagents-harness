import os
from datetime import datetime
from pathlib import Path

from langchain_core.tools import tool
from tavily import TavilyClient

# 文件工具允许读写的根目录，默认为项目下的 workspace/
WORK_DIR = Path(os.environ.get("AGENT_WORK_DIR", Path(__file__).parent.parent.parent / "workspace"))


def _resolve_safe_path(filepath: str) -> Path:
    """解析路径并确保在 WORK_DIR 内，防止路径遍历攻击"""
    target = (WORK_DIR / filepath).resolve()
    if not str(target).startswith(str(WORK_DIR.resolve())):
        raise ValueError(f"路径超出允许范围: {filepath}")
    return target


@tool
def get_current_time() -> str:
    """获取当前日期和时间"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool
def calculate(expression: str) -> str:
    """计算数学表达式并返回结果。例如: '2 + 3 * 4'"""
    allowed = set("0123456789+-*/().% ")
    if not all(c in allowed for c in expression):
        return "错误：表达式包含不允许的字符"
    try:
        result = eval(expression)  # noqa: S307
        return f"{expression} = {result}"
    except Exception as e:
        return f"计算错误: {e}"


@tool
def web_search(query: str) -> str:
    """搜索互联网获取最新信息。适用于需要实时资讯、事实查询、新闻动态的场景。
    query: 搜索关键词，支持中英文"""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "错误：未配置 TAVILY_API_KEY，无法使用搜索功能"

    try:
        client = TavilyClient(api_key=api_key)
        results = client.search(query, max_results=5, topic="general")
        entries = []
        for r in results.get("results", []):
            title = r.get("title", "无标题")
            url = r.get("url", "")
            content = r.get("content", "")
            entries.append(f"【{title}】\n来源: {url}\n{content}")
        return "\n\n---\n\n".join(entries) if entries else "未找到相关结果"
    except Exception as e:
        return f"搜索失败: {e}"


@tool
def read_file(filepath: str) -> str:
    """读取文件内容。filepath 为相对于工作目录的路径，如 'notes/todo.md'"""
    try:
        target = _resolve_safe_path(filepath)
        if not target.exists():
            return f"文件不存在: {filepath}"
        if not target.is_file():
            return f"不是文件: {filepath}"
        content = target.read_text(encoding="utf-8")
        return content
    except ValueError as e:
        return f"错误: {e}"
    except Exception as e:
        return f"读取失败: {e}"


@tool
def write_file(filepath: str, content: str) -> str:
    """写入文件。filepath 为相对于工作目录的路径，如 'notes/todo.md'。会自动创建不存在的目录"""
    try:
        target = _resolve_safe_path(filepath)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"已写入 {filepath}（{len(content)} 字符）"
    except ValueError as e:
        return f"错误: {e}"
    except Exception as e:
        return f"写入失败: {e}"


@tool
def list_directory(dirpath: str = ".") -> str:
    """列出目录下的文件和子目录。dirpath 为相对于工作目录的路径，默认为根目录"""
    try:
        target = _resolve_safe_path(dirpath)
        if not target.exists():
            return f"目录不存在: {dirpath}"
        if not target.is_dir():
            return f"不是目录: {dirpath}"
        items = sorted(target.iterdir())
        lines = []
        for item in items:
            prefix = "📁 " if item.is_dir() else "📄 "
            lines.append(f"{prefix}{item.name}")
        return "\n".join(lines) if lines else "目录为空"
    except ValueError as e:
        return f"错误: {e}"
    except Exception as e:
        return f"列出失败: {e}"
