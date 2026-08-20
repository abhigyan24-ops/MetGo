"""
Tests for Part 5a-fix's yard capacity hard constraint (maintenance
track: 3 bays, confirmed real fact; wash track: 2 trains, a flagged
assumption -- see constants.py).

Includes a permanent regression guard (test_25_train_stress_no_longer_collapses_to_all_cleaning)
reproducing the exact failure found against the real seeded database in
Part 5b verification: with every train looking maximally overdue for
cleaning (the "never completed a cleaning slot" fail-safe from Part 3b,
firing for literally every train because none of the real seed data's
cleaning_slots rows are marked completed), the solver used to put all
25 trains in cleaning simultaneously -- a real, reproduced, and now
fixed bug, not a hypothetical one.
"""

from datetime import date

from ortools.sat.python import cp_model

from src.constants import MAX_TRAINS_IN_CLEANING, MAX_TRAINS_IN_MAINTENANCE, PLANNING_DATE
from src.models import Train, YardLayout, YardLine
from src.solver.decision_breakdown import check_hard_feasibility
from src.solver.model_builder import build_model
from src.solver.objective import build_total_objective
from src.solver.plan_formatter import format_plan
from src.solver.states import ALL_STATES, MAINTENANCE, CLEANING
from src.solver.validation import validate_plan


def make_train(train_id, current_bay="B1", fitness_cert_expiry=None, job_card_severity=None,
                last_cleaned=None, branding_hours_this_month=60, branding_target_hours=60,
                mileage_total=100000):
    return Train(
        train_id=train_id,
        fitness_cert_expiry=fitness_cert_expiry or date(2026, 12, 1),
        job_card_severity=job_card_severity,
        last_cleaned=last_cleaned or PLANNING_DATE,
        branding_hours_this_month=branding_hours_this_month,
        branding_target_hours=branding_target_hours,
        current_bay=current_bay,
        mileage_total=mileage_total,
    )


def test_maintenance_capacity_hard_blocks_a_fourth_train():
    """A bare model where 3 trains are already forced into maintenance
    (at cap) -- forcing a 4th must be infeasible."""
    trains = [make_train(f"M{i}", current_bay=f"B{i}") for i in range(4)]
    model = cp_model.CpModel()
    assign_vars = {}
    for t in trains:
        for s in ALL_STATES:
            assign_vars[(t.train_id, s)] = model.NewBoolVar(f"{t.train_id}_{s}")
        model.AddExactlyOne(assign_vars[(t.train_id, s)] for s in ALL_STATES)
    maintenance_vars = [assign_vars[(t.train_id, MAINTENANCE)] for t in trains]
    model.Add(sum(maintenance_vars) <= MAX_TRAINS_IN_MAINTENANCE)
    for t in trains:
        model.Add(assign_vars[(t.train_id, MAINTENANCE)] == 1)  # force ALL 4 into maintenance
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status == cp_model.INFEASIBLE


def test_cleaning_capacity_hard_blocks_a_third_train():
    trains = [make_train(f"C{i}", current_bay=f"B{i}") for i in range(3)]
    model = cp_model.CpModel()
    assign_vars = {}
    for t in trains:
        for s in ALL_STATES:
            assign_vars[(t.train_id, s)] = model.NewBoolVar(f"{t.train_id}_{s}")
        model.AddExactlyOne(assign_vars[(t.train_id, s)] for s in ALL_STATES)
    cleaning_vars = [assign_vars[(t.train_id, CLEANING)] for t in trains]
    model.Add(sum(cleaning_vars) <= MAX_TRAINS_IN_CLEANING)
    for t in trains:
        model.Add(assign_vars[(t.train_id, CLEANING)] == 1)  # force ALL 3 into cleaning
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status == cp_model.INFEASIBLE


def test_validate_plan_catches_over_capacity_maintenance():
    plan = [{"train_id": f"M{i}", "assigned_state": "maintenance"} for i in range(MAX_TRAINS_IN_MAINTENANCE + 1)]
    violations = validate_plan(plan, [], YardLayout(lines={}))
    assert any("maintenance track capacity" in v for v in violations)


