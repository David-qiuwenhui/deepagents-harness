from datetime import datetime

from langchain_core.tools import tool
from langgraph.config import get_store


NAMESPACE = ("memories",)


def _get_store():
    """获取 LangGraph Store 实例，仅在 Agent 图执行期间可用"""
    store = get_store()
    if store is None:
        raise RuntimeError("Store 未配置，请确保 create_deep_agent 传入 store 参数")
    return store


@tool
def save_memory(key: str, content: str) -> str:
    """保存一条记忆。key 是记忆的标识（如 'user_name'、'favorite_color'），content 是具体内容。
    当用户告诉你重要信息（偏好、个人资料、关键事实）时应主动调用此工具保存。"""
    try:
        store = _get_store()
        saved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        store.put(NAMESPACE, key, {"content": content, "saved_at": saved_at})
        return f"已保存记忆 [{key}]: {content}"
    except RuntimeError as e:
        return f"记忆服务不可用: {e}"
    except Exception as e:
        return f"保存失败: {e}"


@tool
def recall_memory(query: str) -> str:
    """搜索已保存的记忆。query 为搜索关键词，会匹配记忆的 key 和内容。
    当需要回忆之前保存的信息时应调用此工具。"""
    try:
        store = _get_store()
        items = store.search(NAMESPACE)
        if not items:
            return "暂无已保存的记忆"

        query_lower = query.lower()
        matched = []
        for item in items:
            key_match = query_lower in item.key.lower()
            content_match = query_lower in str(item.value).lower()
            if key_match or content_match:
                content = item.value.get("content", "")
                saved_at = item.value.get("saved_at", "未知时间")
                matched.append(f"[{item.key}] {content}（保存于 {saved_at}）")

        if matched:
            return f"找到 {len(matched)} 条相关记忆:\n" + "\n".join(matched)

        all_items = []
        for item in items:
            content = item.value.get("content", "")
            all_items.append(f"[{item.key}] {content}")
        return f"未找到与「{query}」直接相关的记忆。当前所有记忆:\n" + "\n".join(all_items)
    except RuntimeError as e:
        return f"记忆服务不可用: {e}"
    except Exception as e:
        return f"检索失败: {e}"


@tool
def list_memories() -> str:
    """列出所有已保存的记忆。"""
    try:
        store = _get_store()
        items = store.search(NAMESPACE)
        if not items:
            return "暂无已保存的记忆"
        lines = []
        for item in items:
            content = item.value.get("content", "")
            saved_at = item.value.get("saved_at", "未知时间")
            lines.append(f"[{item.key}] {content}（{saved_at}）")
        return f"共 {len(lines)} 条记忆:\n" + "\n".join(lines)
    except RuntimeError as e:
        return f"记忆服务不可用: {e}"
    except Exception as e:
        return f"列出失败: {e}"
