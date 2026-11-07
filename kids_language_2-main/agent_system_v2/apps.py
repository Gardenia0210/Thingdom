from django.apps import AppConfig
import logging
import os

logger = logging.getLogger(__name__)

_initialized = False

class AgentSystemV2Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "agent_system_v2"

    def ready(self):
        """Ready."""
        from django.conf import settings
        if not settings.MQTT_ENABLED:
            return
        global _initialized

        if _initialized:
            logger.debug("Agent System V2 应用已初始化，跳过重复初始化")
            return

        run_main = os.environ.get("RUN_MAIN")

        if run_main is not None and run_main != "true":
            logger.debug(f"跳过非主进程初始化 (RUN_MAIN={run_main})")
            return

        if run_main is None:
            import sys
            if "runserver" in " ".join(sys.argv):
                logger.debug(
                    f"跳过开发服务器重载进程初始化 "
                    f"(RUN_MAIN={run_main}, 命令: {' '.join(sys.argv)})"
                )
                return

        process_id = os.getpid()
        logger.info(
            f"开始初始化 Agent System V2 应用 "
            f"(进程ID: {process_id}, RUN_MAIN={run_main})"
        )

        try:
            from .mqtt_client import mqtt_client_v2
            from .mqtt_handlers import (
                handle_device_agent_type,
                handle_object_detected_v2,
                handle_user_response_v2,
                handle_user_stop_v2,
            )

            try:
                logger.info(
                    f"正在连接 MQTT Broker "
                    f"({os.getenv('MQTT_BROKER_HOST', 'localhost')}:"
                    f"{os.getenv('MQTT_BROKER_PORT', '1883')})..."
                )
                mqtt_client_v2.connect()
                logger.info("MQTT v2 客户端连接请求已发送")
            except Exception as e:
                logger.error(f"MQTT v2 客户端连接失败: {e}", exc_info=True)
                return

            mqtt_client_v2.subscribe(
                topic="device/agent_type",
                qos=1,
                callback=handle_device_agent_type,
            )

            mqtt_client_v2.subscribe(
                topic="device/object_detected_v2",
                qos=1,
                callback=handle_object_detected_v2,
            )

            mqtt_client_v2.subscribe(
                topic="device/user_response_v2",
                qos=1,
                callback=handle_user_response_v2,
            )

            mqtt_client_v2.subscribe(
                topic="device/user_stop_v2",
                qos=1,
                callback=handle_user_stop_v2,
            )

            try:
                from .scheduled_tasks import start_scheduled_tasks
                start_scheduled_tasks()
            except Exception as e:
                logger.error(f"启动定时任务失败: {e}", exc_info=True)

            _initialized = True
            logger.info(
                "Agent System V2 应用已初始化，MQTT 主题订阅完成 "
                "(device/agent_type, device/object_detected_v2, "
                "device/user_response_v2, device/user_stop_v2)"
            )

        except Exception as e:
            logger.error(f"初始化 Agent System V2 应用时出错: {e}")
