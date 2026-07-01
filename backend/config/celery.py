"""
KAVAN v6.0 — Celery Application Configuration
============================================================
Celery is used for background task processing.
Tasks are auto-discovered from each app's tasks.py module.

Usage:
    Start worker:  celery -A config.celery worker --loglevel=info
    Start beat:    celery -A config.celery beat   --loglevel=info
    Monitor:       celery -A config.celery flower
"""

import os

from celery import Celery
from celery.schedules import crontab

# Set default Django settings module for Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

# Create the Celery application
app = Celery("kavan")

# Load configuration from Django settings (CELERY_ prefix)
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# ============================================================
# BEAT SCHEDULE (Periodic Tasks)
# ============================================================

app.conf.beat_schedule = {
    # Layer 1: Health check logging (every 5 minutes)
    "log-health-status": {
        "task": "apps.health.tasks.log_health_status",
        "schedule": crontab(minute="*/5"),
        "options": {"expires": 60},
    },
    # Layer 6: Deployment health checks (every 5 minutes)
    "health-check-all-deployments": {
        "task": "deployments.health_check_all",
        "schedule": crontab(minute="*/5"),
        "options": {"expires": 120},
    },
}

app.conf.timezone = "UTC"


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery connectivity."""
    print(f"Request: {self.request!r}")
