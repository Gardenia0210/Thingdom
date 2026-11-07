"""Mqtt handlers."""
import json
import logging
import threading
from django.db import transaction
from django.utils import timezone
from user_system.models import User, UserStudyPlan, UserOngoingPlan
from .models import Conversation, LongTermMemory, PresetObjectIdentification, AgentSystemPrompt, AiMood, Message
from .mqtt_client import mqtt_client
from .agent_service import invoke_agent, AgentResponse
from .agents.word_mastery_agent import invoke_word_mastery_agent
from .agents.conversation_summary_agent import invoke_conversation_summary_agent

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

def _is_processing(device_id: str, topic_type: str) -> bool:
    """Is processing."""
    lock = _get_processing_lock(device_id, topic_type)
    return lock.locked()

def _send_response(device_id, status, message, island_type=None, device_battery=None):
    """Send response."""
    response_topic = f"server/device/{device_id}/agent_type/response"
    response_data = {
        "status": status,
        "message": message,
        "device_id": device_id
    }
    
    if island_type:
        response_data["island_type"] = island_type
    
    if device_battery is not None:
        response_data["device_battery"] = device_battery
    
    try:
        mqtt_client.publish(response_topic, response_data, qos=1)
        logger.info(f"已发送响应消息到 {response_topic}: {status}")
    except Exception as e:
        logger.error(f"发送响应消息失败: {e}")

def _send_object_detected_response(device_id, status, message, agent_data=None):
    """Send object detected response."""
    response_topic = f"server/device/{device_id}/object_detected/response"
    response_data = {
        "status": status,
        "message": message,
        "device_id": device_id
    }
    
    if agent_data:
        response_data["agent_data"] = agent_data
    
    try:
        mqtt_client.publish(response_topic, response_data, qos=1)
        logger.info(f"已发送物体识别响应消息到 {response_topic}: {status}")
    except Exception as e:
        logger.error(f"发送物体识别响应消息失败: {e}")

def _send_agent_response(device_id, status, message, response_data=None):
    """Send agent response."""
    response_topic = f"server/device/{device_id}/object_detected/agent_response"
    response_payload = {
        "status": status,
        "message": message,
        "device_id": device_id
    }
    
    if response_data:
        response_payload.update(response_data)
    
    try:
        mqtt_client.publish(response_topic, response_payload, qos=1)
        logger.info(f"已发送Agent响应消息到 {response_topic}: {status}")
    except Exception as e:
        logger.error(f"发送Agent响应消息失败: {e}")

def _send_user_response_data_preparation(device_id, status, message, agent_data=None, words_mastery=None):
    """Send user response data preparation."""
    response_topic = f"server/device/{device_id}/user_response/response"
    response_payload = {
        "status": status,
        "message": message,
        "device_id": device_id
    }
    
    if agent_data:
        response_payload["agent_data"] = agent_data
    
    if words_mastery:
        response_payload["words_mastery"] = words_mastery
    
    try:
        mqtt_client.publish(response_topic, response_payload, qos=1)
        logger.info(f"已发送用户响应数据处理完成消息到 {response_topic}: {status}")
    except Exception as e:
        logger.error(f"发送用户响应数据处理完成消息失败: {e}")

def _send_user_response_agent_response(device_id, status, message, response_data=None):
    """Send user response agent response."""
    response_topic = f"server/device/{device_id}/user_response/agent_response"
    response_payload = {
        "status": status,
        "message": message,
        "device_id": device_id
    }
    
    if response_data:
        response_payload.update(response_data)
    
    try:
        mqtt_client.publish(response_topic, response_payload, qos=1)
        logger.info(f"已发送用户响应Agent响应消息到 {response_topic}: {status}")
    except Exception as e:
        logger.error(f"发送用户响应Agent响应消息失败: {e}")

def _send_user_stop_response(device_id, status, message, conversation_summary=None):
    """Send user stop response."""
    response_topic = f"server/device/{device_id}/user_stop/response"
    response_payload = {
        "status": status,
        "message": message,
        "device_id": device_id
    }
    
    if conversation_summary:
        response_payload["conversation_summary"] = conversation_summary
    
    try:
        mqtt_client.publish(response_topic, response_payload, qos=1)
        logger.info(f"已发送用户停止对话响应消息到 {response_topic}: {status}")
    except Exception as e:
        logger.error(f"发送用户停止对话响应消息失败: {e}")

