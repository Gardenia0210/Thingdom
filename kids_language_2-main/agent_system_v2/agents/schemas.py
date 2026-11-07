"""Schemas."""
from pydantic import BaseModel, Field
from typing import TypedDict
from typing_extensions import NotRequired

class NamingAgentResponse(BaseModel):
    """Namingagentresponse."""
    object_identification: str = Field(
        description="中文身份名，4-10个中文字的角色化称谓"
    )
    description: str = Field(
        description="中文简介，1句话，28-55字，描述角色在章节里的职责/价值"
    )
    object_identification_english: str = Field(
        description="英文身份名，Title Case，2-5个英文词"
    )
    description_english: str = Field(
        description="英文简介，1句话，约14-26个英文词"
    )

class MainAgentResponse(BaseModel):
    """Mainagentresponse."""
    ai_message: str = Field(
        description=(
            "Your English reply. Usually 1-2 short sentences (10-20 words), "
            "occasionally 2-3 sentences (up to 30 words) for variety."
        )
    )
    words_used_id: list[int] = Field(
        default_factory=list,
        description=(
            "CRITICAL — MUST fill this field! "
            "List the word_id integers of ANY candidate vocabulary words that appear in your ai_message. "
            "Example: if your reply contains 'apple' (word_id=41) and 'red' (word_id=53), "
            "then words_used_id = [41, 53]. "
            "Do NOT leave empty if you used a word from the candidate list. "
            "If you truly did not use any candidate word, set to []."
        ),
    )
    ai_mood: str = Field(
        default="happy",
        description=(
            "Your current mood. "
            "MUST be one of the mood options listed in the system prompt. "
            "Do NOT invent new values."
        ),
    )

class WordEvaluation(BaseModel):
    """Wordevaluation."""
    word_id: int = Field(
        description="The word_id being evaluated, must match one of the provided word IDs."
    )
    recognition: float = Field(
        description="0-1 score: did the child recognize/understand this word in context?"
    )
    usage: float = Field(
        description="0-1 score: did the child use this word correctly in their response?"
    )
    fluency: float = Field(
        description="0-1 score: how naturally/fluently was the word used?"
    )
    confidence: float = Field(
        description="0-1 score: how confident is this evaluation? Below 0.55 means insufficient evidence."
    )

class WordMasteryAgentResponse(BaseModel):
    """Wordmasteryagentresponse."""
    evaluations: list[WordEvaluation] = Field(
        description="Per-word evaluation results. One entry for each word_id provided."
    )

class SummaryAgentResponse(BaseModel):
    """Summaryagentresponse."""
    personality_traits: list[str] | None = Field(
        default=None,
        description=(
            "Updated personality traits of the child (e.g. ['curious', 'shy', 'creative']). "
            "Set to null if no update is needed. Only update when there is clear evidence "
            "across multiple exchanges."
        ),
    )
    interest_topics: list[str] | None = Field(
        default=None,
        description=(
            "Updated interest topics of the child (e.g. ['animals', 'colors', 'space']). "
            "Set to null if no update is needed."
        ),
    )
    motivation_triggers: list[str] | None = Field(
        default=None,
        description=(
            "What motivates this child to engage (e.g. ['praise', 'games', 'stories']). "
            "Set to null if no update is needed."
        ),
    )
    english_level: str | None = Field(
        default=None,
        description=(
            "Child's English level: A (beginner), B (elementary), C (intermediate), D (advanced). "
            "Set to null if no update is needed. Only change when there is strong evidence."
        ),
    )
    update_reason: str = Field(
        description=(
            "Brief explanation of why fields were updated, or 'no update needed' if nothing changed. "
            "Write in Chinese."
        ),
    )

# ==================== Runtime Context ====================

class AgentContext(TypedDict):
    """Agentcontext."""
    object_name: str
    object_identification: NotRequired[str]
    object_identification_english: NotRequired[str]
    description_english: NotRequired[str]
    object_persona: NotRequired[int]
    chapter_type: str
    conversation_id: int
    user_id: str
    plan_ids: list[int]
    meet_count: int
    device_id: str
    recently_failed_word_ids: NotRequired[list[int]]
