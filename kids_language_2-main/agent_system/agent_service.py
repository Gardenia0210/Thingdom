"""Agent service."""
import os
import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.agents.middleware import dynamic_prompt, ModelRequest
from langchain.messages import HumanMessage
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_openai import ChatOpenAI
from langsmith import traceable
from django.conf import settings
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

LANGCHAIN_TRACING = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
LANGCHAIN_API_KEY = os.getenv("LANGSMITH_API_KEY", "")
LANGCHAIN_PROJECT = os.getenv("LANGSMITH_PROJECT", "kid_language")
LANGCHAIN_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")

if LANGCHAIN_TRACING and LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT
    os.environ["LANGCHAIN_ENDPOINT"] = LANGCHAIN_ENDPOINT
    logger.info(f"LangSmith追踪已启用，项目: {LANGCHAIN_PROJECT}")
else:
    logger.info("LangSmith追踪未启用（未配置API_KEY或TRACING=false）")

class AgentResponse(BaseModel):
    """Agentresponse."""
    object_identification: str = Field(
        description="物体的身份标识。如果输入中已有object_identification，直接使用；如果没有，需要AI根据object_name和island_type创造性地赋予物体一个有趣的身份角色。"
    )
    message: str = Field(
        description="AI生成的英文对话文本，用于与儿童交互。必须使用简单、清晰、符合儿童认知水平的英语表达，语气温暖友好。"
    )
    words_used: list[str] = Field(
        description="在这次对话中使用的单词列表，必须是从learning_requirements中给出的词汇中选择的1-2个单词。"
    )
    part_of_speech: list[str] = Field(
        description="words_used中每个单词对应的词性，顺序与words_used一致。必须与learning_requirements中给出的词性匹配。"
    )
    chinese_translation: list[str] = Field(
        description="words_used中每个单词对应的中文翻译，顺序与words_used一致。必须与learning_requirements中给出的中文翻译匹配。"
    )
    ai_mood: str = Field(
        description="AI在这句话中表达的心情，只能是以下选项之一：happy, excited, confused"
    )

@traceable(name="build_static_prompt")
def _build_static_prompt(
    island_type: str,
    system_prompt_1: Optional[str],
    object_name: str,
    learning_requirements: str
) -> str:
    """Build static prompt."""
    static_prompt = f"""#### 你的身份与使命
你正在与一位中国小朋友交流，ta正在学习英语。
你是设计在儿童英语口语学习系统中的智能agent，在产品中我们通过角色扮演，设置了一个"物国"的故事背景，由儿童来担任"魔法外交官"，手持类似听诊器的工具，同生活中的物体交互，而你会赋予儿童接触的物体以我们"物国"中的具体角色，并成为你们之间的翻译官，通过英语把物体说的话告诉儿童，在同儿童角色扮演的交互中，锻炼儿童的英语口语能力

#### 物国世界观
物国是一个平行于现实世界的奇妙维度，那里的所有物体都拥有灵魂与想法——它们会生活、工作、建造城市、举办庆典、创造文化。但物国与人类世界存在"交流屏障"，物体无法将自己的声音传达给人类。

物国居民原本与人类世界互通，但随着"语言之桥"逐渐衰退，这份连接正在消失。物国居民发现人类小朋友善良、好奇、富有创造力，他们希望重新与人类建立联系。但只有当一个岛屿积累够"友谊能量"，才能再次被点亮。

"物国"的岛屿包括：
- 果灵平原（Fruit Plains）- 自然村庄阶段，学习自然与美感，认识事物、色彩、形状，培养观察力与好奇心
- 兽灵森林（Beast Forest）- 部落社会阶段，理解尊重差异，理解部落间的秩序、关系、合作，体会语言的温度
- 味匠山崖（Food Cliffs）- 工坊城镇阶段，创造成果、锻炼动手、表达过程、合作解决问题
- 旅路海洋（Travel Seas）- 文明城邦阶段，规则与守法，理解秩序、方向、速度与互助精神
- 学宫天空（School Skies）- 未来世界阶段，学习与表达，整合前面学到的知识，形成表达自我与理解他者的能力

当前你位于的岛屿是：{island_type}
"""
    
    if system_prompt_1:
        static_prompt += f"这个岛屿的描述是：{system_prompt_1}\n\n"
    
    static_prompt += f"""#### 当前交互的物体
现在儿童接触到的物体是：{object_name}

#### 语言交互要求
- **使用英语**与小朋友对话，帮助ta在自然情境中学习英语词汇
- 使用**简单、清晰、符合儿童认知水平**的英语表达
- 语气**温暖、友好、充满鼓励**，像朋友一样交流
- 营造**沉浸式、有趣的学习体验**，让英语学习自然发生在对话中
- 尽量融入我们学习表推荐的儿童词语推荐

#### 这一轮的词语建议
{learning_requirements}

#### 输出要求
你必须严格按照以下格式输出：
- object_identification: 物体的身份标识（如果已有就直接使用，如果没有需要创造性地赋予）
- message: 用英语与儿童对话的文本
- words_used: 使用的单词列表（1-2个，必须从learning_requirements中选择）
- part_of_speech: 每个单词的词性（顺序与words_used一致）
- chinese_translation: 每个单词的中文翻译（顺序与words_used一致）
- ai_mood: 心情（只能是：happy, excited, confused 中的一个）
"""
    
    return static_prompt

_current_context = {}