def _process_agent_response(
    agent_response: AgentResponse,
    conversation_id: int,
    user_id,
    device_id: str,
    island_type: str,
    object_name: str
) -> dict:
    """Process agent response."""
    with transaction.atomic():

        conversation = Conversation.objects.get(id=conversation_id)
        if not conversation.object_identification and agent_response.object_identification:
            conversation.object_identification = agent_response.object_identification
            conversation.save()
            logger.info(f"更新conversation的object_identification: {agent_response.object_identification}")

        try:
            memory = LongTermMemory.objects.get(
                user_id=user_id,
                device_id=device_id,
                island_type=island_type,
                object_name=object_name
            )
            if not memory.object_identification and agent_response.object_identification:
                memory.object_identification = agent_response.object_identification
                memory.save()
                logger.info(f"更新long_term_memory的object_identification: {agent_response.object_identification}")
        except LongTermMemory.DoesNotExist:
            logger.warning(f"未找到long_term_memory记录")

        ai_mood_obj = None
        mood_id = None
        try:
            ai_mood_obj = AiMood.objects.get(mood=agent_response.ai_mood)
            mood_id = ai_mood_obj.id
            logger.info(f"找到AI心情: {agent_response.ai_mood} (id: {mood_id})")
        except AiMood.DoesNotExist:
            logger.warning(f"未找到AI心情: {agent_response.ai_mood}")

        message_obj = Message.objects.create(
            user_id=user_id,
            device_id=device_id,
            conversation_id=conversation_id,
            sender='ai',
            message=agent_response.message,
            words_used=agent_response.words_used,
            mood_id=ai_mood_obj
        )
        logger.info(f"创建消息记录: message_id={message_obj.id}")

        part_of_speech_map = {
            'verb': None,
            'noun': None,
            'adjective': None,
            'exclamation': None,
            'discourse marker': None,
            'adverb': None
        }
        
        for word, pos, translation in zip(
            agent_response.words_used,
            agent_response.part_of_speech,
            agent_response.chinese_translation
        ):
            try:

                ongoing_word = UserOngoingPlan.objects.filter(
                    user_id=user_id,
                    words=word,
                    part_of_speech=pos,
                    chinese_translation=translation
                ).first()
                
                if ongoing_word:

                    word_info = {
                        "word": word,
                        "chinese_translation": translation
                    }

                    pos_lower = pos.lower()
                    if 'verb' in pos_lower or pos_lower == 'v.' or pos_lower == 'v':
                        part_of_speech_map['verb'] = word_info
                    elif 'noun' in pos_lower or pos_lower == 'n.' or pos_lower == 'n':
                        part_of_speech_map['noun'] = word_info
                    elif 'adjective' in pos_lower or pos_lower == 'adj.' or pos_lower == 'adj' or pos_lower == 'a.':
                        part_of_speech_map['adjective'] = word_info
                    elif 'adverb' in pos_lower or pos_lower == 'adv.' or pos_lower == 'adv':
                        part_of_speech_map['adverb'] = word_info
                    elif 'interjection' in pos_lower or 'exclamation' in pos_lower or pos_lower == 'int.':
                        part_of_speech_map['exclamation'] = word_info
                    elif 'discourse' in pos_lower or 'marker' in pos_lower:
                        part_of_speech_map['discourse marker'] = word_info
                    
                    logger.info(f"找到单词匹配: {word} ({pos}) - {translation}")
                else:
                    logger.warning(f"未在user_ongoing_plan中找到匹配的单词: {word} ({pos}) - {translation}")
            except Exception as e:
                logger.error(f"查询单词词性时出错: {e}")

        islands_progress = []
        try:
            activated_plans = UserStudyPlan.objects.filter(
                user_id=user_id,
                is_activated=True
            ).order_by('island_inner_id')
            
            for plan in activated_plans:
                islands_progress.append({
                    "island_inner_id": plan.island_inner_id,
                    "learned_percentage": str(plan.learned_percentage),
                    "is_locked": plan.is_locked
                })
            
            if islands_progress:
                logger.info(f"找到 {len(islands_progress)} 个激活的岛屿计划")
        except Exception as e:
            logger.warning(f"查询激活学习计划时出错: {e}")

        response_data = {
            "conversation_id": conversation_id,
            "object_identification": agent_response.object_identification,
            "message": agent_response.message,
            "verb": part_of_speech_map['verb'],
            "noun": part_of_speech_map['noun'],
            "adjective": part_of_speech_map['adjective'],
            "exclamation": part_of_speech_map['exclamation'],
            "discourse_marker": part_of_speech_map['discourse marker'],
            "adverb": part_of_speech_map['adverb'],
            "mood_id": mood_id,
            "islands_progress": islands_progress if islands_progress else None
        }
        
        return response_data

