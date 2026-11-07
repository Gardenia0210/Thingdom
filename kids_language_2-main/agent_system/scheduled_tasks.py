"""Scheduled tasks."""
import logging
import threading
import time
from datetime import timedelta
from django.utils import timezone
from django.db import connection

logger = logging.getLogger(__name__)

def check_and_update_review_status():
    """Check and update review status."""
    try:

        connection.ensure_connection()

        from user_system.models import User, UserStudyPlan, UserOngoingPlan
        
        logger.info("开始执行定时任务：检查并更新复习状态")

        users_with_devices = User.objects.filter(device_id__isnull=False).exclude(device_id='')
        
        updated_count = 0
        
        for user in users_with_devices:
            try:

                activated_plans = UserStudyPlan.objects.filter(
                    user=user,
                    is_activated=True
                )
                
                for plan in activated_plans:

                    words_to_check = UserOngoingPlan.objects.filter(
                        plan=plan,
                        is_learned=True,
                        reviewed_typed=0
                    )

                    sixty_minutes_ago = timezone.now() - timedelta(minutes=60)

                    for word_record in words_to_check:
                        if word_record.learned_time and word_record.learned_time < sixty_minutes_ago:

                            word_record.reviewed_typed = 1
                            word_record.save()
                            updated_count += 1
                            logger.debug(
                                f"用户 {user.username} 的单词 {word_record.words} "
                                f"({word_record.part_of_speech}) 已学习超过60分钟，设置 reviewed_typed=1"
                            )
            
            except Exception as e:
                logger.error(f"处理用户 {user.username} 的复习状态时出错: {e}", exc_info=True)
                continue
        
        logger.info(f"定时任务完成：检查并更新复习状态，共更新 {updated_count} 条记录")
        
    except Exception as e:
        logger.error(f"执行定时任务时出错: {e}", exc_info=True)

def update_all_plans_learned_percentage():
    """Update all plans learned percentage."""
    try:

        connection.ensure_connection()

        from user_system.utils import update_learned_percentage
        
        logger.info("开始执行定时任务：更新所有学习计划的 learned_percentage")

        updated_count = update_learned_percentage()
        
        logger.info(f"定时任务完成：更新所有学习计划的 learned_percentage，共更新 {updated_count} 个计划")
        
    except Exception as e:
        logger.error(f"执行定时任务时出错: {e}", exc_info=True)

def start_scheduled_tasks():
    """Start scheduled tasks."""
    def run_periodically():
        """Run periodically."""

        try:
            check_and_update_review_status()
            update_all_plans_learned_percentage()
        except Exception as e:
            logger.error(f"定时任务首次执行出错: {e}", exc_info=True)

        while True:
            try:

                time.sleep(1800)

                check_and_update_review_status()
                update_all_plans_learned_percentage()
            except Exception as e:
                logger.error(f"定时任务执行出错: {e}", exc_info=True)

    task_thread = threading.Thread(target=run_periodically, daemon=True)
    task_thread.start()
    logger.info("定时任务线程已启动，每30分钟检查一次复习状态并更新所有学习计划的 learned_percentage")

