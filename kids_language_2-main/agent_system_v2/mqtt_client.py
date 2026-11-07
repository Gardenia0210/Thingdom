"""Mqtt client."""
import paho.mqtt.client as mqtt
import json
import logging
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
from django.conf import settings

logger = logging.getLogger(__name__)

_message_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="mqtt_v2_handler_")

class MQTTClientV2:
    """Mqttclientv2."""
    _instance = None
    _client = None
    _connected = False
    _connecting = False
    _topic_handlers = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MQTTClientV2, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self._initialize_client()

    def _initialize_client(self):
        """Initialize client."""
        client_id = f"{settings.MQTT_CLIENT_ID_PREFIX}_v2_{uuid.uuid4().hex[:8]}"

        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            protocol=mqtt.MQTTv5,
        )

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.on_publish = self._on_publish
        self._client.on_subscribe = self._on_subscribe

        if settings.MQTT_BROKER_USERNAME:
            self._client.username_pw_set(
                settings.MQTT_BROKER_USERNAME,
                settings.MQTT_BROKER_PASSWORD,
            )

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        """On connect."""
        if reason_code == 0:
            self._connected = True
            self._connecting = False
            logger.info(
                f"MQTT v2 客户端已连接到 "
                f"{settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}"
            )

            for topic, _cb in list(self._topic_handlers.items()):
                try:
                    result = self._client.subscribe(topic, qos=1)
                    logger.info(f"连接成功后重新订阅主题: {topic}")
                except Exception as e:
                    logger.error(f"重新订阅主题 {topic} 时出错: {e}")
        else:
            self._connected = False
            self._connecting = False
            logger.error(f"MQTT v2 连接失败，reason_code: {reason_code}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        """On disconnect."""
        self._connected = False
        logger.warning(f"MQTT v2 客户端已断开连接，reason_code: {reason_code}")

    def _on_message(self, client, userdata, msg):
        """On message."""
        try:
            payload = msg.payload.decode("utf-8")
            topic = msg.topic
            logger.info(f"收到 MQTT v2 消息 - Topic: {topic}, Payload: {payload}")

            handler = self._topic_handlers.get(topic)
            if not handler:
                for pattern, handler_func in list(self._topic_handlers.items()):
                    if self._topic_matches(pattern, topic):
                        handler = handler_func
                        break

            if handler:
                _message_executor.submit(self._execute_handler, handler, topic, payload)
            else:
                logger.debug(f"未找到主题 {topic} 的处理函数")
        except Exception as e:
            logger.error(f"处理 MQTT v2 消息时出错: {e}", exc_info=True)

    def _execute_handler(self, handler, topic, payload):
        """Execute handler."""
        try:
            from django.db import connection
            connection.ensure_connection()
            handler(topic, payload)
        except Exception as e:
            logger.error(
                f"执行 MQTT v2 消息处理函数时出错 (topic={topic}): {e}",
                exc_info=True,
            )
        finally:
            from django.db import connection
            connection.close()

    def _on_publish(self, client, userdata, mid, reason_code, properties):
        """On publish."""
        logger.debug(f"MQTT v2 消息已发布，消息ID: {mid}")

    def _on_subscribe(self, client, userdata, mid, reason_code_list, properties):
        """On subscribe."""
        logger.info(f"MQTT v2 订阅成功，消息ID: {mid}, reason_codes: {reason_code_list}")

    @staticmethod
    def _topic_matches(pattern, topic):
        """Topic matches."""
        pattern_parts = pattern.split("/")
        topic_parts = topic.split("/")

        if len(pattern_parts) != len(topic_parts) and "#" not in pattern:
            return False

        for i, part in enumerate(pattern_parts):
            if part == "#":
                return True
            if part == "+":
                continue
            if i >= len(topic_parts) or part != topic_parts[i]:
                return False
        return True

    def connect(self):
        """Connect."""
        if self._connected:
            logger.debug("MQTT v2 客户端已连接，跳过重复连接")
            return
        if self._connecting:
            logger.debug("MQTT v2 客户端正在连接中，跳过重复连接")
            return
        try:
            self._connecting = True
            self._client.connect(
                settings.MQTT_BROKER_HOST,
                settings.MQTT_BROKER_PORT,
                settings.MQTT_KEEPALIVE,
            )
            self._client.loop_start()
            logger.info("MQTT v2 客户端开始连接...")
        except Exception as e:
            self._connecting = False
            logger.error(f"MQTT v2 连接异常: {e}")
            raise

    def disconnect(self):
        """Disconnect."""
        if self._connected:
            self._client.loop_stop()
            self._client.disconnect()
            logger.info("MQTT v2 客户端已断开连接")

    def publish(self, topic, payload, qos=1, retain=False):
        """Publish."""
        if not self._connected:
            logger.warning("MQTT v2 客户端未连接，尝试连接...")
            self.connect()

        try:
            if isinstance(payload, dict):
                payload = json.dumps(payload, ensure_ascii=False)
            result = self._client.publish(topic, payload, qos=qos, retain=retain)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"消息已发布到主题: {topic}")
                return True
            else:
                logger.error(f"发布消息失败，返回码: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"发布 MQTT v2 消息时出错: {e}")
            return False

    def subscribe(self, topic, qos=1, callback=None):
        """Subscribe."""
        if callback:
            self._topic_handlers[topic] = callback
            logger.info(f"已注册主题 {topic} 的处理函数 (v2)")

        if not self._connected and not self._connecting:
            logger.warning("MQTT v2 客户端未连接，尝试连接...")
            self.connect()

        if self._connected:
            try:
                result = self._client.subscribe(topic, qos=qos)
                if result[0] == mqtt.MQTT_ERR_SUCCESS:
                    logger.info(f"已订阅主题: {topic}")
                    return True
                else:
                    logger.error(f"订阅主题失败，返回码: {result[0]}")
                    return False
            except Exception as e:
                logger.error(f"订阅 MQTT v2 主题时出错: {e}")
                return False
        else:
            logger.info(f"MQTT v2 正在连接中，主题 {topic} 将在连接成功后订阅")
            return True

    def unsubscribe(self, topic):
        """Unsubscribe."""
        if self._connected:
            self._client.unsubscribe(topic)
            if topic in self._topic_handlers:
                del self._topic_handlers[topic]
            logger.info(f"已取消订阅主题: {topic}")

    @property
    def is_connected(self):
        """Is connected."""
        return self._connected

mqtt_client_v2 = MQTTClientV2()
