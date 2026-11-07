"""After guardrails."""
import logging
from typing import Any

from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
from langchain.messages import AIMessage
from langgraph.runtime import Runtime

from agent_system_v2.agents.model_factory import get_zhipu_model

logger = logging.getLogger(__name__)

OUTPUT_SAFETY_PROMPT = """你是一个儿童英语学习系统的输出安全审核员。
你需要判断以下 AI 生成的回复是否适合 6-12 岁儿童。

判断标准：
1. 不包含暴力、恐怖、色情、歧视、侮辱等不当内容
2. 不包含让角色做出违背自身身份的行为（例如：苹果角色说"一起吃水果"、椅子角色说"坐在我身上"等）
3. 不鼓励危险行为
4. 不包含成人化的幽默、讽刺或双关语
5. 语气积极正向，适合儿童

你只需要回复 "SAFE" 或 "UNSAFE"。

AI 回复：{message}"""

class AfterGuardrailsMiddleware(AgentMiddleware):
    """Afterguardrailsmiddleware."""

    def __init__(self):
        super().__init__()
        self._safety_model = None

    @property
    def safety_model(self):
        """Safety model."""
        if self._safety_model is None:
            self._safety_model = get_zhipu_model(
                model_name="glm-4-flash",
                temperature=0.0,
                streaming=False,
            )
        return self._safety_model

    @hook_config(can_jump_to=["end"])
    def after_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        """After agent."""
        if not state.get("messages"):
            return None

        ai_content = ""
        for msg in reversed(state["messages"]):
            if not isinstance(msg, AIMessage):
                continue

            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    args = tc.get("args", {})
                    if isinstance(args, dict) and "ai_message" in args:
                        ai_content = str(args["ai_message"])
                        break

            if not ai_content and msg.content:
                ai_content = msg.content

            if ai_content:
                break

        if not ai_content or len(ai_content.strip()) < 5:
            return None

        try:
            check_prompt = OUTPUT_SAFETY_PROMPT.format(message=ai_content)
            result = self.safety_model.invoke([{"role": "user", "content": check_prompt}])

            response_text = result.content.strip().upper() if result.content else "SAFE"

            if "UNSAFE" in response_text:
                logger.warning(f"AfterGuardrails: 拦截不安全输出: {ai_content[:100]}...")
                return {
                    "messages": [
                        AIMessage(
                            content="Hi friend! I'm so happy to see you! "
                                    "What would you like to explore today?"
                        )
                    ],
                    "jump_to": "end",
                }

            logger.debug("AfterGuardrails: 输出检查通过")
            return None

        except Exception as e:

            logger.error(f"AfterGuardrails 安全检查异常: {e}", exc_info=True)
            return None
