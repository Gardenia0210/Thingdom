"""Mqtt handlers."""
import json
import logging
import threading
from django.db import transaction
from user_system.models import User, UserStudyPlan, UserOngoingPlan
from .mqtt_client import mqtt_client_v2
from .events import build_object_event

logger = logging.getLogger(__name__)

_processing_locks = {}
_locks_mutex = threading.Lock()

def _get_processing_lock(device_id: str, topic_type: str) -> threading.Lock:
    """Get processing lock."""
    key = (device_id, topic_type)
    with _locks_mutex:
        if key not in _processing_locks:
            _processing_locks[key] = threading.Lock()
        return _processing_locks[key]

def _try_acquire_lock(device_id: str, topic_type: str) -> bool:
    """Try acquire lock."""
    lock = _get_processing_lock(device_id, topic_type)
    return lock.acquire(blocking=False)

def _release_lock(device_id: str, topic_type: str):
    """Release lock."""
    lock = _get_processing_lock(device_id, topic_type)
    try:
        lock.release()
    except RuntimeError:
        pass

def _fallback_fill_words_used_id(ai_message: str, plan_ids: list[int]) -> list[int]:
    """Fallback fill words used id."""
    if not ai_message or not plan_ids:
        return []
    try:
        candidates = list(UserOngoingPlan.objects.filter(
            plan_id__in=plan_ids,
            is_frozen=False,
        ).exclude(
            learned_type="mastered"
        ).values("id", "words"))

        if not candidates:
            return []

        import re
        ai_lower = ai_message.lower()
        matched_ids = []
        for c in candidates:
            word = c["words"].lower().strip()
            if not word:
                continue

            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, ai_lower):
                matched_ids.append(c["id"])

        if matched_ids:
            logger.info(
                f"words_used_id 后端兜底: 在 ai_message 中匹配到 {matched_ids}"
            )
        return matched_ids
    except Exception as e:
        logger.error(f"words_used_id 后端兜底失败: {e}")
        return []

def _send_agent_type_response(device_id, status, message, chapter_type=None, device_battery=None):
    """Send agent type response."""
    response_topic = f"server/device/{device_id}/agent_type/response"
    response_data = {
        "status": status,
        "message": message,
        "device_id": device_id,
    }

    if chapter_type:
        response_data["chapter_type"] = chapter_type

    if device_battery is not None:
        response_data["device_battery"] = device_battery

    try:
        mqtt_client_v2.publish(response_topic, response_data, qos=1)
        logger.info(f"已发送 agent_type 响应消息到 {response_topic}: {status}")
    except Exception as e:
        logger.error(f"发送 agent_type 响应消息失败: {e}")

