from deepagents import create_deep_agent
from langgraph.store.memory import InMemoryStore

from agent.config import get_model
from agent.memory_tools import list_memories, recall_memory, save_memory
from agent.tools import calculate, get_current_time, list_directory, read_file, web_search, write_file


def main():
    model = get_model()
    tools = [
        get_current_time, calculate, web_search,
        read_file, write_file, list_directory,
        save_memory, recall_memory, list_memories,
    ]

    agent = create_deep_agent(
        model=model,
        tools=tools,
        system_prompt="你是一个有用的助手。你可以使用工具来完成任务。请用中文回答。",
        store=InMemoryStore(),
    )

    print("=" * 60)
    print("DeepAgents 最小化 Agent Demo (GLM-5.1)")
    print("=" * 60)

    result = agent.invoke(
        {"messages": [{"role": "user", "content": "现在是几点？帮我算一下 15 * 37 + 128 的结果"}]}
    )

    print("\nAgent 响应:")
    print("-" * 60)
    print(result["messages"][-1].content)
    print("-" * 60)


if __name__ == "__main__":
    main()
