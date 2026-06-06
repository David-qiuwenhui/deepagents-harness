import os
from datetime import datetime

from langchain_core.tools import tool
from tavily import TavilyClient


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
