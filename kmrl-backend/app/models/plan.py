"""
Induction plan and assignment models.

An InductionPlan is one complete overnight scheduling run.
Each run produces:
  - PlanAssignment rows (one per train: state + reason + constraint type)
  - ShuntMove rows (ordered list of shunting operations needed to pull trains)
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, DateTime, Date,
    ForeignKey, Enum as SAEnum, Text, Boolean,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class AssignmentState(str, enum.Enum):
    SERVICE     = "service"
    MAINTENANCE = "maintenance"
    STANDBY     = "standby"
    CLEANING    = "cleaning"
    BREAKDOWN   = "breakdown"


class ConstraintType(str, enum.Enum):
    HARD = "hard"   # legally / operationally cannot be violated
    SOFT = "soft"   # preference; can be overridden with justification


class PlanStatus(str, enum.Enum):
    PENDING    = "pending"
    GENERATING = "generating"
    COMPLETE   = "complete"
    FAILED     = "failed"


class InductionPlan(Base):
    """
    One planning run — e.g. "plan_2026_08_13" generated at 22:00 the night before.
    """
    __tablename__ = "induction_plans"

    plan_id      = Column(String(40), primary_key=True)   # e.g. "plan_2026_08_13"
    plan_date    = Column(Date, nullable=False)             # date of service this plan covers
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    status       = Column(SAEnum(PlanStatus, native_enum=False), default=PlanStatus.PENDING, nullable=False)

    # Celery task ID for async generation — allows polling
    celery_task_id = Column(String(60), nullable=True)

    # Whether this is a what-if override plan (not the authoritative plan)
    is_what_if = Column(Boolean, default=False, nullable=False)

    # Solver metadata
    solver_duration_ms = Column(Integer, nullable=True)
    solver_status      = Column(String(30), nullable=True)   # e.g. "OPTIMAL", "FEASIBLE"

    assignments = relationship("PlanAssignment", back_populates="plan", cascade="all, delete-orphan")
    shunts      = relationship("ShuntMove",      back_populates="plan", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<InductionPlan {self.plan_id} [{self.status.value}]>"


class PlanAssignment(Base):
    """
    One row per train per plan — what state the train is assigned and why.
    This is the core output consumed by Track C (dashboard) and Track A (solver feedback).
    """
    __tablename__ = "plan_assignments"

    id      = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(String(40), ForeignKey("induction_plans.plan_id"), nullable=False, index=True)
    train_id = Column(String(10), ForeignKey("trains.train_id"), nullable=False, index=True)

    state           = Column(SAEnum(AssignmentState, native_enum=False, length=20), nullable=False)
    reason          = Column(Text, nullable=False)
    constraint_type = Column(SAEnum(ConstraintType, native_enum=False, length=10), nullable=False)

    # Which constraints were evaluated (comma-separated keys, used by explainability)
    constraints_considered = Column(String(200), nullable=True)

    plan  = relationship("InductionPlan", back_populates="assignments")
    train = relationship("Train")

    def __repr__(self) -> str:
        return f"<PlanAssignment plan={self.plan_id} train={self.train_id} → {self.state.value}>"


class ShuntMove(Base):
    """
    One shunt operation required to pull a train from its bay.
    Ordered by `sequence` — execute in ascending sequence order.

    SIMULATED yard layout.
    """
    __tablename__ = "shunt_moves"

    id       = Column(Integer, primary_key=True, autoincrement=True)
    plan_id  = Column(String(40), ForeignKey("induction_plans.plan_id"), nullable=False, index=True)

    # Which train is being moved in this shunt step
    train_id = Column(String(10), ForeignKey("trains.train_id"), nullable=False)

    from_bay  = Column(String(10), nullable=False)
    to_bay    = Column(String(10), nullable=False)

    # Execution order within the plan
    sequence  = Column(Integer, nullable=False, default=0)

    plan  = relationship("InductionPlan", back_populates="shunts")
    train = relationship("Train")

    def __repr__(self) -> str:
        return f"<ShuntMove {self.train_id}: {self.from_bay} → {self.to_bay} (seq={self.sequence})>"
