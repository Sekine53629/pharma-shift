"""Celery configuration for pharma-shift project."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("pharma_shift")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
