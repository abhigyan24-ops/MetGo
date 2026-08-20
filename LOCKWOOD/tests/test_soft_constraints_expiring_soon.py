"""
Isolated tests for Part 3b's new fitness-cert-expiring-soon soft
constraint, following the same bare-model isolation pattern
established in Part 2a/2b/3a.
"""

from datetime import date, timedelta

from ortools.sat.python import cp_model

from src.constants import PLANNING_DATE
from src.models import Train
from src.solver.soft_constraint_config import (
    EXPIRING_SOON_DAYS,
    EXPIRING_SOON_PENALTY_WEIGHT,
)
from src.solver.soft_constraints import build_expiring_soon_penalty
from src.solver.states import ALL_STATES, MAINTENANCE, SERVICE


def make_train(train_id, fitness_cert_expiry):
    return Train(
        train_id=train_id,
        fitness_cert_expiry=fitness_cert_expiry,
        job_card_severity=None,
        last_cleaned=PLANNING_DATE,
        branding_hours_this_month=60,
        branding_target_hours=60,
        current_bay="X1",
        mileage_total=100000,
    )


def _bare_model(trains):
    model = cp_model.CpModel()
    assign_vars = {}
    for train in trains:
        for state in ALL_STATES:
            assign_vars[(train.train_id, state)] = model.NewBoolVar(
                f"{train.train_id}_{state}"
            )
    for train in trains:
        model.AddExactlyOne(
            [assign_vars[(train.train_id, s)] for s in ALL_STATES]
        )
    return model, assign_vars


def test_penalty_positive_when_expiring_soon_and_in_service():
    train = make_train("X1", PLANNING_DATE + timedelta(days=EXPIRING_SOON_DAYS))
    model, assign_vars = _bare_model([train])
    model.Add(assign_vars[("X1", SERVICE)] == 1)
    penalty = build_expiring_soon_penalty([train], assign_vars)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(penalty) == EXPIRING_SOON_PENALTY_WEIGHT


def test_penalty_zero_when_expiring_soon_but_in_maintenance():
    train = make_train("X1", PLANNING_DATE + timedelta(days=1))
    model, assign_vars = _bare_model([train])
    model.Add(assign_vars[("X1", MAINTENANCE)] == 1)
    penalty = build_expiring_soon_penalty([train], assign_vars)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(penalty) == 0


def test_penalty_zero_when_expiry_is_far_away():
    train = make_train("X1", PLANNING_DATE + timedelta(days=EXPIRING_SOON_DAYS + 1))
    model, assign_vars = _bare_model([train])
    model.Add(assign_vars[("X1", SERVICE)] == 1)
    penalty = build_expiring_soon_penalty([train], assign_vars)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(penalty) == 0


def test_boundary_exactly_on_planning_date_counts_as_expiring_soon():
    """A cert expiring ON PLANNING_DATE itself (0 days out) is not yet
    expired (the hard constraint only blocks expiry < PLANNING_DATE)
    but is about as soon as "soon" gets."""
    train = make_train("X1", PLANNING_DATE)
    model, assign_vars = _bare_model([train])
    model.Add(assign_vars[("X1", SERVICE)] == 1)
    penalty = build_expiring_soon_penalty([train], assign_vars)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(penalty) == EXPIRING_SOON_PENALTY_WEIGHT


def test_boundary_exactly_at_threshold_still_counts():
    train = make_train("X1", PLANNING_DATE + timedelta(days=EXPIRING_SOON_DAYS))
    model, assign_vars = _bare_model([train])
    model.Add(assign_vars[("X1", SERVICE)] == 1)
    penalty = build_expiring_soon_penalty([train], assign_vars)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(penalty) == EXPIRING_SOON_PENALTY_WEIGHT
