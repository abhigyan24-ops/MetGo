"""
Isolated tests for Part 3a's new major-job-card soft constraint,
following the same bare-model isolation pattern established in
Part 2a/2b.
"""

from datetime import date

from ortools.sat.python import cp_model

from src.constants import PLANNING_DATE
from src.models import Train
from src.solver.soft_constraint_config import MAJOR_JOB_CARD_PENALTY_WEIGHT
from src.solver.soft_constraints import build_major_job_card_penalty
from src.solver.states import ALL_STATES, SERVICE, STANDBY


def make_train(train_id, job_card_severity):
    return Train(
        train_id=train_id,
        fitness_cert_expiry=date(2027, 1, 1),
        job_card_severity=job_card_severity,
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


def test_major_job_card_penalty_positive_when_in_service():
    train = make_train("X1", "major")
    model, assign_vars = _bare_model([train])
    model.Add(assign_vars[("X1", SERVICE)] == 1)
    penalty = build_major_job_card_penalty([train], assign_vars)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(penalty) == MAJOR_JOB_CARD_PENALTY_WEIGHT


def test_major_job_card_penalty_zero_when_not_in_service():
    train = make_train("X1", "major")
    model, assign_vars = _bare_model([train])
    model.Add(assign_vars[("X1", STANDBY)] == 1)
    penalty = build_major_job_card_penalty([train], assign_vars)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(penalty) == 0


def test_minor_job_card_never_penalized():
    train = make_train("X1", "minor")
    model, assign_vars = _bare_model([train])
    model.Add(assign_vars[("X1", SERVICE)] == 1)
    penalty = build_major_job_card_penalty([train], assign_vars)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(penalty) == 0


def test_no_job_card_never_penalized():
    train = make_train("X1", None)
    model, assign_vars = _bare_model([train])
    model.Add(assign_vars[("X1", SERVICE)] == 1)
    penalty = build_major_job_card_penalty([train], assign_vars)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(penalty) == 0


def test_major_does_not_hard_block_service():
    """
    MAJOR severity must NOT make service infeasible — only CRITICAL
    does that (enforced in model_builder.py, not here). This test
    confirms forcing a MAJOR train into service remains solvable.
    """
    train = make_train("X1", "major")
    model, assign_vars = _bare_model([train])
    model.Add(assign_vars[("X1", SERVICE)] == 1)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