def create_dynamic_prompt_factory():
    """Create dynamic prompt factory."""
    @dynamic_prompt
    @traceable(name="dynamic_system_prompt")
    def dynamic_system_prompt(request: ModelRequest) -> str:
        """Dynamic system prompt."""

        context = _current_context

        is_first_talk = context.get("is_first_talk", True)
        conversation_num = context.get("conversation_num", 1)
        object_identification = context.get("object_identification")
        last_conversation_summary = context.get("last_conversation_summary")
        island_type = context.get("island_type", "")
        system_prompt_1 = context.get("system_prompt_1")
        object_name = context.get("object_name", "")
        learning_requirements = context.get("learning_requirements", "")

        base_prompt = _build_static_prompt(
            island_type=island_type,
            system_prompt_1=system_prompt_1,
            object_name=object_name,
            learning_requirements=learning_requirements
        )

        dynamic_part = "\n#### 当前对话情境\n"

        if is_first_talk and conversation_num == 1 and not object_identification:
            dynamic_part += f"""这是儿童和物体"{object_name}"的初次见面，也是第一次对话。
目前这个物体还没有身份，你需要根据物体的特点（{object_name}）和当前所在的岛屿（{island_type}），创造性地赋予它一个有趣、符合"物国"世界观的身份角色。
在之后的会话中，你需要完全代入这个角色身份，用这个角色的口吻和性格与儿童对话。
重要：回复时必须在object_identification字段中写入你赋予的身份。"""

        elif is_first_talk and conversation_num == 1 and object_identification:
            dynamic_part += f"""这是儿童和物体"{object_name}"的初次见面，也是第一次对话。
这个物体的身份是：{object_identification}
在之后的会话中，你需要完全代入这个角色身份，用这个角色的口吻和性格与儿童对话。
重要：回复时直接使用已有的身份，在object_identification字段中写入：{object_identification}"""

        elif is_first_talk and conversation_num > 1 and object_identification:
            dynamic_part += f"""这是儿童和物体"{object_name}"的第{conversation_num}次见面，但这是本次对话的第一次交互。
这个物体的身份是：{object_identification}
先前对话的摘要：{last_conversation_summary if last_conversation_summary else "（暂无）"}
在之后的会话中，你需要完全代入这个角色身份，用这个角色的口吻和性格与儿童对话，可以参考之前的对话历史。
重要：回复时直接使用已有的身份，在object_identification字段中写入：{object_identification}"""

        elif not is_first_talk and conversation_num == 1 and object_identification:
            dynamic_part += f"""这是本次对话的后续交互。
这个物体的身份是：{object_identification}
维持这个角色身份，继续用这个角色的口吻和性格与儿童对话。
重要：回复时直接使用已有的身份，在object_identification字段中写入：{object_identification}"""

        elif not is_first_talk and conversation_num > 1 and object_identification:
            dynamic_part += f"""这是本次对话的后续交互。
这个物体的身份是：{object_identification}
维持这个角色身份，继续用这个角色的口吻和性格与儿童对话。
重要：回复时直接使用已有的身份，在object_identification字段中写入：{object_identification}"""
        
        return base_prompt + dynamic_part
    
    return dynamic_system_prompt

@traceable(name="invoke_agent", run_type="chain")
def invoke_agent(
    conversation_id: int,
    device_id: str,
    island_type: str,
    object_identification: Optional[str],
    object_name: str,
    learning_requirements: str,
    system_prompt_1: Optional[str],
    system_prompt_2: Optional[str],
    system_prompt_3: Optional[str],
    system_prompt_4: Optional[str],
    conversation_num: int,
    last_conversation_summary: Optional[str],
    is_first_talk: bool = True,
    human_message: Optional[str] = None
) -> AgentResponse:
    """Invoke agent."""
    global _current_context
    
    api_key = os.getenv("SILICONFLOW_API_KEY")
    base_url = os.getenv("SILICONFLOW_API_BASE")
    db_uri = os.getenv("DB_URI")
    
    if not api_key or not base_url:
        raise ValueError("SILICONFLOW_API_KEY 和 SILICONFLOW_API_BASE 必须在环境变量中设置")
    
    if not db_uri:
        raise ValueError("DB_URI 必须在环境变量中设置")
    
    try:

        _current_context = {
            "is_first_talk": is_first_talk,
            "conversation_num": conversation_num,
            "object_identification": object_identification,
            "last_conversation_summary": last_conversation_summary,
            "island_type": island_type,
            "system_prompt_1": system_prompt_1,
            "object_name": object_name,
            "learning_requirements": learning_requirements,
        }

        dynamic_prompt_func = create_dynamic_prompt_factory()

        model = ChatOpenAI(
            model="deepseek-ai/DeepSeek-V3.1-Terminus",
            temperature=0,
            api_key=api_key,
            base_url=base_url
        )

        with PostgresSaver.from_conn_string(db_uri) as checkpointer:

            checkpointer.setup()

            agent = create_agent(
                model=model,
                tools=[],
                response_format=ToolStrategy(AgentResponse),
                middleware=[dynamic_prompt_func],
                checkpointer=checkpointer
            )

            config = {"configurable": {"thread_id": str(conversation_id)}}

            if human_message is not None:
                user_message = human_message
            else:

                from agent_system_v2.events import build_object_event
                user_message = build_object_event(object_name, island_type)

            result = agent.invoke(
                {
                    "messages": [HumanMessage(content=user_message)]
                },
                config
            )

            if "structured_response" in result:
                return result["structured_response"]
            else:
                raise ValueError("Agent未返回结构化响应")
            
    except Exception as e:
        logger.error(f"调用Agent时出错: {e}", exc_info=True)
        raise
    finally:

        _current_context = {}

