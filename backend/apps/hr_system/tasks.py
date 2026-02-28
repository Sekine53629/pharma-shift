"""Celery tasks for HR evaluation bias monitoring."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def check_all_evaluator_bias():
    """全評価者のバイアスをチェックし、異常があれば管理者に通知"""
    from apps.notifications.services import send_zoom_message
    from apps.staff.models import Staff

    from .models import HrEvaluation
    from .services import check_evaluator_bias

    evaluator_ids = (
        HrEvaluation.objects.filter(evaluation_type="supervisor")
        .values_list("evaluator_id", flat=True)
        .distinct()
    )

    alerts = []
    for evaluator_id in evaluator_ids:
        result = check_evaluator_bias(evaluator_id)
        if result and result.get("alert"):
            alerts.append(result)

            # 評価者名を取得してログ
            evaluator = Staff.objects.filter(id=evaluator_id).first()
            evaluator_name = evaluator.name if evaluator else f"ID:{evaluator_id}"
            logger.warning(
                "Evaluator bias detected: %s (ratio=%.2f, avg=%.2f)",
                evaluator_name,
                result["evaluator_ratio"],
                result["average_ratio"],
            )

    if alerts:
        # 管理者に通知
        message = (
            f"【評価バイアス検知】{len(alerts)}名の評価者に偏りが検出されました。\n"
            "管理画面から詳細を確認してください。"
        )
        # admin ロールの全ユーザーに通知
        from apps.accounts.models import User

        admin_users = User.objects.filter(is_active=True)
        for user in admin_users:
            if user.has_role("admin") and hasattr(user, "staff_profile"):
                staff = user.staff_profile
                if staff.store and staff.store.zoom_account:
                    send_zoom_message(
                        staff.store.zoom_account, message, "evaluation_bias"
                    )

    logger.info("Evaluator bias check complete: %d alerts", len(alerts))
    return len(alerts)