def handle_device_agent_type(topic, payload):
    """Handle device agent type."""
    device_id = None
    chapter_type = None
    device_battery = None
    lock_acquired = False

    try:
        data = json.loads(payload)
        device_id = data.get("device_id")
        chapter_type = data.get("chapter_type")
        device_battery = data.get("device_battery")

        if not device_id:
            logger.error("收到 device/agent_type 消息，但缺少 device_id")
            _send_agent_type_response("unknown", "error", "缺少 device_id 字段")
            return

        if not _try_acquire_lock(device_id, "agent_type"):
            logger.warning(f"设备 {device_id} 的 agent_type 请求正在处理中，拒绝重复请求")
            _send_agent_type_response(device_id, "busy", "请求正在处理中，请稍后重试")
            return
        lock_acquired = True

        if not chapter_type:
            logger.error(f"收到 device/agent_type 消息，但缺少 chapter_type (device_id: {device_id})")
            _send_agent_type_response(device_id, "error", "缺少 chapter_type 字段")
            return

        try:
            with transaction.atomic():
                user = User.objects.get(device_id=device_id)
                user.chapter_type = chapter_type

                if device_battery is not None:
                    from decimal import Decimal, InvalidOperation
                    try:
                        user.device_battery = Decimal(str(device_battery))
                        logger.info(f"已更新用户 {user.username} 的 device_battery 为 {device_battery}")
                    except (InvalidOperation, ValueError) as e:
                        logger.warning(f"device_battery 值无效: {device_battery}, 错误: {e}")

                user.save()
                logger.info(
                    f"已更新用户 {user.username} (device_id: {device_id}) "
                    f"的 chapter_type 为 {chapter_type}"
                )

                _send_agent_type_response(
                    device_id,
                    "success",
                    f"chapter_type 已更新为 {chapter_type}",
                    chapter_type,
                    str(user.device_battery) if user.device_battery is not None else None,
                )
        except User.DoesNotExist:
            logger.warning(
                f"收到 device/agent_type 消息，"
                f"但未找到绑定 device_id={device_id} 的用户"
            )
            _send_agent_type_response(
                device_id, "error", f"未找到绑定 device_id={device_id} 的用户"
            )
        except Exception as e:
            logger.error(f"更新用户 chapter_type 时出错: {e}")
            _send_agent_type_response(device_id, "error", f"更新失败: {str(e)}")

    except json.JSONDecodeError as e:
        logger.error(f"解析 device/agent_type 消息 JSON 失败: {e}, 原始消息: {payload}")
        if device_id:
            _send_agent_type_response(device_id, "error", f"JSON 解析失败: {str(e)}")
        else:
            _send_agent_type_response("unknown", "error", f"JSON 解析失败: {str(e)}")
    except Exception as e:
        logger.error(f"处理 device/agent_type 消息时出错: {e}")
        if device_id:
            _send_agent_type_response(device_id, "error", f"处理消息时出错: {str(e)}")
        else:
            _send_agent_type_response("unknown", "error", f"处理消息时出错: {str(e)}")
    finally:
        if lock_acquired and device_id:
            _release_lock(device_id, "agent_type")

def _send_object_detected_response(device_id, status, message, **extra_fields):
    """Send object detected response."""
    response_topic = f"server/device/{device_id}/object_detected/response_v2"
    response_data = {
        "status": status,
        "message": message,
        "device_id": device_id,
    }
    response_data.update(extra_fields)

    try:
        mqtt_client_v2.publish(response_topic, response_data, qos=1)
        logger.info(f"已发送 object_detected 响应到 {response_topic}: {status}")
    except Exception as e:
        logger.error(f"发送 object_detected 响应失败: {e}")

def _send_agent_stream_token(device_id, content):
    """Send agent stream token."""
    topic = f"server/device/{device_id}/object_detected/agent_response_v2"
    mqtt_client_v2.publish(topic, {
        "type": "stream",
        "content": content,
    }, qos=0)

def _send_agent_complete_response(device_id, response_data):
    """Send agent complete response."""
    topic = f"server/device/{device_id}/object_detected/agent_response_v2"
    response_data["type"] = "complete"
    response_data["status"] = "success"
    mqtt_client_v2.publish(topic, response_data, qos=1)
    logger.info(f"已发送 agent 完整响应到 {topic}")

def _send_agent_error_response(device_id, error_message):
    """Send agent error response."""
    topic = f"server/device/{device_id}/object_detected/agent_response_v2"
    mqtt_client_v2.publish(topic, {
        "type": "error",
        "status": "error",
        "message": error_message,
        "device_id": device_id,
    }, qos=1)
    logger.error(f"已发送 agent 错误响应: {error_message}")

