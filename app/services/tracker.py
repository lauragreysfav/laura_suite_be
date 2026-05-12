import logging
from app.celery_app import celery_app

logger = logging.getLogger("laura.services.tracker")


def start_scheduler():
    logger.info("celery_beat_managed_externally")
    pass


def stop_scheduler():
    logger.info("celery_beat_stopped_externally")
    pass
