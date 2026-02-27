"""Audit logging utility."""

from .models import AuditLog


def log_action(user, action: str, table_name: str = "", record_id: int = None,
               before_data=None, after_data=None):
    """監査ログを記録"""
    AuditLog.objects.create(
        user=user,
        action=action,
        table_name=table_name,
        record_id=record_id,
        before_data=before_data,
        after_data=after_data,
    )
