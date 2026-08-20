"""
Tests for Part 1c's plan formatter and independent validator — the
final Part 1 checkpoint: a solved plan must produce zero validation
violations.
"""

from ortools.sat.python import cp_model

from src.data.test_fleet_6 import TEST_FLEET_6, TEST_YARD_LAYOUT_6
from src.solver.model_builder import build_model
from src.solver.plan_formatter import format_plan
from src.solver.validation import validate_plan


def test_solved_plan_has_zero_validation_violations():
    model, assign_vars = build_model(TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

    plan = format_plan(solver, assign_vars, TEST_FLEET_6)
    violations = validate_plan(plan, TEST_FLEET_6, TEST_YARD_LAYOUT_6)

    assert violations == [], f"Expected zero violations, got: {violations}"


def test_validator_detects_a_deliberately_broken_plan():
    """
    Sanity check on the validator itself: feed it a plan that
    deliberately violates the fitness-certificate rule (KMRL-02 in
    service despite an expired certificate) and confirm the validator
    actually catches it. This proves the validator isn't silently
    passing everything.
    """
    broken_plan = [
        {"train_id": t.train_id, "assigned_state": "standby"}
        for t in TEST_FLEET_6
    ]
    for entry in broken_plan:
        if entry["train_id"] == "KMRL-02":
            entry["assigned_state"] = "service"

    violations = validate_plan(broken_plan, TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    assert len(violations) >= 1
    assert any("KMRL-02" in v for v in violations)
