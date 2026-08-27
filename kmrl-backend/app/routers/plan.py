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
from app.config import get_settings
from app.worker.tasks import generate_plan_async, generate_what_if_plan, call_solver
from app.models.plan import InductionPlan, PlanAssignment, ShuntMove, PlanStatus, AssignmentState, ConstraintType
from app.models.train import Train
from app.models.yard import YardBay
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
# ---------------------------------------------------------------------------
# POST /plan/generate ?" main planning endpoint
# ---------------------------------------------------------------------------

@router.post("/generate", response_model=PlanOut, summary="Generate overnight induction plan")
def generate_plan(db: Session = Depends(get_db)):
    """
    Generate a complete induction plan for the next service day.

    Supports both:
    1. Synchronous in-process execution (DEPLOYMENT_MODE=render/sync)
    2. Distributed Celery task queue (DEPLOYMENT_MODE=docker/celery)
    """
    plan_date_str = date.today().isoformat()
    settings = get_settings()

    # Synchronous alternate path for Render / card-free / standalone deployment
    if settings.deployment_mode.lower() in ("render", "sync", "standalone"):
        trains = db.query(Train).all()
        yard_bays = db.query(YardBay).all()
        run_suffix = datetime.utcnow().strftime("%H%M%S")
        plan_id = f"plan_{plan_date_str.replace('-', '_')}_{run_suffix}"

        plan = InductionPlan(
            plan_id=plan_id,
            plan_date=date.today(),
            generated_at=datetime.utcnow(),
            status=PlanStatus.GENERATING,
            celery_task_id="sync-task",
            is_what_if=False,
        )
        db.add(plan)
        db.commit()

        solver_result = call_solver(trains, yard_bays, override=None)
        plan.solver_status = solver_result["status"]
        plan.solver_duration_ms = solver_result["solve_time_ms"]

        if plan.solver_status not in ("OPTIMAL", "FEASIBLE"):
            plan.status = PlanStatus.FAILED
            db.commit()
            raise HTTPException(status_code=409, detail=f"Solver could not find a valid plan (status: {plan.solver_status}).")

        for assignment_data in solver_result["assignments"]:
            assignment = PlanAssignment(
                plan_id=plan_id,
                train_id=assignment_data["train_id"],
                state=AssignmentState(assignment_data["state"]),
                reason=assignment_data["reason"],
                constraint_type=ConstraintType(assignment_data["constraint_type"]),
                constraints_considered="fitness_cert,job_cards,cleaning_schedule,branding_contract,yard_position",
            )
            db.add(assignment)

        for shunt_data in solver_result["shunts"]:
            shunt = ShuntMove(
                plan_id=plan_id,
                train_id=shunt_data["train_id"],
                from_bay=shunt_data["from_bay"],
                to_bay=shunt_data["to_bay"],
                sequence=shunt_data["sequence"],
            )
            db.add(shunt)

        plan.status = PlanStatus.COMPLETE
        db.commit()
        return _plan_to_response(plan)

    # Celery / Redis distributed queue path
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

    settings = get_settings()

    # Synchronous alternate path for Render / card-free deployment
    if settings.deployment_mode.lower() in ("render", "sync", "standalone"):
        trains = db.query(Train).all()
        yard_bays = db.query(YardBay).all()
        whatif_id = f"whatif_{override['train_id']}_{override['status']}_{int(datetime.utcnow().timestamp())}"

        plan = InductionPlan(
            plan_id=whatif_id,
            plan_date=date.today(),
            generated_at=datetime.utcnow(),
            status=PlanStatus.GENERATING,
            celery_task_id="sync-task",
            is_what_if=True,
        )
        db.add(plan)
        db.commit()

        solver_result = call_solver(trains, yard_bays, override=override)
        plan.solver_status = solver_result["status"]
        plan.solver_duration_ms = solver_result["solve_time_ms"]

        if plan.solver_status not in ("OPTIMAL", "FEASIBLE"):
            plan.status = PlanStatus.FAILED
            db.commit()
            raise HTTPException(
                status_code=409,
                detail=f"This override combination has no valid plan (solver status: {plan.solver_status}).",
            )

        for assignment_data in solver_result["assignments"]:
            assignment = PlanAssignment(
                plan_id=whatif_id,
                train_id=assignment_data["train_id"],
                state=AssignmentState(assignment_data["state"]),
                reason=assignment_data["reason"],
                constraint_type=ConstraintType(assignment_data["constraint_type"]),
                constraints_considered="fitness_cert,job_cards,cleaning_schedule,branding_contract,yard_position",
            )
            db.add(assignment)

        for shunt_data in solver_result["shunts"]:
            shunt = ShuntMove(
                plan_id=whatif_id,
                train_id=shunt_data["train_id"],
                from_bay=shunt_data["from_bay"],
                to_bay=shunt_data["to_bay"],
                sequence=shunt_data["sequence"],
            )
            db.add(shunt)

        plan.status = PlanStatus.COMPLETE
        db.commit()
        return _plan_to_response(plan)

    # Celery / Redis distributed queue path
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