def _generate_learning_requirements(user_id):
    """Generate learning requirements."""
    try:

        activated_unlocked_plans = UserStudyPlan.objects.filter(
            user_id=user_id,
            is_activated=True,
            is_locked=False
        ).values_list('id', flat=True)
        
        if not activated_unlocked_plans:

            return "当前没有正在进行的单词学习计划，和儿童进行英语自然对话即可，无需针对性使用词汇。"
        
        plan_ids = list(activated_unlocked_plans)

        words_to_learn_queryset = UserOngoingPlan.objects.filter(
            plan_id__in=plan_ids,
            is_learned=False
        ).values('words', 'part_of_speech', 'chinese_translation').distinct()[:10]

        words_to_review_queryset = UserOngoingPlan.objects.filter(
            plan_id__in=plan_ids,
            reviewed_typed=1
        ).values('words', 'part_of_speech', 'chinese_translation').distinct()
        
        words_to_learn_list = list(words_to_learn_queryset)
        words_to_review_list = list(words_to_review_queryset)

        def format_words(words_list):
            """Format words."""
            if not words_list:
                return ""
            formatted = []
            for item in words_list:
                formatted.append(f"{item['words']} ({item['part_of_speech']}) - {item['chinese_translation']}")
            return "\n  ".join(formatted)

        if words_to_learn_list and words_to_review_list:
            return f"""词汇状态：
- 待学习：
  {format_words(words_to_learn_list)}
- 待复习：
  {format_words(words_to_review_list)}
指令：在对话中自然融入1-2个上述词汇，优先使用待复习词汇。如强行融入会影响对话流畅度则跳过。使用的词汇需在回复末尾的"used_words"字段中列出，同时必须包含对应的"part_of_speech"和"chinese_translation"字段。"""

        if words_to_learn_list and not words_to_review_list:
            return f"""词汇状态：
- 待学习：
  {format_words(words_to_learn_list)}
- 没有待复习的词语
指令：在对话中自然融入1-2个待学习词汇。如强行融入会影响对话流畅度则跳过。使用的词汇需在回复末尾的"used_words"字段中列出，同时必须包含对应的"part_of_speech"和"chinese_translation"字段。"""

        if not words_to_learn_list and words_to_review_list:
            return f"""词汇状态：
- 没有待学习的词语
- 待复习：
  {format_words(words_to_review_list)}
指令：在对话中自然融入1-2个待复习词汇。如强行融入会影响对话流畅度则跳过。使用的词汇需在回复末尾的"used_words"字段中列出，同时必须包含对应的"part_of_speech"和"chinese_translation"字段。"""

        return "进行自然对话即可，无需针对性使用词汇。"
        
    except Exception as e:
        logger.error(f"生成学习需求时出错: {e}")
        return "进行自然对话即可，无需针对性使用词汇。"

def _generate_learning_requirements_for_user_response(user_id, failed_words_info):
    """Generate learning requirements for user response."""
    try:

        if not failed_words_info:
            return _generate_learning_requirements(user_id)

        activated_plan = UserStudyPlan.objects.filter(
            user_id=user_id,
            is_activated=True
        ).first()
        
        if not activated_plan:

            words_list = []
            for word_info in failed_words_info:
                words_list.append(f"{word_info['word']} ({word_info['part_of_speech']}) - {word_info['chinese_translation']}")

            newline_indent = '\n  '
            words_str = newline_indent.join(words_list)
            
            return f"""词汇状态：
- 待学习：
  {words_str}
- 没有待复习的词语
指令：在对话中自然融入上述词汇。如强行融入会影响对话流畅度则跳过。使用的词汇需在回复末尾的"used_words"字段中列出，同时必须包含对应的"part_of_speech"和"chinese_translation"字段。"""

        words_to_learn = []
        words_to_review = []
        
        for word_info in failed_words_info:
            word_str = f"{word_info['word']} ({word_info['part_of_speech']}) - {word_info['chinese_translation']}"
            if not word_info['is_learned']:
                words_to_learn.append(word_str)
            elif not word_info['is_reviewed']:
                words_to_review.append(word_str)

        def format_words(words_list):
            if not words_list:
                return ""
            return "\n  ".join(words_list)

        if words_to_learn and words_to_review:
            return f"""词汇状态：
- 待学习：
  {format_words(words_to_learn)}
- 待复习：
  {format_words(words_to_review)}
指令：在对话中自然融入上述词汇。如强行融入会影响对话流畅度则跳过。使用的词汇需在回复末尾的"used_words"字段中列出，同时必须包含对应的"part_of_speech"和"chinese_translation"字段。"""

        if words_to_learn and not words_to_review:
            return f"""词汇状态：
- 待学习：
  {format_words(words_to_learn)}
- 没有待复习的词语
指令：在对话中自然融入上述词汇。如强行融入会影响对话流畅度则跳过。使用的词汇需在回复末尾的"used_words"字段中列出，同时必须包含对应的"part_of_speech"和"chinese_translation"字段。"""

        if not words_to_learn and words_to_review:
            return f"""词汇状态：
- 没有待学习的词语
- 待复习：
  {format_words(words_to_review)}
指令：在对话中自然融入上述词汇。如强行融入会影响对话流畅度则跳过。使用的词汇需在回复末尾的"used_words"字段中列出，同时必须包含对应的"part_of_speech"和"chinese_translation"字段。"""

        return _generate_learning_requirements(user_id)
        
    except Exception as e:
        logger.error(f"生成用户响应学习需求时出错: {e}")
        return _generate_learning_requirements(user_id)

