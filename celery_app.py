# celery_app.py
from celery import Celery
from celery.schedules import crontab
import os
import logging

from config import config

logger = logging.getLogger(__name__)

REDIS_URL = config.get_celery_broker()

celery_app = Celery(
    "astra",
    broker=REDIS_URL,
    backend=config.get_celery_backend(),
    include=["tasks"]  # ✅ This imports all tasks
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    task_track_started=config.CELERY_TASK_TRACK_STARTED,
    task_time_limit=config.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=config.CELERY_TASK_SOFT_TIME_LIMIT,
    
    worker_max_tasks_per_child=config.CELERY_WORKER_MAX_TASKS_PER_CHILD,
    worker_prefetch_multiplier=1,
    
    # ✅ All tasks now registered
    beat_schedule={
        'collect-fx-rates': {
            'task': 'collect_fx_rates',
            'schedule': crontab(minute=0),
            'options': {'expires': 1800}
        },
        'check-agent-rules': {
            'task': 'check_agent_rules',
            'schedule': crontab(minute=5),
            'options': {'expires': 1800}
        },
        'train-prediction-models': {
            'task': 'train_prediction_models',
            'schedule': crontab(hour=2, minute=0),
            'options': {'expires': 7200}
        },
    }
)


@celery_app.task(name="health_check")
def health_check():
    return {"status": "healthy", "timestamp": "now"}