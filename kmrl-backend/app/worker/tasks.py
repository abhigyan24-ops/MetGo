"""
Celery tasks for async plan generation.

Currently implements:
  - generate_plan_async: Full plan generation (nightly scheduled run)
  - generate_what_if_plan: What-if scenario re-solve (dashboard interactive feature)

These tasks call into Track A's CP-SAT solver (Google OR-Tools — free/open-source).
"""

import logging
from datetime import date, datetime
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session

from app.worker.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.plan import InductionPlan, PlanAssignment, ShuntMove, PlanStatus, AssignmentState, ConstraintType
from app.models.train import Train
from app.models.yard import YardBay
from ortools.sat.python import cp_model
import time

import sys
from pathlib import Path

# LOCKWOOD sits as a sibling folder to this repo (Desktop\LOCKWOOD next to
# Desktop\kmrl-backend). Without this, every "from src..." import below
# fails with ModuleNotFoundError, since nothing else on this machine adds
# LOCKWOOD to the Python path.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "LOCKWOOD"))

from src.constants import PLANNING_DATE
from src.solver.model_builder import build_model
from src.solver.objective import build_total_objective
from src.solver.plan_formatter import format_plan
from src.solver.validation import validate_plan
from src.solver.states import SERVICE
from src.solver.overrides import Override, apply_overrides
from src.adapters.db_adapter import adapt_train, adapt_yard_layout


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: call solver — wired to Track A's real CP-SAT solver (lockwood)
# ---------------------------------------------------------------------------