def handle_object_detected_v2(topic, payload):
    """Handle object detected v2."""
    device_id = None
    lock_acquired = False

    try:
        data = json.loads(payload)
        device_id = data.get("device_id")
        object_name = data.get("object_name")

        if not device_id:
            logger.error("收到 object_detected_v2 消息，但缺少 device_id")
            _send_object_detected_response("unknown", "error", "缺少 device_id 字段")
            return

        if not object_name:
            logger.error(f"收到 object_detected_v2 消息，但缺少 object_name (device: {device_id})")
            _send_object_detected_response(device_id, "error", "缺少 object_name 字段")
            return

        if not _try_acquire_lock(device_id, "object_detected"):
            logger.warning(f"设备 {device_id} 的 object_detected 请求正在处理中")
            _send_object_detected_response(device_id, "busy", "请求正在处理中，请稍后重试")
            return
        lock_acquired = True

        try:
            user = User.objects.get(device_id=device_id)
        except User.DoesNotExist:
            _send_object_detected_response(device_id, "error", f"未找到绑定设备 {device_id} 的用户")
            return

        user_id = str(user.id)
        chapter_type = user.chapter_type
        if not chapter_type:
            raise ValueError("Select a chapter before starting a conversation.")

        from .models import Conversation

        conversation = Conversation.objects.filter(
            device_id=device_id,
            object_name=object_name,
            chapter_type=chapter_type,
        ).first()

        if conversation:

            if not conversation.is_active:
                conversation.meet_count += 1
                conversation.is_active = True
                conversation.save(update_fields=["meet_count", "is_active", "updated_at"])
                logger.info(
                    f"找到已有 conversation {conversation.id}（was inactive），"
                    f"meet_count 更新为 {conversation.meet_count}, is_active=True"
                )
            else:
                logger.info(
                    f"找到已有 conversation {conversation.id}（already active），"
                    f"meet_count 保持 {conversation.meet_count}"
                )
        else:

            conversation = Conversation.objects.create(
                user=user,
                device_id=device_id,
                object_name=object_name,
                chapter_type=chapter_type,
                meet_count=1,
                is_active=True,
            )
            logger.info(f"创建新 conversation {conversation.id}")

        active_plans = UserStudyPlan.objects.filter(
            user=user,
            is_activated=True,
            is_locked=False,
        ).values_list("id", flat=True)
        plan_ids = list(active_plans)

        _send_object_detected_response(
            device_id=device_id,
            status="success",
            message="物体识别处理成功，Agent正在生成回复",
            conversation_id=conversation.id,
            object_name=object_name,
            object_identification=conversation.object_identification,
            object_identification_english=conversation.object_identification_english,
            meet_count=conversation.meet_count,
            chapter_type=chapter_type,
        )

        agent_context = {
            "object_name": object_name,
            "object_identification": conversation.object_identification or "",
            "object_identification_english": conversation.object_identification_english or "",
            "description_english": conversation.description_english or "",
            "object_persona": conversation.object_persona,
            "chapter_type": chapter_type,
            "conversation_id": conversation.id,
            "user_id": user_id,
            "plan_ids": plan_ids,
            "meet_count": conversation.meet_count,
            "device_id": device_id,
        }

        token_buffer = []

        def on_stream_token(text: str):
            """On stream token."""
            token_buffer.append(text)

            buffer_text = "".join(token_buffer)
            if len(buffer_text) >= 3 or text in " .,!?;:":
                _send_agent_stream_token(device_id, buffer_text)
                token_buffer.clear()

        try:
            from .agents.main_agent import invoke_agent_with_stream

            result = invoke_agent_with_stream(
                user_message=build_object_event(object_name, chapter_type),
                context=agent_context,
                on_token=on_stream_token,
            )

            if token_buffer:
                _send_agent_stream_token(device_id, "".join(token_buffer))
                token_buffer.clear()

            ai_message = result.get("ai_message", "")
            words_used_id_raw = result.get("words_used_id", [])
            ai_mood = result.get("ai_mood", "happy")
            is_blocked = result.get("is_guardrail_blocked", False)

            if not words_used_id_raw and ai_message and not is_blocked:
                words_used_id_raw = _fallback_fill_words_used_id(ai_message, plan_ids)

            words_used_detail = []
            if words_used_id_raw and not is_blocked:
                try:
                    ongoing_words = UserOngoingPlan.objects.filter(
                        id__in=words_used_id_raw
                    ).values("id", "words", "part_of_speech", "chinese_translation")

                    for w in ongoing_words:
                        words_used_detail.append({
                            "id": w["id"],
                            "words": w["words"],
                            "part_of_speech": w["part_of_speech"],
                            "chinese_translation": w["chinese_translation"],
                        })
                except Exception as e:
                    logger.error(f"查询 words_used_id 详情失败: {e}")

            if not is_blocked:
                try:
                    from .models import Message, AiMood

                    mood_obj = AiMood.objects.filter(mood=ai_mood).first()

                    Message.objects.create(
                        user=user,
                        device_id=device_id,
                        conversation=conversation,
                        sender="ai",
                        message=ai_message,
                        words_used_id=words_used_detail if words_used_detail else None,
                        mood_id=mood_obj,
                        meet_count=conversation.meet_count,
                    )
                    logger.info(f"AI 消息已存入 messages 表 (conversation: {conversation.id})")
                except Exception as e:
                    logger.error(f"存储 AI 消息失败: {e}", exc_info=True)

            conversation.refresh_from_db()

            _send_agent_complete_response(device_id, {
                "device_id": device_id,
                "conversation_id": conversation.id,
                "message": ai_message,
                "meet_count": conversation.meet_count,
                "object_identification": conversation.object_identification or "",
                "object_identification_english": conversation.object_identification_english or "",
                "words_used_id": words_used_detail,
                "ai_mood": ai_mood,
            })

        except Exception as e:
            logger.error(f"Agent 调用失败: {e}", exc_info=True)
            _send_agent_error_response(device_id, f"Agent 生成失败: {str(e)}")

    except json.JSONDecodeError as e:
        logger.error(f"解析 object_detected_v2 消息 JSON 失败: {e}")
        if device_id:
            _send_object_detected_response(device_id, "error", f"JSON 解析失败: {str(e)}")
    except Exception as e:
        logger.error(f"处理 object_detected_v2 消息时出错: {e}", exc_info=True)
        if device_id:
            _send_object_detected_response(device_id, "error", f"处理失败: {str(e)}")
    finally:
        if lock_acquired and device_id:
            _release_lock(device_id, "object_detected")

