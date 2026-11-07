"""Utils."""
from decimal import Decimal
from .models import UserStudyPlan, UserOngoingPlan, DictChapter
import logging

logger = logging.getLogger(__name__)

UNLOCK_THRESHOLD = Decimal('80.00')

def update_learned_percentage(plan_id=None, user_id=None):
    """Update learned percentage."""

    WEIGHT_MAP = {
        'not_started': 0,
        'learning': 1,
        'review_due': 2,
        'mastered': 3,
    }
    MAX_SCORE = Decimal('60')

    updated_count = 0

    try:

        if plan_id:
            plans = UserStudyPlan.objects.filter(id=plan_id).select_related('dictionary')
        elif user_id:
            plans = UserStudyPlan.objects.filter(user_id=user_id).select_related('dictionary')
        else:
            plans = UserStudyPlan.objects.all().select_related('dictionary')

        unlock_check_set = set()

        for plan in plans:
            try:

                ongoing_words = UserOngoingPlan.objects.filter(
                    plan_id=plan.id
                ).values_list('learned_type', flat=True)

                word_list = list(ongoing_words)
                if not word_list:
                    logger.warning(
                        f"计划 {plan.id} (字典 {plan.dictionary_id}, 章节 {plan.chapter_inner_id}) "
                        f"在 user_ongoing_plan 中没有记录，跳过更新"
                    )
                    continue

                total_score = sum(WEIGHT_MAP.get(lt, 0) for lt in word_list)

                percentage = Decimal(total_score) / MAX_SCORE * Decimal('100')

                percentage = min(percentage, Decimal('100.00'))
                percentage = percentage.quantize(Decimal('0.01'))

                plan.learned_percentage = percentage
                plan.save(update_fields=['learned_percentage'])

                updated_count += 1
                logger.debug(
                    f"更新计划 {plan.id} (章节 {plan.chapter_inner_id}) 的 learned_percentage: "
                    f"total_score={total_score}, word_count={len(word_list)}, "
                    f"percentage={percentage}"
                )

                unlock_check_set.add((plan.user_id, plan.dictionary_id))

            except Exception as e:
                logger.error(f"更新计划 {plan.id} 的 learned_percentage 时出错: {e}", exc_info=True)
                continue

        for user_id_check, dict_id in unlock_check_set:
            try:
                check_and_unlock_next_chapter(user_id_check, dict_id)
            except Exception as e:
                logger.error(f"检查解锁章节时出错 (user={user_id_check}, dict={dict_id}): {e}", exc_info=True)

        logger.info(f"learned_percentage 更新完成，共更新 {updated_count} 个计划")
        return updated_count

    except Exception as e:
        logger.error(f"更新 learned_percentage 时出错: {e}", exc_info=True)
        return updated_count

def check_and_unlock_next_chapter(user_id, dictionary_id):
    """Check and unlock next chapter."""
    unlocked_count = 0

    try:
        plans = list(UserStudyPlan.objects.filter(
            user_id=user_id,
            dictionary_id=dictionary_id
        ).order_by('chapter_inner_id'))

        if not plans:
            return 0

        for i, plan in enumerate(plans):
            if not plan.is_locked and plan.learned_percentage >= UNLOCK_THRESHOLD:
                if i + 1 < len(plans):
                    next_plan = plans[i + 1]
                    if next_plan.is_locked:
                        next_plan.is_locked = False
                        next_plan.save(update_fields=['is_locked'])
                        unlocked_count += 1
                        logger.info(
                            f"已解锁章节: user={user_id}, dict={dictionary_id}, "
                            f"chapter={next_plan.chapter_inner_id} "
                            f"(前一章节进度: {plan.learned_percentage}%)"
                        )

        return unlocked_count

    except Exception as e:
        logger.error(f"检查解锁章节时出错: {e}", exc_info=True)
        return unlocked_count
