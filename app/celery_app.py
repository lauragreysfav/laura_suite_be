from celery import Celery
from app.config import settings

celery_app = Celery(
    "laura",
    broker=settings.celery_broker_url or "redis://redis:6379/0",
    backend=settings.celery_result_backend or "redis://redis:6379/0",
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=120,
    task_time_limit=180,
    beat_schedule={
        "check-all-trackers-every-hour": {
            "task": "app.tasks.tracker_tasks.check_all_trackers",
            "schedule": 3600.0,
            "args": (None,),
        },
        "prime-stashdb-cache-every-6h": {
            "task": "app.tasks.library_search_tasks.prime_suggest_cache",
            "schedule": 21600.0,
        },
    },
)


import app.tasks.search_tasks
import app.tasks.tracker_tasks
import app.tasks.email_tasks
import app.tasks.library_search_tasks
