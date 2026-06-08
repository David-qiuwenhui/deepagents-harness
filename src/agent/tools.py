import ast
import operator
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
    if not target.is_relative_to(WORK_DIR.resolve()):
        raise ValueError(f"路径超出允许范围: {filepath}")
    return target


@tool
def get_current_time() -> str:
    """获取当前日期和时间"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


def _safe_eval(expression: str) -> float:
    tree = ast.parse(expression, mode="eval")

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"不支持的常量类型: {type(node.value).__name__}")
        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in _SAFE_OPS:
                raise ValueError(f"不支持的运算符: {op_type.__name__}")
            return _SAFE_OPS[op_type](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in _SAFE_OPS:
                raise ValueError(f"不支持的一元运算符: {op_type.__name__}")
            return _SAFE_OPS[op_type](_eval(node.operand))
        raise ValueError(f"不支持的表达式节点: {type(node).__name__}")

    return _eval(tree)


@tool
def calculate(expression: str) -> str:
    """计算数学表达式并返回结果。例如: '2 + 3 * 4'"""
    try:
        result = _safe_eval(expression)
        return f"{expression} = {result}"
    except (ValueError, SyntaxError, ZeroDivisionError, OverflowError) as e:
        return f"计算错误: {e}"


_tavily_client: TavilyClient | None = None


def _get_tavily_client() -> TavilyClient | None:
    global _tavily_client
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return None
    if _tavily_client is None:
        _tavily_client = TavilyClient(api_key=api_key)
    return _tavily_client


@tool
def web_search(query: str) -> str:
    """搜索互联网获取最新信息。适用于需要实时资讯、事实查询、新闻动态的场景。
    query: 搜索关键词，支持中英文"""
    client = _get_tavily_client()
    if not client:
        return "错误：未配置 TAVILY_API_KEY，无法使用搜索功能"

    try:
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
            prefix = "[DIR]  " if item.is_dir() else "[FILE] "
            lines.append(f"{prefix}{item.name}")
        return "\n".join(lines) if lines else "目录为空"
    except ValueError as e:
        return f"错误: {e}"
    except Exception as e:
        return f"列出失败: {e}"
