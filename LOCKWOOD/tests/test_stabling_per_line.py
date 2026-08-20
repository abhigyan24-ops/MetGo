"""
Dedicated tests proving the Part 3a per-line stabling redesign: trains
on different yard lines never block each other, while same-line
blocking continues to work exactly as Part 1c intended. Uses a
minimal custom 2-line, 4-bay scenario, deliberately separate from the
real 6-train test fleet, for the smallest possible reproduction.
"""

from datetime import date

from ortools.sat.python import cp_model

from src.constants import PLANNING_DATE
from src.models import Train, YardLine, YardLayout
from src.solver.model_builder import build_model
from src.solver.states import SERVICE, STANDBY


def make_train(train_id, current_bay):
    """Minimal Train factory — only current_bay varies across this file's tests."""
    return Train(
        train_id=train_id,
        fitness_cert_expiry=date(2027, 1, 1),
        job_card_severity=None,
        last_cleaned=PLANNING_DATE,
        branding_hours_this_month=60,
        branding_target_hours=60,
        current_bay=current_bay,
        mileage_total=100000,
    )


def _two_line_layout():
    return YardLayout(lines={
        "L1": YardLine(line_id="L1", bay_order=["L1-A", "L1-B"]),
        "L2": YardLine(line_id="L2", bay_order=["L2-A", "L2-B"]),
    })


def test_deepest_train_on_line_1_blocked_by_line_1_entrance():
    yard = _two_line_layout()
    front = make_train("FRONT", "L1-A")
    deep = make_train("DEEP", "L1-B")
    trains = [front, deep]
    model, assign_vars = build_model(trains, yard)
    model.Add(assign_vars[("FRONT", STANDBY)] == 1)
    model.Add(assign_vars[("DEEP", SERVICE)] == 1)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status == cp_model.INFEASIBLE


def test_deepest_train_on_line_2_not_blocked_by_line_1_entrance():
    yard = _two_line_layout()
    front_line1 = make_train("FRONT_L1", "L1-A")
    deep_line2 = make_train("DEEP_L2", "L2-B")
    trains = [front_line1, deep_line2]
    model, assign_vars = build_model(trains, yard)
    model.Add(assign_vars[("FRONT_L1", STANDBY)] == 1)
    model.Add(assign_vars[("DEEP_L2", SERVICE)] == 1)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
