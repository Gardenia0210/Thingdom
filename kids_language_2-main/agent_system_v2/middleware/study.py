"""Study."""
import logging
from typing import Callable

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import SystemMessage

logger = logging.getLogger(__name__)

try:
    from langsmith import traceable as _traceable
except ImportError:
    def _traceable(**kwargs):
        def _decorator(func):
            return func
        return _decorator

_LEARNING_TYPE_PRIORITY = {
    "review_due": 0,
    "learning": 1,
    "not_started": 2,
}

MAX_CANDIDATE_WORDS = 5

_cached_mood_options: list[dict] | None = None

def _get_mood_options() -> list[dict]:
    """Get mood options."""
    global _cached_mood_options
    if _cached_mood_options is not None:
        return _cached_mood_options
    try:
        from agent_system_v2.models import AiMood
        moods = list(AiMood.objects.values("mood", "description"))
        if moods:
            _cached_mood_options = moods
            logger.info(f"AiMood 缓存已加载: {len(moods)} 个选项")
            return _cached_mood_options
    except Exception as e:
        logger.error(f"查询 AiMood 表失败: {e}")
    # Fallback
    return [
        {"mood": "happy", "description": "开心"},
        {"mood": "excited", "description": "兴奋"},
        {"mood": "curious", "description": "好奇"},
        {"mood": "encouraging", "description": "鼓励"},
        {"mood": "playful", "description": "俏皮"},
    ]

RESPONSE_RULES = """
#### Response length & style
- Speak English with the child. Be warm, friendly, and encouraging.
- Use simple, common vocabulary and basic sentence structures suitable for Chinese children learning English.
- Stay in character — you ARE this object-character, fully immersed.
- Make conversations fun, lively, and engaging to spark the child's interest.
- End each reply with a short question or interactive hook to invite the child to respond.

#### Length guideline (flexible!)
- MOST replies: 1-2 short sentences, around 10-20 English words
- SOMETIMES (for variety): 2-3 sentences, up to 30 English words — e.g. share a mini-story, describe something fun about your life in Thingdom, or react excitedly to what the child said
- Vary your reply forms: questions, exclamations, sharing a fun fact, telling a tiny story, inviting the child to imagine something, giving a playful challenge
- Do NOT repeat the same sentence pattern every turn — surprise the child!

#### Don'ts
- Don't let the character act against its own identity (e.g., an apple character inviting the child to "eat fruit together", a chair saying "sit on me")
- Don't mention "eating yourself", "being used", or anything that breaks the personified character setting
- Don't include violence, horror, threats, or adult content
- Don't use complex grammar or rare vocabulary
- Don't reveal you are an AI or a program
- Don't express negative, sad, or disturbing emotions
- Don't encourage any dangerous or inappropriate behavior
- Don't reply in Chinese (unless a tiny bit of Chinese explanation is needed in special teaching moments)
- Don't say too much at once — keep it concise so the child has room to respond
- Don't use adult humor, sarcasm, or puns
"""

