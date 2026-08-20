"""
Tests for the combined objective function — UPDATED IN PART 3a with a
new verified reference solution reflecting the multi-line yard
redesign. The plan itself is unchanged from Part 2c; the objective
value dropped from 85.0 to 76.0 because shunting cost is now computed
per-line (see Section 10 of the Part 3a prompt for why).
"""

from ortools.sat.python import cp_model

from src.data.test_fleet_6 import TEST_FLEET_6, TEST_YARD_LAYOUT_6
from src.solver.model_builder import build_model
from src.solver.objective import build_total_objective
from src.solver.plan_formatter import format_plan
from src.solver.validation import validate_plan


def _solve_optimized_plan():
    model, assign_vars = build_model(TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    objective = build_total_objective(TEST_FLEET_6, assign_vars, TEST_YARD_LAYOUT_6)
    model.Minimize(objective)
    solver = cp_model.CpSolver()
    solver.parameters.random_seed = 0
    status = solver.Solve(model)
    return solver, status, assign_vars


def test_optimized_plan_is_feasible():
    solver, status, _ = _solve_optimized_plan()
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_optimized_plan_has_zero_hard_constraint_violations():
    solver, status, assign_vars = _solve_optimized_plan()
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    plan = format_plan(solver, assign_vars, TEST_FLEET_6)
    violations = validate_plan(plan, TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    assert violations == [], f"Expected zero violations, got: {violations}"


def test_optimized_plan_matches_verified_reference_solution():
    """
    Regression test against the Part 3b verified reference solution.
    The plan is unchanged from Part 3a; the objective rose from 76.0
    to 82.0 because KMRL-05 (cert expiring the day after
    PLANNING_DATE) now incurs the new expiring-soon penalty (6) for
    staying in service rather than moving to maintenance -- the
    solver judged that penalty cheaper than the alternative of losing
    KMRL-05's service+branding value, so the plan itself did not
    change, only its cost. See the Part 3b prompt for the full
    independently-verified output this was checked against.
    """
    solver, status, assign_vars = _solve_optimized_plan()
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

    expected_plan = {
        "KMRL-01": "service",
        "KMRL-02": "maintenance",
        "KMRL-03": "cleaning",
        "KMRL-04": "cleaning",
        "KMRL-05": "service",
        "KMRL-06": "service",
    }

    plan = format_plan(solver, assign_vars, TEST_FLEET_6)
    actual_plan = {p["train_id"]: p["assigned_state"] for p in plan}

    assert actual_plan == expected_plan
    assert solver.ObjectiveValue() == 82.0