def _send_user_response_response(device_id, status, message, **extra_fields):
    """Send user response response."""
    response_topic = f"server/device/{device_id}/user_response/response_v2"
    response_data = {
        "status": status,
        "message": message,
        "device_id": device_id,
    }
    response_data.update(extra_fields)

    try:
        mqtt_client_v2.publish(response_topic, response_data, qos=1)
        logger.info(f"已发送 user_response 响应到 {response_topic}: {status}")
    except Exception as e:
        logger.error(f"发送 user_response 响应失败: {e}")

def _send_user_response_stream_token(device_id, content):
    """Send user response stream token."""
    topic = f"server/device/{device_id}/user_response/agent_response_v2"
    mqtt_client_v2.publish(topic, {
        "type": "stream",
        "content": content,
    }, qos=0)

def _send_user_response_complete(device_id, response_data):
    """Send user response complete."""
    topic = f"server/device/{device_id}/user_response/agent_response_v2"
    response_data["type"] = "complete"
    response_data["status"] = "success"
    mqtt_client_v2.publish(topic, response_data, qos=1)
    logger.info(f"已发送 user_response agent 完整响应到 {topic}")

def _send_user_response_agent_error(device_id, error_message):
    """Send user response agent error."""
    topic = f"server/device/{device_id}/user_response/agent_response_v2"
    mqtt_client_v2.publish(topic, {
        "type": "error",
        "status": "error",
        "message": error_message,
        "device_id": device_id,
    }, qos=1)
    logger.error(f"已发送 user_response agent 错误响应: {error_message}")

