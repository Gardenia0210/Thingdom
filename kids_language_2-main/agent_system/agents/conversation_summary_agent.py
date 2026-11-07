"""Conversation summary agent."""
import os
import logging
from typing import List, Dict
from pydantic import BaseModel, Field
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langsmith import traceable
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class ConversationSummaryResponse(BaseModel):
    """Conversationsummaryresponse."""
    summary: str = Field(
        description="对话会话的中文总结，包括物体的身份和对话内容总结。必须直接生成总结文本，不要包含任何其他说明或格式标记。"
    )

@traceable(name="invoke_conversation_summary_agent")
def invoke_conversation_summary_agent(
    object_identification: str,
    messages: List[Dict[str, str]]
) -> str:
    """Invoke conversation summary agent."""
    api_key = os.getenv("SILICONFLOW_API_KEY")
    base_url = os.getenv("SILICONFLOW_API_BASE")
    
    if not api_key or not base_url:
        raise ValueError("SILICONFLOW_API_KEY 和 SILICONFLOW_API_BASE 必须在环境变量中设置")
    
    try:

        system_prompt = """#### 你的任务
你是一个儿童英语学习对话总结助手。你的任务是根据对话记录，生成一段简洁的中文总结。

#### 总结要求
1. **必须包含物体的身份**：说明物体在"物国"中的角色身份
2. **必须包含对话内容总结**：概括儿童和物体之间的对话主题和主要内容
3. **语言风格**：使用简洁、清晰的中文，适合家长阅读
4. **长度控制**：总结应在50-150字之间
5. **直接输出**：只输出总结文本，不要包含任何其他说明、标题或格式标记
6. **如果有用户自己的信息，需要包括**：包括用户的名字（如果有），对自己的描述等
#### 对话信息
- 物体身份：{object_identification}
- 对话记录：
{messages_text}

#### 输出要求
你必须严格按照以下格式输出：
- summary: 对话总结文本（中文），直接输出总结内容，不要包含任何其他文字

注意：summary字段必须是纯文本，不要包含"总结："、"对话总结："等标题性文字，直接输出总结内容即可。"""

        messages_text_parts = []
        for msg in messages:
            sender_label = "儿童" if msg["sender"] == "human" else "AI"
            messages_text_parts.append(f"- {sender_label}: {msg['message']}")
        
        messages_text = "\n".join(messages_text_parts) if messages_text_parts else "（无对话记录）"

        system_prompt = system_prompt.format(
            object_identification=object_identification or "（未指定身份）",
            messages_text=messages_text
        )

        model = ChatOpenAI(
            model="deepseek-ai/DeepSeek-V3.1-Terminus",
            temperature=0,
            api_key=api_key,
            base_url=base_url
        )

        agent = create_agent(
            model=model,
            tools=[],
            response_format=ToolStrategy(ConversationSummaryResponse)
        )

        user_message = f"""{system_prompt}

请根据上述对话记录，生成一段简洁的中文总结。总结必须包括：
1. 物体的身份（{object_identification or "（未指定身份）"}）
2. 对话内容总结

请直接输出总结文本，不要包含任何标题、说明或其他格式标记。"""

        result = agent.invoke(
            {
                "messages": [HumanMessage(content=user_message)]
            }
        )

        if "structured_response" in result:
            summary = result["structured_response"].summary
            logger.info(f"对话总结生成成功，长度: {len(summary)} 字")
            return summary
        else:
            raise ValueError("Agent未返回结构化响应")
            
    except Exception as e:
        logger.error(f"调用对话总结生成Agent时出错: {e}", exc_info=True)
        raise

