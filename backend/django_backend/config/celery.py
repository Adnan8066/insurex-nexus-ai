"""Celery application for background work: claim scoring, policy expiry, renewal reminders.

Start a worker and the scheduler (Redis must be running and CELERY_BROKER_URL set):

    celery -A config worker -l info
    celery -A config beat -l info

Tests and environments without a broker run tasks in-process (see settings.py,
CELERY_TASK_ALWAYS_EAGER). Without Celery installed, the task functions still run
when called directly.
"""
import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('insurex')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