def handle_device_object_detected(topic, payload):
    """Handle device object detected."""
    device_id = None
    object_name = None
    lock_acquired = False
    
    try:

        data = json.loads(payload)
        device_id = data.get('device_id')
        object_name = data.get('object_name')
        
        if not device_id:
            logger.error("收到 device/object_detected 消息，但缺少 device_id")
            _send_object_detected_response("unknown", "error", "缺少 device_id 字段")
            return

        if not _try_acquire_lock(device_id, "object_detected"):
            logger.warning(f"设备 {device_id} 的 object_detected 请求正在处理中，拒绝重复请求")
            _send_object_detected_response(device_id, "busy", "请求正在处理中，请稍后重试")
            return
        lock_acquired = True
        
        if not object_name:
            logger.error(f"收到 device/object_detected 消息，但缺少 object_name (device_id: {device_id})")
            _send_object_detected_response(device_id, "error", "缺少 object_name 字段")
            return
        
        with transaction.atomic():

            try:
                user = User.objects.get(device_id=device_id)
                user_id = user.id
                island_type = user.island_type or ""
            except User.DoesNotExist:
                logger.warning(f"收到 device/object_detected 消息，但未找到绑定 device_id={device_id} 的用户")
                _send_object_detected_response(device_id, "error", f"未找到绑定 device_id={device_id} 的用户")
                return
            
            if not island_type:
                logger.warning(f"用户 {user.username} (device_id: {device_id}) 的 island_type 为空")
                _send_object_detected_response(device_id, "error", "用户的 island_type 未设置")
                return

            object_identification = None
            description = None
            try:
                preset = PresetObjectIdentification.objects.get(
                    island_type=island_type,
                    object_name=object_name
                )
                object_identification = preset.object_identification
                description = preset.description
                logger.info(f"找到预设身份映射: {island_type}/{object_name} -> {object_identification}")
            except PresetObjectIdentification.DoesNotExist:
                logger.info(f"未找到预设身份映射: {island_type}/{object_name}，将保持 object_identification 为空")

            conversation = Conversation.objects.create(
                user_id=user_id,
                device_id=device_id,
                island_type=island_type,
                object_identification=object_identification,
                object_name=object_name,
                conversation_summary=None,
                is_active=True
            )
            conversation_id = conversation.id
            logger.info(f"创建新对话会话: conversation_id={conversation_id}, object_name={object_name}")

            conversation_num = 1
            last_conversation_summary = None
            
            try:
                memory = LongTermMemory.objects.get(
                    user_id=user_id,
                    device_id=device_id,
                    island_type=island_type,
                    object_name=object_name
                )

                memory.conversation_num += 1
                conversation_num = memory.conversation_num
                last_conversation_summary = memory.last_conversation_summary

                if object_identification:
                    conversation.object_identification = object_identification
                    conversation.save()
                    memory.object_identification = object_identification
                
                memory.save()
                logger.info(f"更新长期记忆: conversation_num={conversation_num}")
            except LongTermMemory.DoesNotExist:

                memory = LongTermMemory.objects.create(
                    user_id=user_id,
                    device_id=device_id,
                    island_type=island_type,
                    object_name=object_name,
                    object_identification=object_identification,
                    conversation_num=1,
                    last_conversation_summary=None
                )
                logger.info(f"创建新长期记忆记录: conversation_num=1")

            learning_requirements = _generate_learning_requirements(user_id)
            logger.info(f"生成学习需求: {learning_requirements[:100]}...")

            islands_progress = []
            try:
                activated_plans = UserStudyPlan.objects.filter(
                    user_id=user_id,
                    is_activated=True
                ).order_by('island_inner_id')
                
                for plan in activated_plans:
                    islands_progress.append({
                        "island_inner_id": plan.island_inner_id,
                        "learned_percentage": str(plan.learned_percentage),
                        "is_locked": plan.is_locked
                    })
                
                if islands_progress:
                    logger.info(f"找到 {len(islands_progress)} 个激活的岛屿计划")
            except Exception as e:
                logger.warning(f"查询激活学习计划时出错: {e}")

            system_prompt_1 = None
            system_prompt_2 = None
            system_prompt_3 = None
            system_prompt_4 = None
            
            try:
                prompt_config = AgentSystemPrompt.objects.get(island_type=island_type)
                system_prompt_1 = prompt_config.system_prompt_1
                system_prompt_2 = prompt_config.system_prompt_2
                system_prompt_3 = prompt_config.system_prompt_3
                system_prompt_4 = prompt_config.system_prompt_4
                logger.info(f"找到系统提示词配置: island_type={island_type}")
            except AgentSystemPrompt.DoesNotExist:
                logger.warning(f"未找到系统提示词配置: island_type={island_type}")

            agent_data = {
                "conversation_id": conversation_id,
                "device_id": device_id,
                "island_type": island_type,
                "object_identification": object_identification,
                "object_name": object_name,
                "learning_requirements": learning_requirements,
                "system_prompt_1": system_prompt_1,
                "system_prompt_2": system_prompt_2,
                "system_prompt_3": system_prompt_3,
                "system_prompt_4": system_prompt_4,
                "conversation_num": conversation_num,
                "last_conversation_summary": last_conversation_summary,
                "islands_progress": islands_progress if islands_progress else None
            }

            _send_object_detected_response(
                device_id,
                "success",
                "物体识别处理成功，数据已准备完成",
                agent_data
            )
            
            logger.info(f"物体识别处理完成: conversation_id={conversation_id}, object_name={object_name}")

            try:
                logger.info("开始调用Agent生成回复...")
                agent_response = invoke_agent(
                    conversation_id=conversation_id,
                    device_id=device_id,
                    island_type=island_type,
                    object_identification=object_identification,
                    object_name=object_name,
                    learning_requirements=learning_requirements,
                    system_prompt_1=system_prompt_1,
                    system_prompt_2=system_prompt_2,
                    system_prompt_3=system_prompt_3,
                    system_prompt_4=system_prompt_4,
                    conversation_num=conversation_num,
                    last_conversation_summary=last_conversation_summary,
                    is_first_talk=True,
                    human_message=None
                )
                
                logger.info(f"Agent生成回复成功: {agent_response.message[:50]}...")

                response_data = _process_agent_response(
                    agent_response=agent_response,
                    conversation_id=conversation_id,
                    user_id=user.id,
                    device_id=device_id,
                    island_type=island_type,
                    object_name=object_name
                )

                _send_agent_response(
                    device_id,
                    "success",
                    "Agent生成回复成功",
                    response_data
                )
                
                logger.info(f"Agent处理完成: conversation_id={conversation_id}")
                
            except Exception as e:
                logger.error(f"调用Agent或处理结果时出错: {e}", exc_info=True)
                _send_agent_response(
                    device_id,
                    "error",
                    f"Agent处理失败: {str(e)}",
                    None
                )
            
    except json.JSONDecodeError as e:
        logger.error(f"解析 device/object_detected 消息 JSON 失败: {e}, 原始消息: {payload}")
        if device_id:
            _send_object_detected_response(device_id, "error", f"JSON 解析失败: {str(e)}")
        else:
            _send_object_detected_response("unknown", "error", f"JSON 解析失败: {str(e)}")
    except Exception as e:
        logger.error(f"处理 device/object_detected 消息时出错: {e}", exc_info=True)
        if device_id:
            _send_object_detected_response(device_id, "error", f"处理消息时出错: {str(e)}")
        else:
            _send_object_detected_response("unknown", "error", f"处理消息时出错: {str(e)}")
    finally:

        if lock_acquired and device_id:
            _release_lock(device_id, "object_detected")

