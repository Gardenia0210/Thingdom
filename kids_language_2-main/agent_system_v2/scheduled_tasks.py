"""Scheduled tasks."""
import logging
import threading
import time
from datetime import timedelta
from django.utils import timezone
from django.db import connection

logger = logging.getLogger(__name__)

THAW_DURATION = {
    "learning": timedelta(hours=24),
    "review_due": timedelta(days=3),

}

TASK_INTERVAL_SECONDS = 1800

def thaw_frozen_words():
    """Thaw frozen words."""
    try:
        connection.ensure_connection()

        from user_system.models import UserOngoingPlan

        logger.info("开始执行定时任务：解冻冻结单词")

        now = timezone.now()
        total_thawed = 0

        for learned_type, duration in THAW_DURATION.items():
            threshold_time = now - duration

            frozen_words = UserOngoingPlan.objects.filter(
                is_frozen=True,
                learned_type=learned_type,
                updated_at__lt=threshold_time,
            )

            count = frozen_words.count()
            if count > 0:
                frozen_words.update(is_frozen=False)
                total_thawed += count
                logger.info(
                    f"已解冻 {count} 个 learned_type={learned_type} 的单词"
                    f"（阈值: {duration}）"
                )

        logger.info(f"定时任务完成：解冻冻结单词，共解冻 {total_thawed} 个")

    except Exception as e:
        logger.error(f"解冻冻结单词定时任务出错: {e}", exc_info=True)

def update_all_plans_learned_percentage():
    """Update all plans learned percentage."""
    try:
        connection.ensure_connection()

        from user_system.utils import update_learned_percentage

        logger.info("开始执行定时任务：更新所有学习计划的 learned_percentage")

        updated_count = update_learned_percentage()

        logger.info(
            f"定时任务完成：更新 learned_percentage，共更新 {updated_count} 个计划"
        )

    except Exception as e:
        logger.error(f"更新 learned_percentage 定时任务出错: {e}", exc_info=True)

def start_scheduled_tasks():
    """Start scheduled tasks."""
    def run_periodically():
        """Run periodically."""

        time.sleep(60)

        try:
            thaw_frozen_words()
            update_all_plans_learned_percentage()
        except Exception as e:
            logger.error(f"定时任务首次执行出错: {e}", exc_info=True)

        while True:
            try:
                time.sleep(TASK_INTERVAL_SECONDS)
                thaw_frozen_words()
                update_all_plans_learned_percentage()
            except Exception as e:
                logger.error(f"定时任务执行出错: {e}", exc_info=True)

    task_thread = threading.Thread(target=run_periodically, daemon=True)
    task_thread.start()
    logger.info(
        f"agent_system_v2 定时任务线程已启动，"
        f"每 {TASK_INTERVAL_SECONDS // 60} 分钟执行一次"
        f"（解冻冻结单词 + 更新 learned_percentage）"
    )
