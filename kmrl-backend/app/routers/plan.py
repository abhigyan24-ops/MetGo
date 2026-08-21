"""
Plan generation endpoints ?" the core scheduling API.

This router implements the three locked contract endpoints:
  POST /plan/generate
  POST /plan/what-if
  GET  /plan/{plan_id}/explain/{train_id}
"""

from datetime import datetime, date
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.session import get_db

from celery.exceptions import TimeoutError as CeleryTimeoutError
from app.worker.tasks import generate_plan_async, generate_what_if_plan
from app.models.plan import InductionPlan, PlanAssignment, ShuntMove, PlanStatus
from app.services.explainability import get_explainability_engine
from src.solver.overrides import VALID_OVERRIDE_TYPES

router = APIRouter()

class AssignmentOut(BaseModel):
    train_id: str
    state: str
    reason: str
    constraint_type: str

class ShuntOut(BaseModel):
    train_id: str
    from_bay: str
    to_bay: str


class PlanOut(BaseModel):
    """Complete induction plan output ?" the locked contract shape."""
    plan_id: str
    status: str
    generated_at: str  # ISO 8601 timestamp
    assignments: List[AssignmentOut]
    shunts_required: List[ShuntOut]


class WhatIfRequest(BaseModel):
    """What-if override: force a train into a specific status before re-solving."""
    override: Dict[str, str] = Field(
        ...,
        examples=[{"train_id": "T09", "status": "breakdown"}]
    )


class ExplainOut(BaseModel):
    """Explainability response for a single train in a plan."""
    train_id: str
    assigned_state: str
    explanation: str
    constraints_considered: List[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CELERY_TASK_TIMEOUT_SECONDS = 60

def _plan_to_response(plan: InductionPlan) -> PlanOut:
    """Builds the locked-contract PlanOut response from the durable
    DB state of a completed plan -- the single source of truth after
    any Celery task finishes, rather than trusting the task's own
    (summary-only) return value."""
    return PlanOut(
        plan_id=plan.plan_id,
        status=plan.solver_status or "FEASIBLE",
        generated_at=plan.generated_at.isoformat() if plan.generated_at else "",
        assignments=[
            AssignmentOut(
                train_id=a.train_id,
                state=a.state.value,
                reason=a.reason,
                constraint_type=a.constraint_type.value,
            )
            for a in plan.assignments
        ],
        shunts_required=[
            ShuntOut(train_id=s.train_id, from_bay=s.from_bay, to_bay=s.to_bay)
            for s in plan.shunts
        ],
    )

# ---------------------------------------------------------------------------
# POST /plan/generate ?" main planning endpoint
# ---------------------------------------------------------------------------

@router.post("/generate", response_model=PlanOut, summary="Generate overnight induction plan")
def generate_plan(db: Session = Depends(get_db)):
    """
    Generate a complete induction plan for the next service day.

    Dispatches the real Celery task (app.worker.tasks.generate_plan_async)
    and blocks for the result -- the frontend awaits this endpoint
    directly and does not poll GET /tasks/{task_id} (confirmed by
    reading kmrl-frontend/src/App.jsx directly).
    """
    plan_date_str = date.today().isoformat()

    try:
        result = generate_plan_async.delay(plan_date_str).get(timeout=CELERY_TASK_TIMEOUT_SECONDS)
    except CeleryTimeoutError:
        raise HTTPException(
            status_code=503,
            detail="Plan generation did not complete in time -- check that a Celery worker is running.",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Plan generation failed: {exc}")

    if result["status"] != "complete":
        raise HTTPException(status_code=409, detail=f"Plan generation did not complete successfully: {result}")

    plan = db.query(InductionPlan).filter(InductionPlan.plan_id == result["plan_id"]).first()
    if plan is None:
        raise HTTPException(status_code=500, detail="Plan was reported complete but could not be found in the database.")
    if plan.solver_status not in ("OPTIMAL", "FEASIBLE"):
        raise HTTPException(status_code=409, detail=f"Solver could not find a valid plan (status: {plan.solver_status}).")

    return _plan_to_response(plan)

# ---------------------------------------------------------------------------
# POST /plan/what-if ?" what-if scenario re-solver
# ---------------------------------------------------------------------------

@router.post("/what-if", response_model=PlanOut, summary="Generate what-if scenario with override")
def what_if(request: WhatIfRequest, db: Session = Depends(get_db)):
    """
    Re-run the solver with a manual override (e.g. simulate a breakdown).

    Same blocking-Celery-call pattern as /generate -- see that
    endpoint's docstring. base_plan_id is resolved here to the most
    recent COMPLETE, non-what-if plan for record-keeping and to
    validate a baseline exists; generate_what_if_plan() itself does
    not read anything from that plan (confirmed by reading
    app/worker/tasks.py directly -- it always re-fetches fresh fleet
    data regardless of base_plan_id).
    """
    override = request.override
    train_id = override.get("train_id")
    status_value = override.get("status")

    if not train_id or not status_value:
        raise HTTPException(status_code=422, detail="override must include both train_id and status.")
    if status_value not in VALID_OVERRIDE_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown override status {status_value!r}; must be one of {sorted(VALID_OVERRIDE_TYPES)}.",
        )

    base_plan = (
        db.query(InductionPlan)
        .filter(InductionPlan.status == PlanStatus.COMPLETE, InductionPlan.is_what_if == False)
        .order_by(InductionPlan.generated_at.desc())
        .first()
    )
    if base_plan is None:
        raise HTTPException(status_code=404, detail="No completed plan exists yet -- generate a plan first.")

    try:
        result = generate_what_if_plan.delay(base_plan.plan_id, override).get(timeout=CELERY_TASK_TIMEOUT_SECONDS)
    except CeleryTimeoutError:
        raise HTTPException(
            status_code=503,
            detail="What-if re-plan did not complete in time -- check that a Celery worker is running.",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"What-if re-plan failed: {exc}")

    if result["status"] != "complete":
        raise HTTPException(status_code=409, detail=f"What-if re-plan did not complete successfully: {result}")

    plan = db.query(InductionPlan).filter(InductionPlan.plan_id == result["plan_id"]).first()
    if plan is None:
        raise HTTPException(status_code=500, detail="What-if plan was reported complete but could not be found in the database.")
    if plan.solver_status not in ("OPTIMAL", "FEASIBLE"):
        raise HTTPException(
            status_code=409,
            detail=f"This override combination has no valid plan (solver status: {plan.solver_status}).",
        )

    return _plan_to_response(plan)

# ---------------------------------------------------------------------------
# GET /plan/{plan_id}/explain/{train_id} ?" explainability
# ---------------------------------------------------------------------------

@router.get("/{plan_id}/explain/{train_id}", summary="Explain why a train got its assignment")
def explain_assignment(plan_id: str, train_id: str, db: Session = Depends(get_db)):
    """
    Return a real explanation of why a train was assigned its state,
    via the actual ExplainabilityEngine (Part 4c) -- not mock data.
    """
    assignment = (
        db.query(PlanAssignment)
        .filter(PlanAssignment.plan_id == plan_id, PlanAssignment.train_id == train_id)
        .first()
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail=f"No assignment found for train {train_id} in plan {plan_id}.")

    engine = get_explainability_engine(db)
    return engine.explain_assignment(train_id, assignment)
