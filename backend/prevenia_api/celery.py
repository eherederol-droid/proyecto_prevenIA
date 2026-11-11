"""PrevenIA Celery app"""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prevenia_api.settings')
app = Celery('prevenia')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Scheduled tasks
app.conf.beat_schedule = {
    'weekly-risk-report': {
        'task': 'reports.tasks.weekly_risk_report',
        'schedule': crontab(hour=8, minute=0, day_of_week='monday'),
    },
}
