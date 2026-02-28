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
    "scrape-musubi-prescriptions-daily": {
        "task": "apps.analytics.tasks.scrape_musubi_prescriptions",
        "schedule": crontab(hour=6, minute=0),  # Every day at 6:00 AM JST
    },
    "generate-prescription-forecasts-weekly": {
        "task": "apps.analytics.tasks.generate_prescription_forecasts",
        "schedule": crontab(hour=7, minute=0, day_of_week=1),  # Monday 7:00 AM JST
    },
    "check-evaluator-bias-daily": {
        "task": "apps.hr_system.tasks.check_all_evaluator_bias",
        "schedule": crontab(hour=11, minute=0),  # Every day at 11:00 AM JST
    },
    "fetch-idwr-weekly": {
        "task": "apps.analytics.tasks.fetch_idwr_weekly",
        "schedule": crontab(hour=5, minute=0, day_of_week=2),  # Tuesday 5:00 AM JST
    },
    "fetch-weather-daily": {
        "task": "apps.analytics.tasks.fetch_weather_daily",
        "schedule": crontab(hour=5, minute=30),  # Every day at 5:30 AM JST
    },
}