def _process_word_mastery(conversation, words_id, ai_message_text, human_message_text, user):
    """Process word mastery."""
    from .agents.word_mastery_agent import invoke_word_mastery_agent

    mastery_results = []
    failed_word_ids = []

    words_detail = list(UserOngoingPlan.objects.filter(
        id__in=words_id,
        plan__user=user,
        plan__is_activated=True,
        plan__is_locked=False,
        is_frozen=False,
    ).exclude(learned_type="mastered").values("id", "words", "part_of_speech", "chinese_translation", "learned_type"))

    if not words_detail:
        logger.warning(f"words_id {words_id} 在 user_ongoing_plan 中未找到记录")
        return mastery_results, failed_word_ids

    words_for_agent = [
        {
            "id": w["id"],
            "words": w["words"],
            "part_of_speech": w["part_of_speech"],
            "chinese_translation": w["chinese_translation"],
        }
        for w in words_detail
    ]

    try:
        agent_response = invoke_word_mastery_agent(
            ai_message=ai_message_text,
            human_message=human_message_text,
            words=words_for_agent,
        )
    except Exception as e:
        logger.error(f"Word Mastery Agent 调用失败: {e}", exc_info=True)
        return mastery_results, failed_word_ids

    word_detail_map = {w["id"]: w for w in words_detail}

    from .models import WordsMastery

    for evaluation in agent_response.evaluations:
        word_id = evaluation.word_id

        if word_id not in word_detail_map:
            logger.warning(f"Word Mastery Agent 返回了未知 word_id: {word_id}")
            continue

        mastery_score = (
            0.40 * evaluation.recognition
            + 0.40 * evaluation.usage
            + 0.20 * evaluation.fluency
        )

        is_passed = False
        if evaluation.confidence >= 0.55 and mastery_score >= 0.65:
            is_passed = True

        insufficient_evidence = evaluation.confidence < 0.55

        try:
            WordsMastery.objects.create(
                conversation=conversation,
                cognition=evaluation.recognition,
                usage=evaluation.usage,
                fluency=evaluation.fluency,
                mastery=mastery_score,
                confidence=evaluation.confidence,
                is_passed=is_passed,
                meet_count=conversation.meet_count,
            )
        except Exception as e:
            logger.error(f"写入 words_mastery 记录失败 (word_id={word_id}): {e}")

        if is_passed:
            _advance_learned_type(word_id)
        elif not insufficient_evidence:

            failed_word_ids.append(word_id)

        result_entry = {
            "word_id": word_id,
            "words": word_detail_map[word_id]["words"],
            "recognition": round(evaluation.recognition, 2),
            "usage": round(evaluation.usage, 2),
            "fluency": round(evaluation.fluency, 2),
            "confidence": round(evaluation.confidence, 2),
            "mastery": round(mastery_score, 2),
            "is_passed": is_passed,
            "insufficient_evidence": insufficient_evidence,
        }
        mastery_results.append(result_entry)

    if any(r["is_passed"] for r in mastery_results):
        try:
            from user_system.utils import update_learned_percentage
            update_learned_percentage(user_id=str(user.id))
        except Exception as e:
            logger.error(f"更新 learned_percentage 失败: {e}")

    return mastery_results, failed_word_ids

def _advance_learned_type(word_id: int):
    """Advance learned type."""
    PROGRESSION = {
        "not_started": "learning",
        "learning": "review_due",
        "review_due": "mastered",
    }

    try:
        word_record = UserOngoingPlan.objects.get(id=word_id)
        current_type = word_record.learned_type
        next_type = PROGRESSION.get(current_type)

        if next_type:
            word_record.learned_type = next_type
            word_record.is_frozen = True
            word_record.save(update_fields=["learned_type", "is_frozen", "updated_at"])
            logger.info(
                f"单词 {word_record.words} (id={word_id}) 状态推进: "
                f"{current_type} → {next_type}, is_frozen=True"
            )
        else:
            logger.debug(f"单词 {word_record.words} (id={word_id}) 已达最终状态: {current_type}")

    except UserOngoingPlan.DoesNotExist:
        logger.error(f"更新 learned_type 失败: word_id={word_id} 不存在")
    except Exception as e:
        logger.error(f"更新 learned_type 失败 (word_id={word_id}): {e}")