def test_validate_plan_catches_over_capacity_cleaning():
    plan = [{"train_id": f"C{i}", "assigned_state": "cleaning"} for i in range(MAX_TRAINS_IN_CLEANING + 1)]
    violations = validate_plan(plan, [], YardLayout(lines={}))
    assert any("wash track capacity" in v for v in violations)


def test_validate_plan_allows_at_exactly_capacity():
    plan = [{"train_id": f"M{i}", "assigned_state": "maintenance"} for i in range(MAX_TRAINS_IN_MAINTENANCE)]
    violations = validate_plan(plan, [], YardLayout(lines={}))
    assert violations == []


def test_decision_breakdown_reports_capacity_hard_block():
    trains = [make_train(f"T{i}", current_bay=f"B{i}") for i in range(MAX_TRAINS_IN_CLEANING + 1)]
    plan = [
        {"train_id": t.train_id, "assigned_state": "cleaning" if i < MAX_TRAINS_IN_CLEANING else "service"}
        for i, t in enumerate(trains)
    ]
    the_extra_train = trains[-1]
    reason = check_hard_feasibility(the_extra_train, "cleaning", plan, trains, YardLayout(lines={}))
    assert reason is not None
    assert "wash track" in reason.lower()


def test_decision_breakdown_no_capacity_block_for_already_cleaning_train():
    """A train already assigned cleaning in the plan isn't blocked from
    (trivially) staying cleaning, even if the fleet is at cap -- it's
    not a NEW addition to the count."""
    trains = [make_train(f"T{i}", current_bay=f"B{i}") for i in range(MAX_TRAINS_IN_CLEANING)]
    plan = [{"train_id": t.train_id, "assigned_state": "cleaning"} for t in trains]
    reason = check_hard_feasibility(trains[0], "cleaning", plan, trains, YardLayout(lines={}))
    assert reason is None


def test_25_train_stress_no_longer_collapses_to_all_cleaning():
    """
    Permanent regression guard for the real bug found in Part 5b
    verification: 25 trains, real 5-line/26-bay yard shape, every
    train with NO completed cleaning history (last_cleaned=date.min,
    exactly what the Part 3b adapter's fail-safe produces when a real
    train's cleaning_slots are all completed=False) -- otherwise
    healthy data (valid certs, no job cards, on-target branding,
    identical mileage). Before this fix, this produced all 25 trains
    in cleaning. It must not anymore.
    """
    lines = [
        YardLine(line_id="L1", bay_order=[f"L1-{i}" for i in range(1, 7)]),
        YardLine(line_id="L2", bay_order=[f"L2-{i}" for i in range(1, 7)]),
        YardLine(line_id="L3", bay_order=[f"L3-{i}" for i in range(1, 6)]),
        YardLine(line_id="L4", bay_order=[f"L4-{i}" for i in range(1, 6)]),
        YardLine(line_id="L5", bay_order=[f"L5-{i}" for i in range(1, 5)]),
    ]
    yard = YardLayout(lines={l.line_id: l for l in lines})
    all_bays = [b for line in lines for b in line.bay_order]

    trains = [
        make_train(f"T{i+1:02d}", current_bay=all_bays[i], last_cleaned=date.min)
        for i in range(25)
    ]

    model, assign_vars = build_model(trains, yard)
    model.Minimize(build_total_objective(trains, assign_vars, yard))
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

    plan = format_plan(solver, assign_vars, trains)
    state_counts = {}
    for row in plan:
        state_counts[row["assigned_state"]] = state_counts.get(row["assigned_state"], 0) + 1

    assert state_counts.get("cleaning", 0) <= MAX_TRAINS_IN_CLEANING
    assert state_counts.get("maintenance", 0) <= MAX_TRAINS_IN_MAINTENANCE
    assert state_counts.get("cleaning", 0) < 25, "the exact collapse this test guards against"

    violations = validate_plan(plan, trains, yard)
    assert violations == []
