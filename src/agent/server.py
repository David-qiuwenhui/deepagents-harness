import json
import os
from collections.abc import AsyncGenerator
from pathlib import Path

from deepagents import create_deep_agent
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from agent.tools import calculate, get_current_time, web_search

load_dotenv()

app = FastAPI(title="DeepAgents Chat")

ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/coding/paas/v4/"
SYSTEM_PROMPT = "你是一个有用的助手。你可以使用工具来完成任务。请用中文回答。"
TOOLS = [get_current_time, calculate, web_search]


def _get_model() -> ChatOpenAI:
    return ChatOpenAI(
        model="glm-5.1",
        base_url=ZHIPU_BASE_URL,
        api_key=os.environ["ZHIPUAI_API_KEY"],
    )


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path(__file__).parent / "static" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.post("/api/chat")
async def chat(request: Request) -> StreamingResponse:
    body = await request.json()
    user_message = body.get("message", "")
    history = body.get("history", [])

    if not user_message:
        return StreamingResponse(
            iter(["data: " + json.dumps({"type": "error", "message": "请输入消息"}) + "\n\n"]),
            media_type="text/event-stream",
        )

    messages = []
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=user_message))

    agent = create_deep_agent(
        model=_get_model(),
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
    )

    async def generate() -> AsyncGenerator[str, None]:
        try:
            async for event in agent.astream_events(
                {"messages": messages},
                version="v2",
            ):
                kind = event["event"]

                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    content = getattr(chunk, "content", None)
                    if content and isinstance(content, str):
                        yield f"data: {json.dumps({'type': 'token', 'content': content}, ensure_ascii=False)}\n\n"

                elif kind == "on_tool_start":
                    yield f"data: {json.dumps({'type': 'tool_call', 'name': event['name'], 'args': str(event['data'].get('input', {}))}, ensure_ascii=False)}\n\n"

                elif kind == "on_tool_end":
                    yield f"data: {json.dumps({'type': 'tool_result', 'name': event['name'], 'result': str(event['data'].get('output', ''))}, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
