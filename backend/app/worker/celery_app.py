import os
from celery import Celery

# Use env vars or defaults
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "arcore_worker",
    broker=redis_url,
    backend=redis_url,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_queue="default",
    task_routes={
        "app.worker.tasks.run_push_sync": {"queue": "sync_queue"},
        "app.worker.tasks.run_ingress_sync": {"queue": "sync_queue"},
        "app.worker.tasks.run_scheduled_sync": {"queue": "sync_queue"},
        "app.worker.tasks.reconcile_drift_metrics": {"queue": "default"},
        "app.worker.tasks.reconcile_single_sync": {"queue": "default"},
    },
    # Celery Beat Configuration
    beat_scheduler="celery.beat:PersistentScheduler",
    beat_schedule_filename="/tmp/celerybeat-schedule",
    beat_schedule={
        "dispatch-sync-schedules": {
            "task": "app.worker.tasks.dispatch_sync_schedules",
            "schedule": 15.0,
            "options": {"queue": "default"},
        },
        "reconcile-drift-metrics-every-30-minutes": {
            "task": "app.worker.tasks.reconcile_drift_metrics",
            "schedule": 1800.0,  # 30 minutes in seconds
            "options": {"queue": "default"}
        },
    },
)
