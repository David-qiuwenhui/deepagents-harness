import json
import os
import secrets
from collections.abc import AsyncGenerator
from pathlib import Path

from deepagents import create_deep_agent
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from starlette.responses import JSONResponse
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.store.memory import InMemoryStore

from agent.memory_tools import list_memories, recall_memory, save_memory
from agent.tools import calculate, get_current_time, list_directory, read_file, web_search, write_file

load_dotenv()

app = FastAPI(title="DeepAgents Chat")

ACCESS_PASSWORD = os.environ.get("ACCESS_PASSWORD", "")

_auth_sessions: set[str] = set()


def _check_auth(request: Request) -> None:
    if not ACCESS_PASSWORD:
        return
    token = request.cookies.get("auth_token")
    if token not in _auth_sessions:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.post("/api/auth")
async def authenticate(request: Request):
    body = await request.json()
    password = body.get("password", "")
    if password != ACCESS_PASSWORD:
        return JSONResponse({"success": False, "message": "密码错误"}, status_code=401)
    token = secrets.token_hex(32)
    _auth_sessions.add(token)
    response = JSONResponse({"success": True})
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        secure=bool(ACCESS_PASSWORD),
        max_age=86400 * 30,
        samesite="lax",
    )
    return response


@app.get("/api/auth/check")
async def auth_check(request: Request):
    if not ACCESS_PASSWORD:
        return {"authenticated": True}
    token = request.cookies.get("auth_token")
    if token in _auth_sessions:
        return {"authenticated": True}
    raise HTTPException(status_code=401, detail="Not authenticated")

ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/coding/paas/v4/"
SYSTEM_PROMPT = (
    "你是一个有用的助手。你可以使用工具来完成任务。请用中文回答。\n\n"
    "你拥有长期记忆能力：\n"
    "- 当用户告诉你重要信息（如姓名、偏好、关键事实）时，主动使用 save_memory 工具保存\n"
    "- 当需要回忆之前的信息时，使用 recall_memory 工具搜索\n"
    "- 用户要求列出所有记忆时，使用 list_memories 工具"
)
MEMORY_STORE = InMemoryStore()
TOOLS = [
    get_current_time, calculate, web_search,
    read_file, write_file, list_directory,
    save_memory, recall_memory, list_memories,
]


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


@app.post("/api/chat", dependencies=[Depends(_check_auth)])
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
        store=MEMORY_STORE,
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