def handle_device_agent_type(topic, payload):
    """Handle device agent type."""
    device_id = None
    island_type = None
    device_battery = None
    lock_acquired = False
    
    try:

        data = json.loads(payload)
        device_id = data.get('device_id')
        island_type = data.get('island_type')
        device_battery = data.get('device_battery')
        
        if not device_id:
            logger.error("收到 device/agent_type 消息，但缺少 device_id")
            _send_response("unknown", "error", "缺少 device_id 字段")
            return

        if not _try_acquire_lock(device_id, "agent_type"):
            logger.warning(f"设备 {device_id} 的 agent_type 请求正在处理中，拒绝重复请求")
            _send_response(device_id, "busy", "请求正在处理中，请稍后重试")
            return
        lock_acquired = True
        
        if not island_type:
            logger.error(f"收到 device/agent_type 消息，但缺少 island_type (device_id: {device_id})")
            _send_response(device_id, "error", "缺少 island_type 字段")
            return

        try:
            with transaction.atomic():
                user = User.objects.get(device_id=device_id)
                user.island_type = island_type

                if device_battery is not None:
                    from decimal import Decimal, InvalidOperation
                    try:
                        user.device_battery = Decimal(str(device_battery))
                        logger.info(f"已更新用户 {user.username} 的 device_battery 为 {device_battery}")
                    except (InvalidOperation, ValueError) as e:
                        logger.warning(f"device_battery 值无效: {device_battery}, 错误: {e}")
                
                user.save()
                logger.info(f"已更新用户 {user.username} (device_id: {device_id}) 的 island_type 为 {island_type}")

                _send_response(
                    device_id, 
                    "success", 
                    f"island_type 已更新为 {island_type}", 
                    island_type,
                    str(user.device_battery) if user.device_battery is not None else None
                )
        except User.DoesNotExist:
            logger.warning(f"收到 device/agent_type 消息，但未找到绑定 device_id={device_id} 的用户")
            _send_response(device_id, "error", f"未找到绑定 device_id={device_id} 的用户")
        except Exception as e:
            logger.error(f"更新用户 island_type 时出错: {e}")
            _send_response(device_id, "error", f"更新失败: {str(e)}")
            
    except json.JSONDecodeError as e:
        logger.error(f"解析 device/agent_type 消息 JSON 失败: {e}, 原始消息: {payload}")
        if device_id:
            _send_response(device_id, "error", f"JSON 解析失败: {str(e)}")
        else:
            _send_response("unknown", "error", f"JSON 解析失败: {str(e)}")
    except Exception as e:
        logger.error(f"处理 device/agent_type 消息时出错: {e}")
        if device_id:
            _send_response(device_id, "error", f"处理消息时出错: {str(e)}")
        else:
            _send_response("unknown", "error", f"处理消息时出错: {str(e)}")
    finally:

        if lock_acquired and device_id:
            _release_lock(device_id, "agent_type")