def call_solver(
    trains: list,
    yard_bays: list,
    override: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Calls the real lockwood CP-SAT solver to generate a plan.

    Args:
        trains: real SQLAlchemy Train query results (app.models.train.Train)
        yard_bays: real SQLAlchemy YardBay query results (app.models.yard.YardBay)
        override: optional what-if override, e.g. {"train_id": "T09", "status": "breakdown"}

    Returns: same shape as before (status/solve_time_ms/assignments/shunts) --
    see the module docstring at the top of this file.

    NOTE: shunts is currently always []. Populating real from_bay/to_bay
    shunt routes requires the Neo4j yard graph (app/services/yard_graph.py),
    which lockwood's solver does not decide -- it only decides which STATE
    each train is assigned, not which bay a blocking train moves to. Wiring
    that is separate follow-up work, not silently faked here.

    NOTE: reason/constraint_type below are minimal placeholders sufficient
    to satisfy the PlanAssignment schema. Replacing them with the real
    explainability engine (app/services/explainability.py, already built)
    is Part 4's job, not this one.
    """
    lockwood_trains = [adapt_train(t) for t in trains]
    yard_layout = adapt_yard_layout(yard_bays)

    model, assign_vars = build_model(lockwood_trains, yard_layout)

    # Part 5b: real override mechanism (Part 5a), replacing the Part 3c
    # ad-hoc hack. call_solver()'s own signature is unchanged (still a
    # single optional override dict) -- internally translated into the
    # list Override/apply_overrides() expects.
    overrides = []
    override_forced_id = None
    if override and override.get("train_id"):
        override_forced_id = override["train_id"]
        overrides = [Override(override["train_id"], override["status"])]
    override_reasons = apply_overrides(model, assign_vars, overrides)

    objective = build_total_objective(lockwood_trains, assign_vars, yard_layout)
    model.Minimize(objective)

    solver = cp_model.CpSolver()
    start = time.monotonic()
    status = solver.Solve(model)
    solve_time_ms = int((time.monotonic() - start) * 1000)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        logger.error(f"Solver returned {solver.StatusName(status)} -- no plan produced")
        return {
            "status": "INFEASIBLE",
            "solve_time_ms": solve_time_ms,
            "assignments": [],
            "shunts": [],
        }

    plan = format_plan(solver, assign_vars, lockwood_trains)
    violations = validate_plan(plan, lockwood_trains, yard_layout)
    if violations:
        # A hard-constraint violation in a solved plan is a real bug,
        # not a recoverable condition -- fail loudly rather than
        # silently ship an unsafe plan.
        raise RuntimeError(
            f"Solver produced a plan with hard-constraint violations: {violations}"
        )

    trains_by_id = {t.train_id: t for t in lockwood_trains}
    assignments = []
    for row in plan:
        train_id, state = row["train_id"], row["assigned_state"]
        lw_train = trains_by_id[train_id]
        is_override_forced = train_id == override_forced_id

        if is_override_forced:
            reason, constraint_type = override_reasons[train_id], "hard"
        elif lw_train.fitness_cert_expiry < PLANNING_DATE:
            reason, constraint_type = "Fitness certificate expired", "hard"
        elif lw_train.job_card_severity == "critical":
            reason, constraint_type = "Open critical job card", "hard"
        else:
            reason = {
                "service": "Selected for service; no blocking constraints",
                "maintenance": "Routed to maintenance",
                "cleaning": "Assigned for cleaning",
                "standby": "Kept in standby",
            }[state]
            constraint_type = "soft"

        assignments.append({
            "train_id": train_id,
            "state": state,
            "reason": reason,
            "constraint_type": constraint_type,
        })

    return {
        "status": solver.StatusName(status),
        "solve_time_ms": solve_time_ms,
        "assignments": assignments,
        "shunts": [],
    }


# ---------------------------------------------------------------------------
# Task: Generate full plan (nightly scheduled run)
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="app.worker.tasks.generate_plan_async")
def generate_plan_async(self, plan_date_str: str) -> Dict[str, Any]:
    """
    Generate a complete induction plan for the specified service date.
    
    This is the nightly scheduled run — called at ~22:00 the night before.
    
    Args:
        plan_date_str: ISO date string (e.g. "2026-08-14")
    
    Returns:
        {
          "plan_id": "plan_2026_08_14",
          "status": "complete",
          "assignments_count": 25,
          "shunts_count": 4,
          "solve_time_ms": 2345,
        }
    """
    
    logger.info(f"Starting plan generation for {plan_date_str}")
    
    # Update task state to STARTED
    self.update_state(state="STARTED", meta={"progress": "Loading fleet data..."})
    
    db = SessionLocal()
    try:
        plan_date = date.fromisoformat(plan_date_str)
        # Part 5c-2 fix: plan_id must be unique per *call*, not per
        # calendar day -- the previous f"plan_{date}" scheme collided on
        # the second /plan/generate call in the same day (Postgres
        # UniqueViolation on induction_plans_pkey). plan_date remains its
        # own column for date-based queries; nothing else in the codebase
        # parses plan_id's string shape to recover a date.
        run_suffix = datetime.utcnow().strftime("%H%M%S")
        plan_id = f"plan_{plan_date_str.replace('-', '_')}_{run_suffix}"
        
        # Create plan record
        plan = InductionPlan(
            plan_id=plan_id,
            plan_date=plan_date,
            generated_at=datetime.utcnow(),
            status=PlanStatus.GENERATING,
            celery_task_id=self.request.id,
            is_what_if=False,
        )
        db.add(plan)
        db.commit()
        
        # Load all trains with constraint data
        self.update_state(state="STARTED", meta={"progress": "Loading train constraint data..."})
        trains = db.query(Train).all()
        yard_bays = db.query(YardBay).all()

        # Call solver
        self.update_state(state="STARTED", meta={"progress": "Running CP-SAT solver..."})
        solver_result = call_solver(trains, yard_bays, override=None)
        
        # Store results
        self.update_state(state="STARTED", meta={"progress": "Storing plan assignments..."})
        
        plan.solver_status = solver_result["status"]
        plan.solver_duration_ms = solver_result["solve_time_ms"]
        
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
        
        logger.info(f"Plan {plan_id} generated successfully")
        
        return {
            "plan_id": plan_id,
            "status": "complete",
            "assignments_count": len(solver_result["assignments"]),
            "shunts_count": len(solver_result["shunts"]),
            "solve_time_ms": solver_result["solve_time_ms"],
        }
    
    except Exception as exc:
        logger.exception(f"Plan generation failed: {exc}")
        
        if 'plan' in locals():
            plan.status = PlanStatus.FAILED
            db.commit()
        
        # Re-raise so Celery marks the task as FAILURE
        raise
    
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Task: Generate what-if scenario (dashboard interactive feature)
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="app.worker.tasks.generate_what_if_plan")
def generate_what_if_plan(
    self,
    base_plan_id: str,
    override: Dict[str, str],
) -> Dict[str, Any]:
    """
    Generate a what-if scenario plan with a manual override.
    
    This runs interactively from the dashboard when the user asks
    "What if train 9 breaks down?"
    
    Args:
        base_plan_id: The plan to base the what-if on
        override: {"train_id": "T09", "status": "breakdown"}
    
    Returns:
        Same shape as generate_plan_async, but with is_what_if=True
    """
    
    logger.info(f"Starting what-if plan: override={override}")
    
    self.update_state(state="STARTED", meta={"progress": "Loading base plan..."})
    
    db = SessionLocal()
    try:
        # Create what-if plan record
        whatif_id = f"whatif_{override['train_id']}_{override['status']}_{int(datetime.utcnow().timestamp())}"
        
        plan = InductionPlan(
            plan_id=whatif_id,
            plan_date=date.today(),
            generated_at=datetime.utcnow(),
            status=PlanStatus.GENERATING,
            celery_task_id=self.request.id,
            is_what_if=True,
        )
        db.add(plan)
        db.commit()
        
        # Load fleet data
        self.update_state(state="STARTED", meta={"progress": "Loading fleet data..."})
        trains = db.query(Train).all()
        yard_bays = db.query(YardBay).all()

        # Call solver with override
        self.update_state(state="STARTED", meta={"progress": "Running CP-SAT solver with override..."})
        solver_result = call_solver(trains, yard_bays, override=override)
        
        # Store results
        self.update_state(state="STARTED", meta={"progress": "Storing what-if plan..."})
        
        plan.solver_status = solver_result["status"]
        plan.solver_duration_ms = solver_result["solve_time_ms"]
        
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
        
        logger.info(f"What-if plan {whatif_id} generated successfully")
        
        return {
            "plan_id": whatif_id,
            "status": "complete",
            "override": override,
            "assignments_count": len(solver_result["assignments"]),
            "shunts_count": len(solver_result["shunts"]),
            "solve_time_ms": solver_result["solve_time_ms"],
        }
    
    except Exception as exc:
        logger.exception(f"What-if plan generation failed: {exc}")
        
        if 'plan' in locals():
            plan.status = PlanStatus.FAILED
            db.commit()
        
        raise
    
    finally:
        db.close()
