"""Summary agent."""
import logging
from langchain.messages import SystemMessage, HumanMessage

from .model_factory import get_minimax_model
from .schemas import SummaryAgentResponse
from .json_utils import clean_and_parse_json

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM_PROMPT = """You are a child profile analyst for a children's English learning system. Your job is to analyze a conversation session between an AI character and a Chinese child (age 6-12), then decide whether to update the child's long-term memory profile.

## Your task
Given:
1. The child's existing memory profile (may be empty for new children)
2. This session's conversation messages (AI and child turns)
3. This session's word mastery results (if any)

You must decide whether to update any of these profile fields:
- personality_traits: The child's personality characteristics (e.g., curious, shy, outgoing, creative, careful)
- interest_topics: Topics the child shows interest in (e.g., animals, space, colors, food, games)
- motivation_triggers: What motivates the child to engage (e.g., praise, storytelling, games, challenges, humor)
- english_level: The child's English proficiency level:
  - A: Beginner — knows very few words, mostly responds in Chinese or single English words
  - B: Elementary — can understand simple sentences, responds with basic English phrases
  - C: Intermediate — can hold simple conversations, uses short sentences
  - D: Advanced — converses fluently with varied vocabulary and grammar

## CRITICAL: Update criteria (be conservative!)

You should ONLY update a field when:
1. There is **clear, repeated evidence** across **multiple exchanges** in this session
2. The evidence is **strong enough** to confidently characterize the child
3. The new information is **meaningfully different** from the existing profile

Do NOT update when:
- The session is too short (fewer than 3 exchanges) — there's not enough data
- The evidence is ambiguous or could be interpreted multiple ways
- The child's behavior could be situational rather than a stable trait
- The existing profile already captures the information adequately

## Specific field guidelines

### personality_traits
- Need at least 2-3 exchanges showing consistent behavior
- Look for: response length, enthusiasm level, willingness to try, curiosity patterns
- Example evidence: "Child asked 3 follow-up questions about the topic" → curious

### interest_topics
- The child must show genuine interest (asking questions, elaborating, showing excitement)
- A single mention is NOT enough — look for sustained engagement
- Don't confuse the AI's topic choice with the child's interest

### motivation_triggers
- Observe what makes the child respond more actively or positively
- Look for: longer responses after praise, more engagement during games/stories
- Need clear before/after contrast in the session

### english_level
- This should change VERY rarely — only with strong evidence
- Compare the child's actual language output against level descriptions
- A single good/bad response is not enough to change the level
- If existing level seems accurate, do NOT update

## Output format
- Set a field to null if you do NOT want to update it (this is the default — prefer null)
- When you DO update, provide the complete new value (not just additions)
- update_reason: Always explain your reasoning in Chinese, even if you decide not to update

## Language
- personality_traits, interest_topics, motivation_triggers: Use Chinese values
- english_level: Use A/B/C/D
- update_reason: Write in Chinese

## OUTPUT FORMAT (CRITICAL)
You MUST respond with ONLY a valid JSON object. Do NOT wrap in markdown code blocks. Do NOT include any thinking process or explanation outside the JSON.

Example output:
{"personality_traits": null, "interest_topics": ["动物", "颜色"], "motivation_triggers": null, "english_level": null, "update_reason": "孩子在对话中多次提到喜欢动物和颜色，更新了兴趣话题。"}"""

def invoke_summary_agent(
    existing_memory: dict,
    meet_messages: list[dict],
    meet_mastery: list[dict],
) -> SummaryAgentResponse:
    """Invoke summary agent."""
    logger.info(
        f"调用 Summary Agent: "
        f"{len(meet_messages)} 条消息, {len(meet_mastery)} 条掌握记录"
    )

    model = get_minimax_model(
        model_name="Minimax-M2.1",
        temperature=0.3,
        streaming=False,
    )

    memory_text = _format_existing_memory(existing_memory)

    messages_text = _format_messages(meet_messages)

    mastery_text = _format_mastery(meet_mastery)

    human_prompt = f"""## Existing child profile
{memory_text}

## This session's conversation ({len(meet_messages)} messages)
{messages_text}

## This session's word mastery results
{mastery_text}

Based on the above, analyze whether any profile fields should be updated. Remember to be conservative — only update with strong evidence.
Respond with ONLY JSON, no markdown, no thinking process."""

    messages = [
        SystemMessage(content=SUMMARY_SYSTEM_PROMPT),
        HumanMessage(content=human_prompt),
    ]

    try:
        response = model.invoke(messages)
        raw_text = response.content
        logger.debug(f"Summary Agent 原始输出: {raw_text[:300]}")

        result = clean_and_parse_json(raw_text, SummaryAgentResponse)
        logger.info(f"Summary Agent 输出: update_reason={result.update_reason}")
        return result
    except Exception as first_error:
        logger.warning(
            f"Summary Agent 首次解析失败: {first_error}, 尝试重试..."
        )

    try:
        retry_model = get_minimax_model(
            model_name="Minimax-M2.1",
            temperature=0.5,
            streaming=False,
        )
        response = retry_model.invoke(messages)
        raw_text = response.content
        logger.debug(f"Summary Agent 重试原始输出: {raw_text[:300]}")

        result = clean_and_parse_json(raw_text, SummaryAgentResponse)
        logger.info(
            f"Summary Agent 重试成功: update_reason={result.update_reason}"
        )
        return result
    except Exception as retry_error:
        logger.error(
            f"Summary Agent 重试也失败: {retry_error}", exc_info=True
        )
        raise

def _format_existing_memory(memory: dict) -> str:
    """Format existing memory."""
    lines = []
    for key, value in memory.items():
        if value is None:
            lines.append(f"- {key}: (not yet assessed)")
        elif isinstance(value, list):
            lines.append(f"- {key}: {', '.join(str(v) for v in value)}")
        else:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines) if lines else "(No existing profile data)"

def _format_messages(messages: list[dict]) -> str:
    """Format messages."""
    if not messages:
        return "(No messages in this session)"

    lines = []
    for msg in messages:
        sender = "AI" if msg["sender"] == "ai" else "Child"
        lines.append(f"[{sender}]: {msg['message']}")
    return "\n".join(lines)

def _format_mastery(mastery: list[dict]) -> str:
    """Format mastery."""
    if not mastery:
        return "(No word mastery data for this session)"

    lines = []
    for i, m in enumerate(mastery, 1):
        passed = "✓ Passed" if m.get("is_passed") else "✗ Not passed"
        lines.append(
            f"Word {i}: mastery={m.get('mastery', 0):.2f}, "
            f"confidence={m.get('confidence', 0):.2f} — {passed}"
        )
    return "\n".join(lines)