def handle_device_user_response(topic, payload):
    """Handle device user response."""
    device_id = None
    conversation_id = None
    lock_acquired = False
    
    try:

        data = json.loads(payload)
        device_id = data.get('device_id')
        conversation_id = data.get('conversation_id')
        human_audio_message = data.get('human_audio_message', '')
        words_info = {
            'verb': data.get('verb'),
            'noun': data.get('noun'),
            'adjective': data.get('adjective'),
            'exclamation': data.get('exclamation'),
            'discourse_marker': data.get('discourse_marker'),
            'adverb': data.get('adverb')
        }
        
        if not device_id:
            logger.error("收到 device/user_response 消息，但缺少 device_id")
            _send_user_response_data_preparation("unknown", "error", "缺少 device_id 字段")
            return

        if not _try_acquire_lock(device_id, "user_response"):
            logger.warning(f"设备 {device_id} 的 user_response 请求正在处理中，拒绝重复请求")
            _send_user_response_data_preparation(device_id, "busy", "请求正在处理中，请稍后重试")
            return
        lock_acquired = True
        
        if conversation_id is None:
            logger.error(f"收到 device/user_response 消息，但缺少 conversation_id (device_id: {device_id})")
            _send_user_response_data_preparation(device_id, "error", "缺少 conversation_id 字段")
            return
        
        with transaction.atomic():

            try:
                user = User.objects.get(device_id=device_id)
                user_id = user.id
            except User.DoesNotExist:
                logger.warning(f"收到 device/user_response 消息，但未找到绑定 device_id={device_id} 的用户")
                _send_user_response_data_preparation(device_id, "error", f"未找到绑定 device_id={device_id} 的用户")
                return

            activated_plan = UserStudyPlan.objects.filter(
                user_id=user_id,
                is_activated=True
            ).first()

            has_words = any(words_info.values())

            words_mastery_result = None
            passed_words = []
            failed_words_info = []
            
            if has_words:
                try:
                    logger.info("开始调用单词掌握度判断Agent...")
                    mastery_response = invoke_word_mastery_agent(
                        human_message=human_audio_message,
                        words_info=words_info
                    )

                    words_mastery_result = {
                        'verb': mastery_response.verb,
                        'noun': mastery_response.noun,
                        'adjective': mastery_response.adjective,
                        'exclamation': mastery_response.exclamation,
                        'discourse_marker': mastery_response.discourse_marker,
                        'adverb': mastery_response.adverb
                    }
                    
                    logger.info(f"单词掌握度判断完成")

                    pos_mapping = {
                        'verb': 'verb',
                        'noun': 'noun',
                        'adjective': 'adjective',
                        'exclamation': 'exclamation',
                        'discourse_marker': 'discourse marker',
                        'adverb': 'adverb'
                    }

                    if not activated_plan:
                        logger.warning(f"用户 {user_id} 没有激活的学习计划，跳过单词状态更新")
                    else:
                        for pos_key, pos_value in pos_mapping.items():
                            word_result = words_mastery_result.get(pos_key)
                            if word_result and word_result.get('is_passed'):
                                word = word_result['word']
                                chinese_translation = word_result['chinese_translation']

                                try:
                                    ongoing_word = UserOngoingPlan.objects.get(
                                        user_id=user_id,
                                        plan_id=activated_plan.id,
                                        words=word,
                                        part_of_speech=pos_value,
                                        chinese_translation=chinese_translation
                                    )

                                    if ongoing_word.is_learned and ongoing_word.reviewed_typed == 1:
                                        ongoing_word.reviewed_typed = 2
                                        ongoing_word.is_reviewed = True
                                        ongoing_word.reviewed_time = timezone.now()
                                        logger.info(f"单词 {word} 已学习且复习过1次，设置为复习2次")
                                    elif not ongoing_word.is_learned:

                                        ongoing_word.is_learned = True
                                        ongoing_word.learned_time = timezone.now()
                                        logger.info(f"单词 {word} 标记为已学习，reviewed_typed保持为0")

                                    ongoing_word.save()
                                    passed_words.append({
                                        'word': word,
                                        'part_of_speech': pos_value,
                                        'chinese_translation': chinese_translation
                                    })
                                except UserOngoingPlan.DoesNotExist:
                                    logger.warning(f"未在user_ongoing_plan中找到单词: {word} ({pos_value}) - {chinese_translation}")

                    if passed_words and activated_plan:
                        try:
                            from user_system.utils import update_learned_percentage
                            update_learned_percentage(plan_id=activated_plan.id)
                            logger.info(f"已更新学习计划 {activated_plan.id} 的 learned_percentage")
                        except Exception as e:
                            logger.error(f"更新学习计划的 learned_percentage 时出错: {e}", exc_info=True)

                    if activated_plan:
                        for pos_key, pos_value in pos_mapping.items():
                            word_result = words_mastery_result.get(pos_key)
                            if word_result and not word_result.get('is_passed'):
                                word = word_result['word']
                                chinese_translation = word_result['chinese_translation']

                                try:
                                    failed_word = UserOngoingPlan.objects.filter(
                                        user_id=user_id,
                                        plan_id=activated_plan.id,
                                        words=word,
                                        part_of_speech=pos_value,
                                        chinese_translation=chinese_translation
                                    ).first()
                                    
                                    if failed_word:
                                        failed_words_info.append({
                                            'word': word,
                                            'part_of_speech': pos_value,
                                            'chinese_translation': chinese_translation,
                                            'is_learned': failed_word.is_learned,
                                            'is_reviewed': failed_word.is_reviewed
                                        })
                                    else:

                                        failed_words_info.append({
                                            'word': word,
                                            'part_of_speech': pos_value,
                                            'chinese_translation': chinese_translation,
                                            'is_learned': False,
                                            'is_reviewed': False
                                        })
                                except Exception as e:
                                    logger.error(f"查询未pass单词状态时出错: {e}")
                                
                except Exception as e:
                    logger.error(f"调用单词掌握度判断Agent时出错: {e}", exc_info=True)
                    _send_user_response_data_preparation(device_id, "error", f"单词掌握度判断失败: {str(e)}")
                    return

            learning_requirements = _generate_learning_requirements_for_user_response(
                user_id=user_id,
                failed_words_info=failed_words_info
            )
            logger.info(f"生成学习需求: {learning_requirements[:100]}...")

            try:
                conversation = Conversation.objects.get(id=conversation_id)
                device_id_from_db = conversation.device_id
                island_type = conversation.island_type
                object_identification = conversation.object_identification
                object_name = conversation.object_name
            except Conversation.DoesNotExist:
                logger.error(f"未找到conversation_id={conversation_id}的对话记录")
                _send_user_response_data_preparation(device_id, "error", f"未找到conversation_id={conversation_id}的对话记录")
                return

            system_prompt_1 = None
            system_prompt_2 = None
            system_prompt_3 = None
            system_prompt_4 = None
            
            try:
                prompt_config = AgentSystemPrompt.objects.get(island_type=island_type)
                system_prompt_1 = prompt_config.system_prompt_1
                system_prompt_2 = prompt_config.system_prompt_2
                system_prompt_3 = prompt_config.system_prompt_3
                system_prompt_4 = prompt_config.system_prompt_4
                logger.info(f"找到系统提示词配置: island_type={island_type}")
            except AgentSystemPrompt.DoesNotExist:
                logger.warning(f"未找到系统提示词配置: island_type={island_type}")

            conversation_num = 1
            last_conversation_summary = None
            
            try:
                memory = LongTermMemory.objects.get(
                    user_id=user_id,
                    device_id=device_id_from_db,
                    island_type=island_type,
                    object_name=object_name
                )
                conversation_num = memory.conversation_num
                last_conversation_summary = memory.last_conversation_summary
                logger.info(f"找到长期记忆: conversation_num={conversation_num}")
            except LongTermMemory.DoesNotExist:
                logger.warning(f"未找到长期记忆记录")

            islands_progress = []
            try:
                activated_plans = UserStudyPlan.objects.filter(
                    user_id=user_id,
                    is_activated=True
                ).order_by('island_inner_id')
                
                for plan in activated_plans:
                    islands_progress.append({
                        "island_inner_id": plan.island_inner_id,
                        "learned_percentage": str(plan.learned_percentage),
                        "is_locked": plan.is_locked
                    })
                
                if islands_progress:
                    logger.info(f"找到 {len(islands_progress)} 个激活的岛屿计划")
            except Exception as e:
                logger.warning(f"查询激活学习计划时出错: {e}")

            agent_data = {
                "conversation_id": conversation_id,
                "device_id": device_id_from_db,
                "island_type": island_type,
                "object_identification": object_identification,
                "object_name": object_name,
                "learning_requirements": learning_requirements,
                "system_prompt_1": system_prompt_1,
                "system_prompt_2": system_prompt_2,
                "system_prompt_3": system_prompt_3,
                "system_prompt_4": system_prompt_4,
                "conversation_num": conversation_num,
                "last_conversation_summary": last_conversation_summary,
                "is_first_talk": False,
                "islands_progress": islands_progress if islands_progress else None
            }

            _send_user_response_data_preparation(
                device_id_from_db,
                "success",
                "用户响应处理成功，数据已准备完成",
                agent_data,
                words_mastery_result
            )
            
            logger.info(f"用户响应处理完成: conversation_id={conversation_id}")

            try:
                logger.info("开始调用主Agent生成回复...")
                agent_response = invoke_agent(
                    conversation_id=conversation_id,
                    device_id=device_id_from_db,
                    island_type=island_type,
                    object_identification=object_identification,
                    object_name=object_name,
                    learning_requirements=learning_requirements,
                    system_prompt_1=system_prompt_1,
                    system_prompt_2=system_prompt_2,
                    system_prompt_3=system_prompt_3,
                    system_prompt_4=system_prompt_4,
                    conversation_num=conversation_num,
                    last_conversation_summary=last_conversation_summary,
                    is_first_talk=False,
                    human_message=human_audio_message
                )
                
                logger.info(f"Agent生成回复成功: {agent_response.message[:50]}...")

                response_data = _process_agent_response(
                    agent_response=agent_response,
                    conversation_id=conversation_id,
                    user_id=user_id,
                    device_id=device_id_from_db,
                    island_type=island_type,
                    object_name=object_name
                )

                Message.objects.create(
                    user_id=user_id,
                    device_id=device_id_from_db,
                    conversation_id=conversation_id,
                    sender='human',
                    message=human_audio_message,
                    words_used=None,
                    mood_id=None
                )

                _send_user_response_agent_response(
                    device_id_from_db,
                    "success",
                    "Agent生成回复成功",
                    response_data
                )
                
                logger.info(f"用户响应Agent处理完成: conversation_id={conversation_id}")
                
            except Exception as e:
                logger.error(f"调用Agent或处理结果时出错: {e}", exc_info=True)
                _send_user_response_agent_response(
                    device_id_from_db,
                    "error",
                    f"Agent处理失败: {str(e)}",
                    None
                )
            
    except json.JSONDecodeError as e:
        logger.error(f"解析 device/user_response 消息 JSON 失败: {e}, 原始消息: {payload}")
        if device_id:
            _send_user_response_data_preparation(device_id, "error", f"JSON 解析失败: {str(e)}")
        else:
            _send_user_response_data_preparation("unknown", "error", f"JSON 解析失败: {str(e)}")
    except Exception as e:
        logger.error(f"处理 device/user_response 消息时出错: {e}", exc_info=True)
        if device_id:
            _send_user_response_data_preparation(device_id, "error", f"处理消息时出错: {str(e)}")
        else:
            _send_user_response_data_preparation("unknown", "error", f"处理消息时出错: {str(e)}")
    finally:

        if lock_acquired and device_id:
            _release_lock(device_id, "user_response")

