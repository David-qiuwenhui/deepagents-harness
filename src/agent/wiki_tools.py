from langchain_core.tools import tool

from agent.tools import _resolve_safe_path


@tool
def ingest_doc(filepath: str) -> str:
    """读取 raw/ 目录下的原始文档内容，用于知识库摄入。
    filepath 为相对于 raw/ 目录的路径，如 '系统操作指南.md'。
    读取后请理解文档内容，提取关键信息，整理为 Wiki 页面写入 wiki/ 目录，
    并更新 wiki/index.md 索引和 wiki/log.md 变更日志。"""
    try:
        target = _resolve_safe_path(f"raw/{filepath}")
        if not target.exists():
            return f"文件不存在: raw/{filepath}"
        if not target.is_file():
            return f"不是文件: raw/{filepath}"
        content = target.read_text(encoding="utf-8")
        return f"文档内容如下，请整理为 Wiki 页面：\n\n{content}"
    except ValueError as e:
        return f"错误: {e}"
    except Exception as e:
        return f"读取失败: {e}"


@tool
def search_wiki(query: str) -> str:
    """搜索知识库 Wiki 页面。query 为搜索关键词。
    会先扫描 index.md 中的页面标题和摘要，匹配后读取对应的 Wiki 页面内容返回。"""
    try:
        index_path = _resolve_safe_path("wiki/index.md")
        if not index_path.exists():
            return "知识库索引不存在，请先通过 ingest_doc 工具摄入文档"

        index_content = index_path.read_text(encoding="utf-8")
        query_lower = query.lower()

        matched_files = []
        for line in index_content.split("\n"):
            line_lower = line.lower()
            if line.startswith("- [") and (query_lower in line_lower):
                start = line.find("](")
                end = line.find(")", start)
                if start != -1 and end != -1:
                    filename = line[start + 2 : end]
                    matched_files.append((line, filename))

        if not matched_files:
            return f"未找到与「{query}」直接匹配的 Wiki 页面。当前索引：\n\n{index_content}"

        results = []
        for entry_line, filename in matched_files:
            page_path = _resolve_safe_path(f"wiki/{filename}")
            if page_path.exists():
                page_content = page_path.read_text(encoding="utf-8")
                results.append(f"## {entry_line}\n\n{page_content}")

        return "\n\n---\n\n".join(results)
    except ValueError as e:
        return f"错误: {e}"
    except Exception as e:
        return f"搜索失败: {e}"


@tool
def list_wiki() -> str:
    """列出知识库中所有 Wiki 页面的索引概览。"""
    try:
        index_path = _resolve_safe_path("wiki/index.md")
        if not index_path.exists():
            return "知识库索引不存在"
        return index_path.read_text(encoding="utf-8")
    except ValueError as e:
        return f"错误: {e}"
    except Exception as e:
        return f"读取失败: {e}"
