"""Word mastery agent."""
import logging
from langchain.messages import SystemMessage, HumanMessage

from .model_factory import get_zhipu_model
from .schemas import WordMasteryAgentResponse
from .json_utils import clean_and_parse_json

logger = logging.getLogger(__name__)

WORD_MASTERY_SYSTEM_PROMPT = """You are a children's English vocabulary assessment agent. Your job is to evaluate whether a Chinese child (age 6-12) has demonstrated mastery of specific English words during a conversation.

## Evaluation criteria for each word

For each word you must score these dimensions (0.0 to 1.0):

### recognition (认知度)
- 1.0: The child clearly understood the word when the AI used it (responded appropriately to its meaning)
- 0.5: Partial understanding, or the word was not directly addressed
- 0.0: The child showed no sign of understanding the word

### usage (使用度)
- 1.0: The child actively and correctly used the word in their response
- 0.5: The child attempted to use the word but with minor errors
- 0.0: The child did not use the word at all

### fluency (流利度)
- 1.0: The word was used naturally, in a complete and contextually appropriate way
- 0.5: The word was used but awkwardly or in isolation
- 0.0: Not applicable (word not used)

### confidence (置信度)
- High (>0.7): There is clear evidence in the child's response to make a judgment
- Medium (0.55-0.7): Some evidence, but not conclusive
- Low (<0.55): Insufficient evidence to evaluate (e.g., the child's response was too short, off-topic, or didn't relate to the word at all)

## Important guidelines
- Be fair and encouraging in your assessment — these are young learners
- If the child's response is very short (e.g., just "yes" or "好"), set confidence low
- If the AI didn't actually use the word in its message, recognition should be low and confidence should be low
- Each word must have exactly one evaluation entry
- Do NOT invent word_ids; use only the ones provided

## OUTPUT FORMAT (CRITICAL)
You MUST respond with ONLY a valid JSON object (no markdown, no explanation, no code blocks).
The JSON must follow this exact structure:

{"evaluations": [{"word_id": 41, "recognition": 0.8, "usage": 0.5, "fluency": 0.3, "confidence": 0.7}, {"word_id": 42, "recognition": 0.3, "usage": 0.0, "fluency": 0.0, "confidence": 0.6}]}

- "evaluations" is an array containing one object per word
- Each object has: word_id (int), recognition (float 0-1), usage (float 0-1), fluency (float 0-1), confidence (float 0-1)
- Output ONLY the JSON, nothing else"""

def invoke_word_mastery_agent(
    ai_message: str,
    human_message: str,
    words: list[dict],
) -> WordMasteryAgentResponse:
    """Invoke word mastery agent."""
    logger.info(f"调用 Word Mastery Agent: 评估 {len(words)} 个单词")

    model = get_zhipu_model(model_name="glm-4.7-flash", temperature=0.1, streaming=False)

    words_text = "\n".join(
        f"- word_id={w['id']}: {w['words']} ({w['part_of_speech']}) — {w['chinese_translation']}"
        for w in words
    )

    human_prompt = f"""## Conversation context

**AI said:**
{ai_message}

**Child responded:**
{human_message}

## Words to evaluate
{words_text}

Please evaluate the child's mastery of each word listed above. Respond with ONLY JSON, no markdown."""

    messages = [
        SystemMessage(content=WORD_MASTERY_SYSTEM_PROMPT),
        HumanMessage(content=human_prompt),
    ]

    try:
        response = model.invoke(messages)
        raw_text = response.content
        logger.debug(f"Word Mastery Agent 原始输出: {raw_text[:300]}")

        result = clean_and_parse_json(raw_text, WordMasteryAgentResponse)
        logger.info(
            f"Word Mastery Agent 输出: {len(result.evaluations)} 个评估结果"
        )
        return result
    except Exception as first_error:
        logger.warning(
            f"Word Mastery Agent 首次解析失败: {first_error}, 尝试重试..."
        )

    try:
        retry_model = get_zhipu_model(
            model_name="glm-4.7-flash", temperature=0.3, streaming=False
        )
        response = retry_model.invoke(messages)
        raw_text = response.content
        logger.debug(f"Word Mastery Agent 重试原始输出: {raw_text[:300]}")

        result = clean_and_parse_json(raw_text, WordMasteryAgentResponse)
        logger.info(
            f"Word Mastery Agent 重试成功: {len(result.evaluations)} 个评估结果"
        )
        return result
    except Exception as retry_error:
        logger.error(
            f"Word Mastery Agent 重试也失败: {retry_error}", exc_info=True
        )
        raise
