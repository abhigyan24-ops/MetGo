"""
Tests for Part 2a's cleaning and branding soft-constraint penalty
builders. These use a minimal "bare" model (decision variables and
the exactly-one-state constraint only) deliberately WITHOUT Part 1's
hard constraints, so each penalty function's arithmetic can be
verified in isolation.
"""

from datetime import date, timedelta

from ortools.sat.python import cp_model

from src.constants import PLANNING_DATE
from src.models import Train
from src.solver.soft_constraint_config import (
    BRANDING_PENALTY_WEIGHT,
    CLEANING_PENALTY_WEIGHT,
)
from src.solver.soft_constraints import build_branding_penalty, build_cleaning_penalty
from src.solver.states import ALL_STATES, CLEANING, SERVICE, STANDBY


def make_train(
    train_id,
    fitness_cert_expiry=None,
    job_card_severity=None,
    last_cleaned=None,
    branding_hours_this_month=0,
    branding_target_hours=60,
    current_bay="X1",
    mileage_total=100000,
):
    """Minimal Train factory for isolated soft-constraint tests."""
    return Train(
        train_id=train_id,
        fitness_cert_expiry=fitness_cert_expiry or date(2027, 1, 1),
        job_card_severity=job_card_severity,
        last_cleaned=last_cleaned or PLANNING_DATE,
        branding_hours_this_month=branding_hours_this_month,
        branding_target_hours=branding_target_hours,
        current_bay=current_bay,
        mileage_total=mileage_total,
    )


def _bare_model(trains):
    """
    Builds decision variables and the exactly-one-state structural
    constraint only — deliberately no hard constraints from Part 1,
    so these tests isolate soft-constraint behavior.
    """
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


# --- Cleaning penalty tests ---

def test_cleaning_penalty_is_positive_when_overdue_train_not_cleaning():
    overdue_train = make_train("X1", last_cleaned=PLANNING_DATE - timedelta(days=10))
    model, assign_vars = _bare_model([overdue_train])
    model.Add(assign_vars[("X1", STANDBY)] == 1)  # force NOT cleaning
    penalty = build_cleaning_penalty([overdue_train], assign_vars)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(penalty) == CLEANING_PENALTY_WEIGHT


def test_cleaning_penalty_is_zero_when_overdue_train_assigned_cleaning():
    overdue_train = make_train("X1", last_cleaned=PLANNING_DATE - timedelta(days=10))
    model, assign_vars = _bare_model([overdue_train])
    model.Add(assign_vars[("X1", CLEANING)] == 1)
    penalty = build_cleaning_penalty([overdue_train], assign_vars)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(penalty) == 0


def test_cleaning_penalty_ignores_trains_not_overdue():
    fresh_train = make_train("X1", last_cleaned=PLANNING_DATE)  # cleaned today
    model, assign_vars = _bare_model([fresh_train])
    model.Add(assign_vars[("X1", STANDBY)] == 1)
    penalty = build_cleaning_penalty([fresh_train], assign_vars)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(penalty) == 0


# --- Branding penalty tests ---

def test_branding_penalty_matches_shortfall_when_not_in_service():
    train = make_train("X1", branding_hours_this_month=45, branding_target_hours=60)  # shortfall 15
    model, assign_vars = _bare_model([train])
    model.Add(assign_vars[("X1", STANDBY)] == 1)
    penalty = build_branding_penalty([train], assign_vars)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(penalty) == 15 * BRANDING_PENALTY_WEIGHT


def test_branding_penalty_is_zero_when_in_service():
    train = make_train("X1", branding_hours_this_month=45, branding_target_hours=60)
    model, assign_vars = _bare_model([train])
    model.Add(assign_vars[("X1", SERVICE)] == 1)
    penalty = build_branding_penalty([train], assign_vars)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(penalty) == 0


def test_branding_penalty_is_zero_when_target_already_met():
    train = make_train("X1", branding_hours_this_month=70, branding_target_hours=60)  # exceeded
    model, assign_vars = _bare_model([train])
    model.Add(assign_vars[("X1", STANDBY)] == 1)
    penalty = build_branding_penalty([train], assign_vars)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(penalty) == 0


def test_branding_penalty_prioritizes_larger_shortfall_when_minimized():
    """
    End-to-end proof of the proportional weighting: given a forced
    choice between only one of two trains being allowed into service,
    minimizing the branding penalty must pick the train with the
    larger shortfall.
    """
    train_small_shortfall = make_train(
        "X1", branding_hours_this_month=50, branding_target_hours=60
    )  # shortfall 10
    train_large_shortfall = make_train(
        "X2", branding_hours_this_month=30, branding_target_hours=60
    )  # shortfall 30
    trains = [train_small_shortfall, train_large_shortfall]
    model, assign_vars = _bare_model(trains)
    model.AddExactlyOne(
        [assign_vars[("X1", SERVICE)], assign_vars[("X2", SERVICE)]]
    )
    penalty = build_branding_penalty(trains, assign_vars)
    model.Minimize(penalty)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(assign_vars[("X2", SERVICE)]) == 1
    assert solver.Value(assign_vars[("X1", SERVICE)]) == 0