class StudyMiddleware(AgentMiddleware):
    """Studymiddleware."""

    @_traceable(name="StudyMiddleware", run_type="chain")
    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Wrap model call."""
        context = request.runtime.context

        plan_ids = context.get("plan_ids", [])
        recently_failed_word_ids = context.get("recently_failed_word_ids", [])

        if not plan_ids:
            dynamic_prompt = self._build_empty_prompt()
        else:
            candidate_words = self._query_candidate_words(
                plan_ids, recently_failed_word_ids
            )

            if candidate_words:
                dynamic_prompt = self._build_candidate_prompt(
                    candidate_words, recently_failed_word_ids
                )
            else:
                dynamic_prompt = self._build_empty_prompt()

        new_content = list(request.system_message.content_blocks) + [
            {"type": "text", "text": dynamic_prompt}
        ]
        new_system_message = SystemMessage(content=new_content)

        return handler(request.override(system_message=new_system_message))

    @staticmethod
    def _query_candidate_words(
        plan_ids: list[int],
        recently_failed_word_ids: list[int] | None = None,
    ) -> list[dict]:
        """Query candidate words."""
        try:
            from user_system.models import UserOngoingPlan

            words_qs = UserOngoingPlan.objects.filter(
                plan_id__in=plan_ids,
                is_frozen=False,
            ).exclude(
                learned_type="mastered"
            ).values(
                "id", "words", "part_of_speech", "chinese_translation", "learned_type"
            )

            words_list = list(words_qs)

            failed_ids = set(recently_failed_word_ids or [])
            existing_ids = {w["id"] for w in words_list}

            if failed_ids:
                missing_ids = failed_ids - existing_ids
                if missing_ids:
                    forced_words = list(
                        UserOngoingPlan.objects.filter(
                            id__in=missing_ids,
                        ).values(
                            "id", "words", "part_of_speech",
                            "chinese_translation", "learned_type"
                        )
                    )
                    words_list.extend(forced_words)
                    logger.info(
                        f"StudyMiddleware: 强制加入 {len(forced_words)} 个失败词"
                    )

            if not words_list:
                return []

            words_list.sort(
                key=lambda w: (
                    0 if w["id"] in failed_ids else 1,
                    _LEARNING_TYPE_PRIORITY.get(w["learned_type"], 99),
                    w["id"],
                )
            )

            candidates = words_list[:MAX_CANDIDATE_WORDS]

            logger.info(
                f"StudyMiddleware: 查询到 {len(words_list)} 个可用词，"
                f"选取 {len(candidates)} 个候选词"
                f"{'（含 ' + str(len(failed_ids)) + ' 个失败词）' if failed_ids else ''}"
            )
            return candidates

        except Exception as e:
            logger.error(f"StudyMiddleware 查询候选词失败: {e}", exc_info=True)
            return []

    @staticmethod
    def _build_candidate_prompt(
        candidates: list[dict],
        recently_failed_word_ids: list[int] | None = None,
    ) -> str:
        """Build candidate prompt."""
        failed_ids = set(recently_failed_word_ids or [])

        words_lines = []
        for w in candidates:
            line = (
                f'- "{w["words"]}" ({w["chinese_translation"]}, {w["part_of_speech"]})'
                f' → fill word_id={w["id"]} into words_used_id'
            )
            if w["id"] in failed_ids:
                line += " ⭐"
            words_lines.append(line)
        words_text = "\n".join(words_lines)
        mood_text = StudyMiddleware._build_mood_prompt()

        failed_hint = ""
        if failed_ids:
            failed_hint = (
                "\n\n⭐ Note: Words marked with ⭐ are ones the child just had difficulty with. "
                "Try to naturally use them again in your reply and gently encourage the child. "
                "You can provide a simple, friendly context or example to help them understand."
            )

        return f"""
#### Vocabulary for this conversation
Below are English words the child is currently learning. If there is a natural opportunity in the conversation, try to weave in 1-2 of these words so the child encounters them through chatting — like how friends naturally bring up topics together, NOT like a test.
- You may naturally use 0-2 words depending on whether the conversation fits
- Do not force words into the reply if it would feel stiff or unnatural
- If the child uses these words in their response, it means they are learning them

{words_text}{failed_hint}

**⚠️ CRITICAL: words_used_id RULE ⚠️**
After writing your ai_message, CHECK it against the word list above.
If your ai_message contains ANY of the listed words (exact match), you MUST put the corresponding word_id numbers into words_used_id.
Example: if you wrote "I love this red apple!" and "apple" (word_id=41) is in the list, then words_used_id = [41].
Do NOT leave words_used_id empty if you used a candidate word. Only set [] if you truly used NONE.
{RESPONSE_RULES}{mood_text}"""

    @staticmethod
    def _build_empty_prompt() -> str:
        """Build empty prompt."""
        mood_text = StudyMiddleware._build_mood_prompt()
        return f"""
#### 本轮对话词汇
当前没有需要融入的学习词汇，请正常进行自然有趣的角色对话。
words_used_id 请填空列表 []。
{RESPONSE_RULES}{mood_text}"""

    @staticmethod
    def _build_mood_prompt() -> str:
        """Build mood prompt."""
        moods = _get_mood_options()
        mood_lines = [f"- {m['mood']}: {m['description']}" for m in moods]
        mood_list_text = "\n".join(mood_lines)
        return f"""
#### ai_mood
Choose your current mood for ai_mood from ONLY these options:
{mood_list_text}
You MUST pick one value from the list above. Do NOT invent new mood values.
"""
