"""
Async task status endpoints — poll Celery task results.
"""

from fastapi import APIRouter, HTTPException
from celery.result import AsyncResult

from app.worker.celery_app import celery_app

router = APIRouter()


@router.get("/{task_id}", summary="Poll async task result")
def get_task_result(task_id: str):
    """
    Poll the status of an async Celery task (e.g. a what-if re-solve).

    States: PENDING → STARTED → SUCCESS | FAILURE
    """
    result = AsyncResult(task_id, app=celery_app)

    if result.state == "PENDING":
        return {"task_id": task_id, "status": "pending", "result": None}
    elif result.state == "STARTED":
        return {"task_id": task_id, "status": "running", "result": None}
    elif result.state == "SUCCESS":
        return {"task_id": task_id, "status": "success", "result": result.result}
    elif result.state == "FAILURE":
        raise HTTPException(
            status_code=500,
            detail={"task_id": task_id, "status": "failed", "error": str(result.result)},
        )
    else:
        return {"task_id": task_id, "status": result.state, "result": None}
