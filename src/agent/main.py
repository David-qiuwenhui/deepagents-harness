import logging

from deepagents import create_deep_agent
from langgraph.store.memory import InMemoryStore

from agent.config import get_model
from agent.memory_tools import list_memories, recall_memory, save_memory
from agent.tools import calculate, get_current_time, list_directory, read_file, web_search, write_file
from agent.wiki_tools import ingest_doc, list_wiki, search_wiki

logger = logging.getLogger(__name__)

TOOLS = [
    get_current_time, calculate, web_search,
    read_file, write_file, list_directory,
    save_memory, recall_memory, list_memories,
    ingest_doc, search_wiki, list_wiki,
]


def main():
    logging.basicConfig(level=logging.INFO)

    model = get_model()
    agent = create_deep_agent(
        model=model,
        tools=TOOLS,
        system_prompt="你是一个有用的助手。你可以使用工具来完成任务。请用中文回答。",
        store=InMemoryStore(),
    )

    logger.info("=" * 60)
    logger.info("DeepAgents 最小化 Agent Demo (GLM-5.1)")
    logger.info("=" * 60)

    result = agent.invoke(
        {"messages": [{"role": "user", "content": "现在是几点？帮我算一下 15 * 37 + 128 的结果"}]}
    )

    response = result["messages"][-1].content
    logger.info("Agent 响应:")
    logger.info("-" * 60)
    logger.info(response)
    logger.info("-" * 60)


if __name__ == "__main__":
    main()
