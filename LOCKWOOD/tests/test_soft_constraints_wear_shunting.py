"""
Tests for Part 2b's wear-leveling and shunting soft-constraint
penalty builders. UPDATED IN PART 3a: the make_train factory matches
the new Train shape, and the shunting tests use the new multi-line
YardLayout/YardLine constructors instead of the old flat bay_order
shape.
"""

from datetime import date

from ortools.sat.python import cp_model

from src.constants import PLANNING_DATE
from src.models import Train, YardLine, YardLayout
from src.solver.soft_constraint_config import SHUNTING_PENALTY_WEIGHT
from src.solver.soft_constraints import build_shunting_penalty, build_wear_leveling_penalty
from src.solver.states import ALL_STATES, SERVICE, STANDBY


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


# --- Wear-leveling penalty tests (unchanged logic from Part 2b) ---

def test_wear_leveling_penalty_is_zero_for_below_average_train_in_service():
    below_avg = make_train("X1", mileage_total=100000)
    above_avg = make_train("X2", mileage_total=300000)
    trains = [below_avg, above_avg]
    model, assign_vars = _bare_model(trains)
    model.Add(assign_vars[("X1", SERVICE)] == 1)
    model.Add(assign_vars[("X2", STANDBY)] == 1)
    penalty = build_wear_leveling_penalty(trains, assign_vars)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(penalty) == 0


def test_wear_leveling_penalty_is_positive_for_above_average_train_in_service():
    below_avg = make_train("X1", mileage_total=100000)
    above_avg = make_train("X2", mileage_total=300000)
    trains = [below_avg, above_avg]
    model, assign_vars = _bare_model(trains)
    model.Add(assign_vars[("X1", STANDBY)] == 1)
    model.Add(assign_vars[("X2", SERVICE)] == 1)
    penalty = build_wear_leveling_penalty(trains, assign_vars)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(penalty) == 100


def test_wear_leveling_penalty_prefers_lower_mileage_train_for_service_when_minimized():
    below_avg = make_train("X1", mileage_total=100000)
    above_avg = make_train("X2", mileage_total=300000)
    trains = [below_avg, above_avg]
    model, assign_vars = _bare_model(trains)
    model.AddExactlyOne(
        [assign_vars[("X1", SERVICE)], assign_vars[("X2", SERVICE)]]
    )
    penalty = build_wear_leveling_penalty(trains, assign_vars)
    model.Minimize(penalty)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(assign_vars[("X1", SERVICE)]) == 1
    assert solver.Value(assign_vars[("X2", SERVICE)]) == 0


# --- Shunting penalty tests (UPDATED for multi-line YardLayout) ---

def test_shunting_penalty_is_zero_for_front_train_regardless_of_state():
    yard = YardLayout(lines={"L1": YardLine(line_id="L1", bay_order=["B1", "B2"])})
    front = make_train("X1", current_bay="B1")
    trains = [front]
    model, assign_vars = _bare_model(trains)
    model.Add(assign_vars[("X1", SERVICE)] == 1)
    penalty = build_shunting_penalty(trains, assign_vars, yard)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(penalty) == 0


def test_shunting_penalty_is_positive_for_deep_train_when_moved():
    yard = YardLayout(lines={"L1": YardLine(line_id="L1", bay_order=["B1", "B2"])})
    deep = make_train("X1", current_bay="B2")
    trains = [deep]
    model, assign_vars = _bare_model(trains)
    model.Add(assign_vars[("X1", SERVICE)] == 1)
    penalty = build_shunting_penalty(trains, assign_vars, yard)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(penalty) == SHUNTING_PENALTY_WEIGHT * 1


def test_shunting_penalty_is_zero_for_deep_train_kept_standby():
    yard = YardLayout(lines={"L1": YardLine(line_id="L1", bay_order=["B1", "B2"])})
    deep = make_train("X1", current_bay="B2")
    trains = [deep]
    model, assign_vars = _bare_model(trains)
    model.Add(assign_vars[("X1", STANDBY)] == 1)
    penalty = build_shunting_penalty(trains, assign_vars, yard)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(penalty) == 0


def test_shunting_penalty_prefers_front_train_when_minimized():
    yard = YardLayout(lines={"L1": YardLine(line_id="L1", bay_order=["B1", "B2", "B3"])})
    front = make_train("X1", current_bay="B1")
    deep = make_train("X2", current_bay="B3")
    trains = [front, deep]
    model, assign_vars = _bare_model(trains)
    model.AddExactlyOne(
        [assign_vars[("X1", SERVICE)], assign_vars[("X2", SERVICE)]]
    )
    penalty = build_shunting_penalty(trains, assign_vars, yard)
    model.Minimize(penalty)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(assign_vars[("X1", SERVICE)]) == 1
    assert solver.Value(assign_vars[("X2", SERVICE)]) == 0
