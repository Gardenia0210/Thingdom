"""Object persona."""
import os
import random
import logging
from typing import Callable

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import SystemMessage

logger = logging.getLogger(__name__)

PERSONAS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "personas"
)

try:
    from langsmith import traceable as _traceable
except ImportError:
    def _traceable(**kwargs):
        def _decorator(func):
            return func
        return _decorator

class ObjectPersonaMiddleware(AgentMiddleware):
    """Objectpersonamiddleware."""

    @_traceable(name="ObjectPersonaMiddleware", run_type="chain")
    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Wrap model call."""
        context = request.runtime.context

        object_persona = context.get("object_persona")
        conversation_id = context.get("conversation_id")

        return self._process_persona(object_persona, conversation_id, request, handler)

    def _process_persona(
        self,
        object_persona: int | None,
        conversation_id: int | None,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Process persona."""

        if not object_persona:
            object_persona = random.randint(1, 12)
            logger.info(f"ObjectPersonaMiddleware: 随机分配人格 P{object_persona:02d}")

            if conversation_id:
                try:
                    from agent_system_v2.models import Conversation
                    Conversation.objects.filter(id=conversation_id).update(
                        object_persona=object_persona
                    )
                    logger.info(f"人格 ID {object_persona} 已写入 conversation {conversation_id}")
                except Exception as e:
                    logger.error(f"写入 object_persona 失败: {e}")

        persona_content = self._load_persona_template(object_persona)

        if persona_content:

            dynamic_prompt = f"""
#### 你的人格特质
（以下是你这个角色的性格模板，请在对话中自然体现这些特质）

{persona_content}
"""

            new_content = list(request.system_message.content_blocks) + [
                {"type": "text", "text": dynamic_prompt}
            ]
            new_system_message = SystemMessage(content=new_content)
            return handler(request.override(system_message=new_system_message))
        else:
            logger.warning(
                f"ObjectPersonaMiddleware: 未找到人格模板 {object_persona}.md，跳过注入"
            )
            return handler(request)

    @staticmethod
    def _load_persona_template(persona_id: int) -> str | None:
        """Load persona template."""
        filepath = os.path.join(PERSONAS_DIR, f"{persona_id}.md")
        try:
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                logger.debug(f"已加载人格模板: {filepath}")
                return content
            else:
                logger.warning(f"人格模板文件不存在: {filepath}")
                return None
        except Exception as e:
            logger.error(f"读取人格模板文件失败: {e}")
            return None
