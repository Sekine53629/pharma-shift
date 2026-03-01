from __future__ import annotations

from datetime import date, timedelta

from apps.staff.models import Staff


def get_paid_leave_deadline(staff: Staff) -> date:
    """スタッフの義務有給消化期限を算出"""
    today = date.today()
    deadline_str = staff.paid_leave_deadline  # "09/15" or "02/15"
    month, day = map(int, deadline_str.split("/"))

    deadline = date(today.year, month, day)
    # 期限が過去なら翌年に
    if deadline < today:
        deadline = date(today.year + 1, month, day)

    return deadline


def check_mandatory_paid_leave(staff: Staff) -> dict | None:
    """義務有給5日消化チェック

    Returns alert dict if action needed, None otherwise.
    """
    REQUIRED_DAYS = 5

    if staff.paid_leave_used >= REQUIRED_DAYS:
        return None

    deadline = get_paid_leave_deadline(staff)
    today = date.today()
    remaining_days = (deadline - today).days
    remaining_leave = REQUIRED_DAYS - staff.paid_leave_used

    if remaining_days <= 0:
        return {
            "staff_id": staff.id,
            "staff_name": staff.name,
            "level": "overdue",
            "message": f"義務有給期限超過（残{remaining_leave}日未消化）",
            "deadline": deadline.isoformat(),
            "remaining_leave": remaining_leave,
        }
    elif remaining_days <= 7:
        return {
            "staff_id": staff.id,
            "staff_name": staff.name,
            "level": "urgent",
            "message": f"義務有給期限7日以内（残{remaining_leave}日未消化）",
            "deadline": deadline.isoformat(),
            "remaining_leave": remaining_leave,
        }
    elif remaining_days <= 30:
        return {
            "staff_id": staff.id,
            "staff_name": staff.name,
            "level": "warning",
            "message": f"義務有給期限30日以内（残{remaining_leave}日未消化）",
            "deadline": deadline.isoformat(),
            "remaining_leave": remaining_leave,
        }

    return None


def get_all_paid_leave_alerts() -> list[dict]:
    """全スタッフの義務有給アラートを取得"""
    alerts = []
    for staff in Staff.objects.filter(is_active=True):
        alert = check_mandatory_paid_leave(staff)
        if alert:
            alerts.append(alert)
    return alerts
