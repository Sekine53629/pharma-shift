"""Celery tasks for leave management alerts."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def check_paid_leave_alerts():
    """Check all active staff for mandatory paid leave compliance.

    Sends Zoom notifications for:
    - 30 days before deadline (warning)
    - 7 days before deadline (urgent)
    - Past deadline (overdue — immediate SV alert)
    """
    from apps.notifications.services import notify_store, send_zoom_message
    from apps.staff.models import Staff

    from .services import check_mandatory_paid_leave

    alerts_sent = 0

    for staff in Staff.objects.filter(is_active=True).select_related("store"):
        alert = check_mandatory_paid_leave(staff)
        if not alert:
            continue

        level = alert["level"]
        message = f"【義務有給アラート】{alert['message']}\n対象: {alert['staff_name']}\n期限: {alert['deadline']}"

        if level == "overdue":
            trigger = "paid_leave_overdue"
        elif level == "urgent":
            trigger = "paid_leave_urgent"
        else:
            trigger = "paid_leave_warning"

        # Notify the staff member's store
        if staff.store:
            notify_store(staff.store, message, trigger)
            alerts_sent += 1

    logger.info("Paid leave alert check complete: %d alerts sent", alerts_sent)
    return alerts_sent


@shared_task
def check_leave_request_deadline():
    """Remind stores 3 days before leave request deadline."""
    from datetime import timedelta

    from django.utils import timezone

    from apps.notifications.services import notify_store
    from apps.shifts.models import ShiftPeriod

    today = timezone.now().date()
    target_date = today + timedelta(days=3)

    upcoming_periods = ShiftPeriod.objects.filter(
        request_deadline=target_date,
        is_finalized=False,
    )

    from apps.stores.models import Store

    sent = 0
    for period in upcoming_periods:
        for store in Store.objects.filter(is_active=True):
            message = (
                f"【希望休締め切り3日前】\n"
                f"シフト期間: {period.start_date}〜{period.end_date}\n"
                f"申請締め切り: {period.request_deadline}\n"
                f"未提出の方は早急に申請してください。"
            )
            notify_store(store, message, "leave_deadline_soon")
            sent += 1

    logger.info("Leave deadline reminder: %d notifications sent", sent)
    return sent
