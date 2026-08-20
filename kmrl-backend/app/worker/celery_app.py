"""
Celery app configuration for async task processing.

Redis is used as both the message broker and result backend.
Both Redis and Celery are free and open-source.

Usage:
  Start the worker:
    celery -A app.worker.celery_app worker --loglevel=info --pool=solo

  Monitor tasks:
    celery -A app.worker.celery_app flower  (requires: pip install flower)

Note: On Windows, use --pool=solo instead of the default prefork pool.
"""

from celery import Celery

from app.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# Celery app instance
# ---------------------------------------------------------------------------

celery_app = Celery(
    "kmrl_induction_planner",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.worker.tasks"],  # Auto-discover tasks in tasks.py
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Result expiration (7 days — enough for demo/audit trail)
    result_expires=7 * 24 * 60 * 60,
    
    # Task routing (all tasks go to default queue)
    task_default_queue="celery",
    
    # Worker configuration
    worker_prefetch_multiplier=1,  # Fetch one task at a time (good for long-running tasks)
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (prevent memory leaks)
)

# ---------------------------------------------------------------------------
# Task result inspection helpers
# ---------------------------------------------------------------------------

def get_task_status(task_id: str) -> dict:
    """
    Check the status of a Celery task.
    
    Returns: {
        "task_id": "...",
        "status": "PENDING" | "STARTED" | "SUCCESS" | "FAILURE" | "RETRY",
        "result": ...,  # available when status is SUCCESS
        "error": ...,   # available when status is FAILURE
    }
    """
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id, app=celery_app)
    
    response = {
        "task_id": task_id,
        "status": result.state,
    }
    
    if result.state == "SUCCESS":
        response["result"] = result.result
    elif result.state == "FAILURE":
        response["error"] = str(result.info)
    elif result.state == "STARTED":
        # Some tasks report progress — check result.info
        if result.info:
            response["progress"] = result.info
    
    return response
