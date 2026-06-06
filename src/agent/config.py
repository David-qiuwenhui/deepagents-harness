import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/coding/paas/v4/"


def get_model(model_name: str = "glm-5.1") -> ChatOpenAI:
    api_key = os.environ.get("ZHIPUAI_API_KEY")
    if not api_key:
        raise ValueError("ZHIPUAI_API_KEY environment variable is required")

    return ChatOpenAI(
        model=model_name,
        base_url=ZHIPU_BASE_URL,
        api_key=api_key,
    )
