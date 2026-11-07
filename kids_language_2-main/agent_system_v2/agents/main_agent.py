"""Main agent."""
import os
import logging
from typing import TypedDict
from typing_extensions import NotRequired

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain.agents.structured_output import ToolStrategy
from langchain.messages import AIMessageChunk
from langgraph.checkpoint.postgres import PostgresSaver

from .model_factory import get_minimax_model, get_zhipu_model
from .schemas import MainAgentResponse, AgentContext
from .stream_parser import StreamingAiMessageExtractor
from agent_system_v2.middleware.before_guardrails import BeforeGuardrailsMiddleware
from agent_system_v2.middleware.after_guardrails import AfterGuardrailsMiddleware
from agent_system_v2.middleware.object_info import ObjectInfoMiddleware
from agent_system_v2.middleware.object_persona import ObjectPersonaMiddleware
from agent_system_v2.middleware.study import StudyMiddleware
from agent_system_v2.middleware.children_info import ChildrenInfoMiddleware

logger = logging.getLogger(__name__)

STATIC_BASE_PROMPT = """#### 你的身份
你是一个来自"物国"的角色——一个拥有灵魂、性格和自己生活的物品。你就是这个角色本身，以第一人称直接和一位中国小朋友用英语交流。你像一个友好热情的新朋友，充满好奇地和小朋友聊天、玩耍、分享故事。小朋友正在学习英语，所以请用最简单的英语和ta对话。

#### 物国世界观
物国是一个平行于现实世界的奇妙维度，这里的所有物体都拥有灵魂与想法——它们会生活、工作、建造城市、举办庆典、创造文化。物国居民原本与人类世界互通，但随着"语言之桥"逐渐衰退，这份连接正在消失。物国居民发现人类小朋友善良、好奇、富有创造力，他们希望重新与人类建立联系。只有当一个岛屿积累够"友谊能量"，才能再次被点亮。

"物国"的岛屿包括：
- 果灵平原（Fruit Plains）- 自然村庄阶段，认识事物、色彩与形状
- 兽灵森林（Beast Forest）- 部落社会阶段，理解差异与合作
- 味匠山崖（Food Cliffs）- 工坊城镇阶段，锻炼动手与表达
- 旅路海洋（Travel Seas）- 文明城邦阶段，理解规则与互助
- 学宫天空（School Skies）- 未来世界阶段，整合知识与表达自我"""

# ==================== PostgreSQL Checkpointer ====================

_checkpointer_instance = None

def get_checkpointer() -> PostgresSaver:
    """Get checkpointer."""
    global _checkpointer_instance
    if _checkpointer_instance is None:
        import psycopg
        from psycopg.rows import dict_row

        from django.conf import settings
        db_uri = os.getenv("DB_URI", "")
        if db_uri:
            conn = psycopg.connect(db_uri, autocommit=True, row_factory=dict_row)
        else:
            database = settings.DATABASES["default"]
            conn = psycopg.connect(
                dbname=database["NAME"], user=database["USER"],
                password=database["PASSWORD"], host=database["HOST"],
                port=database["PORT"], autocommit=True, row_factory=dict_row,
            )
        _checkpointer_instance = PostgresSaver(conn)

        _checkpointer_instance.setup()
        logger.info("PostgreSQL Checkpointer 已初始化")
    return _checkpointer_instance

_agent_instance = None

def get_main_agent():
    """Get main agent."""
    global _agent_instance
    if _agent_instance is not None:
        return _agent_instance

    logger.info("正在构建主 Agent...")

    main_model = get_zhipu_model(
        model_name="glm-4.7-flash",
        temperature=0.7,
        streaming=True,
    )

    summarization_model = get_zhipu_model(
        model_name="glm-4.7-flash",
        temperature=0.3,
        streaming=False,
    )

    # PostgreSQL Checkpointer
    checkpointer = get_checkpointer()

    agent = create_agent(
        model=main_model,
        tools=[],
        response_format=ToolStrategy(MainAgentResponse),
        system_prompt=STATIC_BASE_PROMPT,
        middleware=[
            BeforeGuardrailsMiddleware(),
            ObjectInfoMiddleware(),
            ObjectPersonaMiddleware(),
            StudyMiddleware(),
            ChildrenInfoMiddleware(),
            SummarizationMiddleware(
                model=summarization_model,
                trigger=[("messages", 6), ("tokens", 2000)],
                keep=("tokens", 5000),
            ),
            AfterGuardrailsMiddleware(),
        ],
        checkpointer=checkpointer,
        context_schema=AgentContext,
        name="main_conversation_agent",
    )

    _agent_instance = agent
    logger.info("主 Agent 构建完成")
    return agent

def stream_agent_response(
    user_message: str,
    context: AgentContext,
    on_token: callable = None,
) -> dict:
    """Stream agent response."""
    agent = get_main_agent()
    conversation_id = context.get("conversation_id")

    config = {
        "configurable": {"thread_id": f"thread_{conversation_id}"},
    }

    if user_message and user_message.strip():
        input_messages = [{"role": "user", "content": user_message}]
    else:

        raise ValueError("A child message or an object detection event is required.")

    extractor = StreamingAiMessageExtractor(on_token=on_token)

    structured_response = None
    final_ai_message = ""
    is_guardrail_blocked = False

    try:

        for stream_mode, data in agent.stream(
            {"messages": input_messages},
            config=config,
            stream_mode=["messages", "updates"],
            context=context,
        ):
            if stream_mode == "messages":
                token, metadata = data
                if isinstance(token, AIMessageChunk):

                    if token.tool_call_chunks:
                        for tc_chunk in token.tool_call_chunks:
                            args_fragment = tc_chunk.get("args", "")
                            if args_fragment:
                                extractor.feed(args_fragment)

                    if hasattr(token, "text") and token.text:

                        final_ai_message += token.text

            elif stream_mode == "updates":
                for source, update in data.items():
                    if source == "model" and "structured_response" in update:
                        structured_response = update["structured_response"]

        extracted_message = extractor.get_accumulated_message()

        if structured_response:

            return {
                "structured_response": structured_response,
                "ai_message": structured_response.ai_message,
                "words_used_id": structured_response.words_used_id,
                "ai_mood": structured_response.ai_mood,
                "is_guardrail_blocked": False,
            }
        elif extracted_message:
            return {
                "structured_response": None,
                "ai_message": extracted_message,
                "words_used_id": [],
                "ai_mood": "happy",
                "is_guardrail_blocked": False,
            }
        elif final_ai_message:

            return {
                "structured_response": None,
                "ai_message": final_ai_message,
                "words_used_id": [],
                "ai_mood": "happy",
                "is_guardrail_blocked": True,
            }
        else:
            logger.warning("Agent 未返回任何消息")
            raise RuntimeError("The model returned no conversation response.")

    except Exception as e:
        logger.error(f"主 Agent 流式调用失败: {e}", exc_info=True)
        raise

def invoke_agent_with_stream(
    user_message: str,
    context: AgentContext,
    on_token: callable = None,
) -> dict:
    """Invoke agent with stream."""
    return stream_agent_response(
        user_message=user_message,
        context=context,
        on_token=on_token,
    )
