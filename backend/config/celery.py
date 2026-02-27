"""Celery configuration for pharma-shift project."""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("pharma_shift")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "check-paid-leave-alerts-daily": {
        "task": "apps.leave.tasks.check_paid_leave_alerts",
        "schedule": crontab(hour=8, minute=0),  # Every day at 8:00 AM JST
    },
    "check-leave-request-deadline-daily": {
        "task": "apps.leave.tasks.check_leave_request_deadline",
        "schedule": crontab(hour=9, minute=0),  # Every day at 9:00 AM JST
    },
    "alert-unfilled-slots-daily": {
        "task": "apps.assignments.tasks.alert_unfilled_slots",
        "schedule": crontab(hour=10, minute=0),  # Every day at 10:00 AM JST
    },
}
