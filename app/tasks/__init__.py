import logging
from celery import Task

logger = logging.getLogger("laura.tasks")


class LoggedTask(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error("task_failed", extra={
            "task_id": task_id,
            "task_name": self.name,
            "task_args": args[:2] if args else None,
            "error": str(exc)[:500],
        })

    def on_success(self, retval, task_id, args, kwargs):
        logger.info("task_success", extra={
            "task_id": task_id,
            "task_name": self.name,
        })

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning("task_retry", extra={
            "task_id": task_id,
            "task_name": self.name,
            "attempt": self.request.retries,
            "error": str(exc)[:500],
        })