def handle_device_user_stop(topic, payload):
    """Handle device user stop."""
    device_id = None
    conversation_id = None
    lock_acquired = False
    
    try:

        data = json.loads(payload)
        device_id = data.get('device_id')
        conversation_id = data.get('conversation_id')
        
        if not device_id:
            logger.error("收到 device/user_stop 消息，但缺少 device_id")
            _send_user_stop_response("unknown", "error", "缺少 device_id 字段")
            return

        if not _try_acquire_lock(device_id, "user_stop"):
            logger.warning(f"设备 {device_id} 的 user_stop 请求正在处理中，拒绝重复请求")
            _send_user_stop_response(device_id, "busy", "请求正在处理中，请稍后重试")
            return
        lock_acquired = True
        
        if conversation_id is None:
            logger.error(f"收到 device/user_stop 消息，但缺少 conversation_id (device_id: {device_id})")
            _send_user_stop_response(device_id, "error", "缺少 conversation_id 字段")
            return
        
        with transaction.atomic():

            try:
                conversation = Conversation.objects.get(id=conversation_id)
                user_id = conversation.user_id
                device_id_from_db = conversation.device_id
                island_type = conversation.island_type
                object_name = conversation.object_name
                object_identification = conversation.object_identification or ""
            except Conversation.DoesNotExist:
                logger.error(f"未找到conversation_id={conversation_id}的对话记录")
                _send_user_stop_response(device_id, "error", f"未找到conversation_id={conversation_id}的对话记录")
                return

            messages = Message.objects.filter(
                conversation_id=conversation_id
            ).order_by('created_at').values('sender', 'message', 'created_at')
            
            if not messages.exists():
                logger.warning(f"conversation_id={conversation_id}的对话没有消息记录")
                _send_user_stop_response(device_id, "error", "该对话没有消息记录，无法生成总结")
                return

            messages_list = []
            for msg in messages:
                messages_list.append({
                    "sender": msg['sender'],
                    "message": msg['message'],
                    "created_at": msg['created_at'].isoformat() if msg['created_at'] else ""
                })
            
            logger.info(f"读取到 {len(messages_list)} 条消息记录")

            try:
                logger.info("开始调用对话总结生成Agent...")
                conversation_summary = invoke_conversation_summary_agent(
                    object_identification=object_identification,
                    messages=messages_list
                )
                
                logger.info(f"对话总结生成成功: {conversation_summary[:50]}...")

                conversation.conversation_summary = conversation_summary
                conversation.is_active = False
                conversation.save()
                logger.info(f"已更新conversation的conversation_summary和is_active状态")

                try:
                    memory = LongTermMemory.objects.get(
                        user_id=user_id,
                        device_id=device_id,
                        island_type=island_type,
                        object_name=object_name
                    )
                    memory.last_conversation_summary = conversation_summary
                    memory.save()
                    logger.info(f"已更新long_term_memory的last_conversation_summary")
                except LongTermMemory.DoesNotExist:
                    logger.warning(f"未找到long_term_memory记录，跳过更新")

                _send_user_stop_response(
                    device_id,
                    "success",
                    "对话已结束，总结已生成",
                    conversation_summary
                )
                
                logger.info(f"用户停止对话处理完成: conversation_id={conversation_id}")
                
            except Exception as e:
                logger.error(f"调用对话总结生成Agent时出错: {e}", exc_info=True)
                _send_user_stop_response(
                    device_id,
                    "error",
                    f"生成对话总结失败: {str(e)}",
                    None
                )
            
    except json.JSONDecodeError as e:
        logger.error(f"解析 device/user_stop 消息 JSON 失败: {e}, 原始消息: {payload}")
        if device_id:
            _send_user_stop_response(device_id, "error", f"JSON 解析失败: {str(e)}")
        else:
            _send_user_stop_response("unknown", "error", f"JSON 解析失败: {str(e)}")
    except Exception as e:
        logger.error(f"处理 device/user_stop 消息时出错: {e}", exc_info=True)
        if device_id:
            _send_user_stop_response(device_id, "error", f"处理消息时出错: {str(e)}")
        else:
            _send_user_stop_response("unknown", "error", f"处理消息时出错: {str(e)}")
    finally:

        if lock_acquired and device_id:
            _release_lock(device_id, "user_stop")

