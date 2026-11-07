"""Object info."""
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

class ObjectInfoMiddleware(AgentMiddleware):
    """Objectinfomiddleware."""

    @_traceable(name="ObjectInfoMiddleware", run_type="chain")
    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Wrap model call."""
        context = request.runtime.context

        object_name = context.get("object_name", "")
        object_identification = context.get("object_identification")
        object_identification_english = context.get("object_identification_english")
        description_english = context.get("description_english")
        chapter_type = context.get("chapter_type", "")
        conversation_id = context.get("conversation_id")

        if not object_identification:
            try:
                from agent_system_v2.agents.naming_agent import invoke_naming_agent
                from agent_system_v2.models import Conversation

                naming_result = invoke_naming_agent(chapter_type, object_name)

                if conversation_id:
                    Conversation.objects.filter(id=conversation_id).update(
                        object_identification=naming_result.object_identification,
                        object_description=naming_result.description,
                        object_identification_english=naming_result.object_identification_english,
                        description_english=naming_result.description_english,
                    )
                    logger.info(f"命名结果已写入 conversation {conversation_id}")

                object_identification = naming_result.object_identification
                object_identification_english = naming_result.object_identification_english
                description_english = naming_result.description_english

                logger.info(
                    f"ObjectInfoMiddleware: 命名完成 - "
                    f"{object_identification_english} ({object_identification})"
                )

            except Exception as e:
                logger.error(f"ObjectInfoMiddleware: 命名子Agent调用失败: {e}", exc_info=True)

                object_identification = object_name
                object_identification_english = object_name
                description_english = f"A friendly {object_name} from Thingdom."

        chapter_description = self._get_chapter_description(chapter_type)

        dynamic_prompt = self._build_prompt(
            object_name=object_name,
            object_identification=object_identification,
            object_identification_english=object_identification_english,
            description_english=description_english,
            chapter_type=chapter_type,
            chapter_description=chapter_description,
        )

        new_content = list(request.system_message.content_blocks) + [
            {"type": "text", "text": dynamic_prompt}
        ]
        new_system_message = SystemMessage(content=new_content)

        return handler(request.override(system_message=new_system_message))

    @staticmethod
    def _get_chapter_description(chapter_type: str) -> str:
        """Get chapter description."""
        try:
            from agent_system_v2.models import AgentSystemPrompt
            prompt_record = AgentSystemPrompt.objects.filter(
                chapter_name=chapter_type
            ).first()
            if prompt_record and prompt_record.system_prompt_1:
                return prompt_record.system_prompt_1
        except Exception as e:
            logger.error(f"查询章节描述失败: {e}")

        fallback_map = {
            "fruit": "果灵平原（Fruit Plains）是一片宁静的果园平原，孩子在这里认识自然、颜色与形状。",
            "animal": "兽灵森林（Beast Forest）是神秘的部落社会，孩子学习尊重差异与合作。",
            "food": "味匠山崖（Food Cliffs）是繁忙的工坊城镇，孩子锻炼动手能力与表达。",
            "travel": "旅路海洋（Travel Seas）是有序的文明城邦，孩子理解规则与互助。",
            "school": "学宫天空（School Skies）是未来世界学院，孩子整合知识并表达自我。",
        }
        return fallback_map.get(chapter_type, "物国的一个神秘角落。")

    @staticmethod
    def _build_prompt(
        object_name: str,
        object_identification: str,
        object_identification_english: str,
        description_english: str,
        chapter_type: str,
        chapter_description: str,
    ) -> str:
        """Build prompt."""
        return f"""
#### 当前章节
你生活在：{chapter_type}
{chapter_description}

#### 你扮演的角色
你的名字是：{object_identification_english}（{object_identification}）
关于你：{description_english}
小朋友接触到的实际物体是：{object_name}
"""
