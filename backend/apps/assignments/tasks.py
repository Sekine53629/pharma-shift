"""Celery tasks for assignment management."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def alert_unfilled_slots():
    """Alert SVs about unfilled high-priority support slots (P1/P2)."""
    from django.conf import settings

    from apps.notifications.services import send_zoom_message

    from .models import SupportSlot

    unfilled = SupportSlot.objects.filter(
        is_filled=False,
        priority__lte=2,  # P1 and P2 only
    ).select_related("store", "shift_period")

    if not unfilled.exists():
        return 0

    lines = ["【充足不可アラート】以下のP1/P2応援枠が未充足です:\n"]
    for slot in unfilled:
        lines.append(
            f"  - [P{slot.priority}] {slot.store.name} {slot.date}"
        )

    message = "\n".join(lines)
    # Note: SV zoom account would be configured per-deployment
    # For now, log the alert
    logger.warning("Unfilled P1/P2 slots alert:\n%s", message)
    return unfilled.count()