def handle_user_response_v2(topic, payload):
    """Handle user response v2."""
    device_id = None
    lock_acquired = False

    try:
        data = json.loads(payload)
        device_id = data.get("device_id")
        conversation_id = data.get("conversation_id")
        human_audio_message = data.get("human_audio_message", "")
        words_id = data.get("words_id", [])

        if not device_id:
            logger.error("收到 user_response_v2 消息，但缺少 device_id")
            _send_user_response_response("unknown", "error", "缺少 device_id 字段")
            return

        if not conversation_id:
            logger.error(f"收到 user_response_v2 消息，但缺少 conversation_id (device: {device_id})")
            _send_user_response_response(device_id, "error", "缺少 conversation_id 字段")
            return

        if not human_audio_message:
            logger.error(f"收到 user_response_v2 消息，但缺少 human_audio_message (device: {device_id})")
            _send_user_response_response(device_id, "error", "缺少 human_audio_message 字段")
            return

        if not _try_acquire_lock(device_id, "user_response"):
            logger.warning(f"设备 {device_id} 的 user_response 请求正在处理中")
            _send_user_response_response(device_id, "busy", "请求正在处理中，请稍后重试")
            return
        lock_acquired = True

        from .models import Conversation, Message

        try:
            conversation = Conversation.objects.get(id=conversation_id, device_id=device_id, is_active=True)
        except Conversation.DoesNotExist:
            _send_user_response_response(device_id, "error", f"未找到 conversation_id={conversation_id}")
            return

        try:
            user = User.objects.get(device_id=device_id)
        except User.DoesNotExist:
            _send_user_response_response(device_id, "error", f"未找到绑定设备 {device_id} 的用户")
            return

        user_id = str(user.id)
        chapter_type = user.chapter_type
        if not chapter_type:
            raise ValueError("Select a chapter before starting a conversation.")

        try:
            Message.objects.create(
                user=user,
                device_id=device_id,
                conversation=conversation,
                sender="human",
                message=human_audio_message,
                words_used_id=None,
                mood_id=None,
                meet_count=conversation.meet_count,
            )
            logger.info(f"儿童消息已存入 messages 表 (conversation: {conversation_id})")
        except Exception as e:
            logger.error(f"存储儿童消息失败: {e}", exc_info=True)

        mastery_results = []
        failed_word_ids = []

        if words_id:

            latest_ai_msg = Message.objects.filter(
                conversation_id=conversation_id,
                sender="ai",
            ).order_by("-created_at").first()

            ai_message_text = latest_ai_msg.message if latest_ai_msg else ""

            mastery_results, failed_word_ids = _process_word_mastery(
                conversation=conversation,
                words_id=words_id,
                ai_message_text=ai_message_text,
                human_message_text=human_audio_message,
                user=user,
            )

        _send_user_response_response(
            device_id=device_id,
            status="success",
            message="用户回复处理成功，Agent正在生成回复",
            conversation_id=conversation_id,
            mastery_results=mastery_results,
        )

        active_plans = UserStudyPlan.objects.filter(
            user=user,
            is_activated=True,
            is_locked=False,
        ).values_list("id", flat=True)
        plan_ids = list(active_plans)

        agent_context = {
            "object_name": conversation.object_name,
            "object_identification": conversation.object_identification or "",
            "object_identification_english": conversation.object_identification_english or "",
            "description_english": conversation.description_english or "",
            "object_persona": conversation.object_persona,
            "chapter_type": chapter_type,
            "conversation_id": conversation.id,
            "user_id": user_id,
            "plan_ids": plan_ids,
            "meet_count": conversation.meet_count,
            "device_id": device_id,
            "recently_failed_word_ids": failed_word_ids,
        }

        token_buffer = []

        def on_stream_token(text: str):
            """On stream token."""
            token_buffer.append(text)
            buffer_text = "".join(token_buffer)
            if len(buffer_text) >= 3 or text in " .,!?;:":
                _send_user_response_stream_token(device_id, buffer_text)
                token_buffer.clear()

        try:
            from .agents.main_agent import invoke_agent_with_stream

            result = invoke_agent_with_stream(
                user_message=human_audio_message,
                context=agent_context,
                on_token=on_stream_token,
            )

            if token_buffer:
                _send_user_response_stream_token(device_id, "".join(token_buffer))
                token_buffer.clear()

            ai_message = result.get("ai_message", "")
            words_used_id_raw = result.get("words_used_id", [])
            ai_mood = result.get("ai_mood", "happy")
            is_blocked = result.get("is_guardrail_blocked", False)

            if not words_used_id_raw and ai_message and not is_blocked:
                words_used_id_raw = _fallback_fill_words_used_id(ai_message, plan_ids)

            words_used_detail = []
            if words_used_id_raw and not is_blocked:
                try:
                    ongoing_words = UserOngoingPlan.objects.filter(
                        id__in=words_used_id_raw
                    ).values("id", "words", "part_of_speech", "chinese_translation")

                    for w in ongoing_words:
                        words_used_detail.append({
                            "id": w["id"],
                            "words": w["words"],
                            "part_of_speech": w["part_of_speech"],
                            "chinese_translation": w["chinese_translation"],
                        })
                except Exception as e:
                    logger.error(f"查询 words_used_id 详情失败: {e}")

            if not is_blocked:
                try:
                    from .models import AiMood

                    mood_obj = AiMood.objects.filter(mood=ai_mood).first()

                    Message.objects.create(
                        user=user,
                        device_id=device_id,
                        conversation=conversation,
                        sender="ai",
                        message=ai_message,
                        words_used_id=words_used_detail if words_used_detail else None,
                        mood_id=mood_obj,
                        meet_count=conversation.meet_count,
                    )
                    logger.info(f"AI 消息已存入 messages 表 (conversation: {conversation_id})")
                except Exception as e:
                    logger.error(f"存储 AI 消息失败: {e}", exc_info=True)

            _send_user_response_complete(device_id, {
                "device_id": device_id,
                "conversation_id": conversation_id,
                "message": ai_message,
                "meet_count": conversation.meet_count,
                "object_identification": conversation.object_identification or "",
                "object_identification_english": conversation.object_identification_english or "",
                "words_used_id": words_used_detail,
                "ai_mood": ai_mood,
            })

        except Exception as e:
            logger.error(f"Agent 调用失败 (user_response): {e}", exc_info=True)
            _send_user_response_agent_error(device_id, f"Agent 生成失败: {str(e)}")

    except json.JSONDecodeError as e:
        logger.error(f"解析 user_response_v2 消息 JSON 失败: {e}")
        if device_id:
            _send_user_response_response(device_id, "error", f"JSON 解析失败: {str(e)}")
    except Exception as e:
        logger.error(f"处理 user_response_v2 消息时出错: {e}", exc_info=True)
        if device_id:
            _send_user_response_response(device_id, "error", f"处理失败: {str(e)}")
    finally:
        if lock_acquired and device_id:
            _release_lock(device_id, "user_response")

