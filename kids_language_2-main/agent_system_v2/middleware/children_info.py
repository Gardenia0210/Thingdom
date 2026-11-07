"""Children info."""
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

class ChildrenInfoMiddleware(AgentMiddleware):
    """Childreninfomiddleware."""

    @_traceable(name="ChildrenInfoMiddleware", run_type="chain")
    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Wrap model call."""
        context = request.runtime.context
        conversation_id = context.get("conversation_id")

        if not conversation_id:
            logger.debug("ChildrenInfoMiddleware: 无 conversation_id，跳过")
            return handler(request)

        child_info = self._query_child_info(conversation_id)

        if not child_info:
            logger.debug(
                f"ChildrenInfoMiddleware: conversation {conversation_id} 无记忆数据，跳过"
            )
            return handler(request)

        info_prompt = self._build_prompt(child_info)

        new_content = list(request.system_message.content_blocks) + [
            {"type": "text", "text": info_prompt}
        ]
        new_system_message = SystemMessage(content=new_content)

        return handler(request.override(system_message=new_system_message))

    @staticmethod
    def _query_child_info(conversation_id: int) -> dict | None:
        """Query child info."""
        try:
            from agent_system_v2.models import LongtermMemory

            mem = LongtermMemory.objects.filter(
                conversation_id=conversation_id
            ).first()

            if not mem:
                return None

            has_data = any([
                mem.personality_traits,
                mem.interest_topics,
                mem.motivation_triggers,
                mem.english_level,
            ])

            if not has_data:
                return None

            return {
                "personality_traits": mem.personality_traits,
                "interest_topics": mem.interest_topics,
                "motivation_triggers": mem.motivation_triggers,
                "english_level": mem.english_level,
            }

        except Exception as e:
            logger.error(f"ChildrenInfoMiddleware 查询失败: {e}", exc_info=True)
            return None

    @staticmethod
    def _build_prompt(child_info: dict) -> str:
        """Build prompt."""
        lines = []

        level_desc = {
            "A": "Beginner — knows very few words",
            "B": "Elementary — understands simple sentences",
            "C": "Intermediate — can hold simple conversations",
            "D": "Advanced — converses fluently",
        }

        if child_info.get("english_level"):
            level = child_info["english_level"]
            desc = level_desc.get(level, level)
            lines.append(f"- English level: {desc}")

        if child_info.get("personality_traits"):
            traits = ", ".join(child_info["personality_traits"])
            lines.append(f"- Personality: {traits}")

        if child_info.get("interest_topics"):
            topics = ", ".join(child_info["interest_topics"])
            lines.append(f"- Interests: {topics}")

        if child_info.get("motivation_triggers"):
            triggers = ", ".join(child_info["motivation_triggers"])
            lines.append(f"- What motivates them: {triggers}")

        if not lines:
            return ""

        info_text = "\n".join(lines)
        return f"""
#### What we know about this child
{info_text}
Use this information to adapt your conversation style, topic choices, and difficulty level. Don't mention these facts directly — just let them guide how you interact."""
