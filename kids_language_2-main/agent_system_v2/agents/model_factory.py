"""Model factory."""
import os
import logging
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def get_zhipu_model(
    model_name: str = "glm-4.7",
    temperature: float = 0.7,
    streaming: bool = False,
    **kwargs,
) -> ChatOpenAI:
    """Get zhipu model."""
    return ChatOpenAI(
        base_url=os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
        api_key=os.getenv("ZHIPU_API_KEY", ""),
        model=model_name,
        temperature=temperature,
        streaming=streaming,
        **kwargs,
    )

def get_minimax_model(
    model_name: str = "Minimax-M2.1",
    temperature: float = 0.7,
    streaming: bool = True,
    **kwargs,
) -> ChatOpenAI:
    """Get minimax model."""
    return ChatOpenAI(
        base_url=os.getenv("MINIMAX_BASE_URL", ""),
        api_key=os.getenv("MINIMAX_API_KEY", ""),
        model=model_name,
        temperature=temperature,
        streaming=streaming,
        **kwargs,
    )
