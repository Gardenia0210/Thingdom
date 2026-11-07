"""Word mastery agent."""
import os
import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langsmith import traceable
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class WordMasteryResponse(BaseModel):
    """Wordmasteryresponse."""
    verb: Optional[Dict[str, Any]] = Field(
        default=None,
        description="动词信息，包含word、chinese_translation和is_passed字段。如果没有动词，则为null。"
    )
    noun: Optional[Dict[str, Any]] = Field(
        default=None,
        description="名词信息，包含word、chinese_translation和is_passed字段。如果没有名词，则为null。"
    )
    adjective: Optional[Dict[str, Any]] = Field(
        default=None,
        description="形容词信息，包含word、chinese_translation和is_passed字段。如果没有形容词，则为null。"
    )
    exclamation: Optional[Dict[str, Any]] = Field(
        default=None,
        description="感叹词信息，包含word、chinese_translation和is_passed字段。如果没有感叹词，则为null。"
    )
    discourse_marker: Optional[Dict[str, Any]] = Field(
        default=None,
        description="语篇标记词信息，包含word、chinese_translation和is_passed字段。如果没有语篇标记词，则为null。"
    )
    adverb: Optional[Dict[str, Any]] = Field(
        default=None,
        description="副词信息，包含word、chinese_translation和is_passed字段。如果没有副词，则为null。"
    )

@traceable(name="invoke_word_mastery_agent")
def invoke_word_mastery_agent(
    human_message: str,
    words_info: Dict[str, Optional[Dict[str, str]]]
) -> WordMasteryResponse:
    """Invoke word mastery agent."""
    api_key = os.getenv("SILICONFLOW_API_KEY")
    base_url = os.getenv("SILICONFLOW_API_BASE")
    
    if not api_key or not base_url:
        raise ValueError("SILICONFLOW_API_KEY 和 SILICONFLOW_API_BASE 必须在环境变量中设置")
    
    try:

        system_prompt = """#### 你的任务
你是一个儿童英语学习评估助手。你的任务是分析儿童的语音文本消息，判断儿童是否掌握了指定单词。

#### 评估标准
1. **掌握（is_passed=true）**：儿童在对话中正确使用了该单词，表达清晰，使用场景恰当
2. **未掌握（is_passed=false）**：儿童没有使用该单词，或者使用错误，或者表达不清晰

#### 评估原则
- 优先考虑儿童是否正确理解和使用单词
- 考虑单词在语境中的使用是否恰当
- 如果儿童完全没有提到该单词，通常判断为未掌握
- 如果儿童正确使用了单词，即使语法有小错误，也应判断为掌握
- 要宽松友好，给予儿童鼓励

#### 输入信息
- 用户的语音文本消息："{human_message}"
- 需要评估的单词：
{words_list}

#### 输出要求
你必须严格按照以下格式输出：
- verb: 如果有动词需要评估，返回包含word、chinese_translation和is_passed的对象；如果没有动词，返回null
- noun: 如果有名词需要评估，返回包含word、chinese_translation和is_passed的对象；如果没有名词，返回null
- adjective: 如果有形容词需要评估，返回包含word、chinese_translation和is_passed的对象；如果没有形容词，返回null
- exclamation: 如果有感叹词需要评估，返回包含word、chinese_translation和is_passed的对象；如果没有感叹词，返回null
- discourse_marker: 如果有语篇标记词需要评估，返回包含word、chinese_translation和is_passed的对象；如果没有语篇标记词，返回null
- adverb: 如果有副词需要评估，返回包含word、chinese_translation和is_passed的对象；如果没有副词，返回null

注意：is_passed字段必须是布尔值（true或false），不能是字符串。"""

        words_list_parts = []
        for pos, word_info in words_info.items():
            if word_info:
                words_list_parts.append(f"- {pos}: {word_info['word']} ({word_info['chinese_translation']})")
        
        words_list_str = "\n".join(words_list_parts) if words_list_parts else "（无需要评估的单词）"

        system_prompt = system_prompt.format(
            human_message=human_message,
            words_list=words_list_str
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
            response_format=ToolStrategy(WordMasteryResponse)
        )

        user_message = f"""{system_prompt}

请分析以下儿童的语音文本消息，判断儿童是否掌握了指定的单词。

儿童的语音文本消息："{human_message}"

需要评估的单词：
{words_list_str}

请严格按照要求的格式输出判断结果。"""

        result = agent.invoke(
            {
                "messages": [HumanMessage(content=user_message)]
            }
        )

        if "structured_response" in result:
            return result["structured_response"]
        else:
            raise ValueError("Agent未返回结构化响应")
            
    except Exception as e:
        logger.error(f"调用单词掌握度判断Agent时出错: {e}", exc_info=True)
        raise