def _send_user_stop_response(device_id, status, message, **extra_fields):
    """Send user stop response."""
    response_topic = f"server/device/{device_id}/user_stop/response_v2"
    response_data = {
        "status": status,
        "message": message,
        "device_id": device_id,
    }
    response_data.update(extra_fields)

    try:
        mqtt_client_v2.publish(response_topic, response_data, qos=1)
        logger.info(f"已发送 user_stop 响应到 {response_topic}: {status}")
    except Exception as e:
        logger.error(f"发送 user_stop 响应失败: {e}")

def handle_user_stop_v2(topic, payload):
    """Handle user stop v2."""
    device_id = None
    lock_acquired = False

    try:
        data = json.loads(payload)
        device_id = data.get("device_id")
        conversation_id = data.get("conversation_id")

        if not device_id:
            logger.error("收到 user_stop_v2 消息，但缺少 device_id")
            _send_user_stop_response("unknown", "error", "缺少 device_id 字段")
            return

        if not conversation_id:
            logger.error(f"收到 user_stop_v2 消息，但缺少 conversation_id (device: {device_id})")
            _send_user_stop_response(device_id, "error", "缺少 conversation_id 字段")
            return

        if not _try_acquire_lock(device_id, "user_stop"):
            logger.warning(f"设备 {device_id} 的 user_stop 请求正在处理中")
            _send_user_stop_response(device_id, "busy", "请求正在处理中，请稍后重试")
            return
        lock_acquired = True

        from .models import Conversation, Message, LongtermMemory, WordsMastery

        try:
            conversation = Conversation.objects.get(id=conversation_id, device_id=device_id, is_active=True)
        except Conversation.DoesNotExist:
            _send_user_stop_response(device_id, "error", f"未找到 conversation_id={conversation_id}")
            return

        conversation.is_active = False
        conversation.save(update_fields=["is_active", "updated_at"])
        logger.info(f"Conversation {conversation_id} is_active 已设为 False")

        longterm_mem = LongtermMemory.objects.filter(
            conversation_id=conversation_id
        ).first()

        existing_memory = {
            "personality_traits": longterm_mem.personality_traits if longterm_mem else None,
            "interest_topics": longterm_mem.interest_topics if longterm_mem else None,
            "motivation_triggers": longterm_mem.motivation_triggers if longterm_mem else None,
            "english_level": longterm_mem.english_level if longterm_mem else None,
        }

        meet_messages = list(
            Message.objects.filter(
                conversation_id=conversation_id,
                meet_count=conversation.meet_count,
            ).order_by("created_at").values("sender", "message")
        )

        meet_mastery = list(
            WordsMastery.objects.filter(
                conversation_id=conversation_id,
                meet_count=conversation.meet_count,
            ).values("cognition", "usage", "fluency", "mastery", "confidence", "is_passed")
        )

        summary_result = None
        try:
            from .agents.summary_agent import invoke_summary_agent

            summary_result = invoke_summary_agent(
                existing_memory=existing_memory,
                meet_messages=meet_messages,
                meet_mastery=meet_mastery,
            )
            logger.info(f"Summary Agent 输出: update_reason={summary_result.update_reason}")
        except Exception as e:
            logger.error(f"Summary Agent 调用失败: {e}", exc_info=True)

        memory_updated = False
        if summary_result:
            update_fields_dict = {}

            if summary_result.personality_traits is not None:
                update_fields_dict["personality_traits"] = summary_result.personality_traits
            if summary_result.interest_topics is not None:
                update_fields_dict["interest_topics"] = summary_result.interest_topics
            if summary_result.motivation_triggers is not None:
                update_fields_dict["motivation_triggers"] = summary_result.motivation_triggers
            if summary_result.english_level is not None:
                update_fields_dict["english_level"] = summary_result.english_level

            if update_fields_dict:
                if longterm_mem:
                    for field, value in update_fields_dict.items():
                        setattr(longterm_mem, field, value)
                    longterm_mem.save(update_fields=list(update_fields_dict.keys()) + ["updated_time"])
                else:
                    LongtermMemory.objects.create(
                        conversation=conversation,
                        **update_fields_dict,
                    )
                memory_updated = True
                logger.info(
                    f"LongtermMemory 已更新 (conversation: {conversation_id}), "
                    f"更新字段: {list(update_fields_dict.keys())}"
                )

        response_extra = {
            "conversation_id": conversation_id,
            "meet_count": conversation.meet_count,
            "memory_updated": memory_updated,
        }
        if summary_result:
            response_extra["update_reason"] = summary_result.update_reason
            if summary_result.personality_traits is not None:
                response_extra["personality_traits"] = summary_result.personality_traits
            if summary_result.interest_topics is not None:
                response_extra["interest_topics"] = summary_result.interest_topics
            if summary_result.english_level is not None:
                response_extra["english_level"] = summary_result.english_level

        _send_user_stop_response(
            device_id=device_id,
            status="success",
            message="对话已结束，记忆已更新" if memory_updated else "对话已结束",
            **response_extra,
        )

    except json.JSONDecodeError as e:
        logger.error(f"解析 user_stop_v2 消息 JSON 失败: {e}")
        if device_id:
            _send_user_stop_response(device_id, "error", f"JSON 解析失败: {str(e)}")
    except Exception as e:
        logger.error(f"处理 user_stop_v2 消息时出错: {e}", exc_info=True)
        if device_id:
            _send_user_stop_response(device_id, "error", f"处理失败: {str(e)}")
    finally:
        if lock_acquired and device_id:
            _release_lock(device_id, "user_stop")
