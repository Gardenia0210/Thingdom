"""Naming agent."""
import logging
from langchain.messages import SystemMessage, HumanMessage

from .model_factory import get_zhipu_model
from .schemas import NamingAgentResponse
from .json_utils import clean_and_parse_json

logger = logging.getLogger(__name__)

NAMING_SYSTEM_PROMPT = """You are a naming agent for "Thingdom" (物国), a children's language learning world where all objects have souls.
Your task: generate a Chinese and English identity + one-sentence description for a real-world object, placed in its chapter setting.

## Chapter styles
- fruit → Fruit Plains (果灵平原): nature, orchards, colors, shapes. Roles: gardener, scout, guide.
- animal → Beast Forest (兽灵森林): tribes, cooperation, friendship totems. Roles: messenger, ranger, guardian.
- food → Food Cliffs (味匠山崖): workshops, cooking, creation, feasts. Roles: chef, mixer, artisan.
- travel → Travel Seas (旅路海洋): routes, order, navigation, teamwork. Roles: navigator, dispatcher, pilot.
- school → School Skies (学宫天空): knowledge, expression, inspiration. Roles: tutor, researcher, archivist.

## Field rules
- object_identification: 4-10 Chinese characters, a role/title (NOT a physical description), chapter-flavored.
- description: 1 Chinese sentence (28-55 chars), positive, child-friendly, about the role's purpose.
- object_identification_english: 2-5 words, Title Case, natural English title matching the Chinese name.
- description_english: 1 English sentence (14-26 words), warm and encouraging, matching the Chinese description.

## Constraints
- Never copy the raw object_name as the identity. Create a unique persona.
- No violence, horror, or adult content. Everything must be suitable for ages 6-12.
- If object_name is vague (e.g. "object"/"thing"), still produce a valid chapter-themed identity.

## OUTPUT FORMAT (CRITICAL)
You MUST respond with ONLY a valid JSON object (no markdown, no explanation, no code blocks).
Example output:
{"object_identification": "果灵平原的色彩守护者", "description": "我是草地的守护者，负责让果灵平原保持生机勃勃的绿色，帮助水果们健康成长。", "object_identification_english": "Color Guardian of Fruit Plains", "description_english": "I am the guardian of the grasslands, keeping the Fruit Plains vibrant and green, helping all the fruits grow healthy and strong."}

Output ONLY the JSON, nothing else."""

def invoke_naming_agent(chapter_type: str, object_name: str) -> NamingAgentResponse:
    """Invoke naming agent."""
    logger.info(f"调用命名子Agent: chapter_type={chapter_type}, object_name={object_name}")

    model = get_zhipu_model(model_name="glm-4.7-flash", temperature=0.7, streaming=False)

    messages = [
        SystemMessage(content=NAMING_SYSTEM_PROMPT),
        HumanMessage(content=f'{{"chapter_type": "{chapter_type}", "object_name": "{object_name}"}}'),
    ]

    try:
        response = model.invoke(messages)
        raw_text = response.content
        logger.debug(f"命名子Agent 原始输出: {raw_text[:200]}")

        result = clean_and_parse_json(raw_text, NamingAgentResponse)
        logger.info(
            f"命名子Agent 输出: "
            f"identification={result.object_identification}, "
            f"english={result.object_identification_english}"
        )
        return result
    except Exception as first_error:
        logger.warning(
            f"命名子Agent 首次解析失败: {first_error}, 尝试重试..."
        )

    try:
        retry_model = get_zhipu_model(
            model_name="glm-4.7-flash", temperature=0.5, streaming=False
        )
        response = retry_model.invoke(messages)
        raw_text = response.content
        logger.debug(f"命名子Agent 重试原始输出: {raw_text[:200]}")

        result = clean_and_parse_json(raw_text, NamingAgentResponse)
        logger.info(
            f"命名子Agent 重试成功: "
            f"identification={result.object_identification}, "
            f"english={result.object_identification_english}"
        )
        return result
    except Exception as retry_error:
        logger.error(
            f"命名子Agent 重试也失败: {retry_error}", exc_info=True
        )
        raise
