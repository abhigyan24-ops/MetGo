"""
Tests for Part 5a's native override mechanism -- the real, tested
replacement for Part 3c's ad-hoc breakdown hack, covering all four
override types the actual frontend what-if simulator sends.
"""

from ortools.sat.python import cp_model

from src.data.test_fleet_6 import TEST_FLEET_6, TEST_YARD_LAYOUT_6
from src.solver.model_builder import build_model
from src.solver.objective import build_total_objective
from src.solver.overrides import Override, apply_overrides
from src.solver.plan_formatter import format_plan
from src.solver.states import CLEANING, MAINTENANCE, SERVICE


def _solve_with_overrides(overrides):
    model, assign_vars = build_model(TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    reasons = apply_overrides(model, assign_vars, overrides)
    model.Minimize(build_total_objective(TEST_FLEET_6, assign_vars, TEST_YARD_LAYOUT_6))
    solver = cp_model.CpSolver()
    solver.parameters.random_seed = 0
    status = solver.Solve(model)
    return solver, status, assign_vars, reasons


def test_invalid_override_type_raises_immediately():
    try:
        Override("KMRL-01", "sabotage")
        assert False, "should have raised ValueError"
    except ValueError as exc:
        assert "sabotage" in str(exc)


def test_unknown_train_id_raises_immediately():
    model, assign_vars = build_model(TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    try:
        apply_overrides(model, assign_vars, [Override("GHOST-99", "breakdown")])
        assert False, "should have raised ValueError"
    except ValueError as exc:
        assert "GHOST-99" in str(exc)


def test_no_overrides_is_a_valid_no_op():
    solver, status, assign_vars, reasons = _solve_with_overrides(None)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert reasons == {}
    # Must match the Part 4a/2c verified baseline exactly.
    assert solver.Value(assign_vars[("KMRL-01", SERVICE)]) == 1


def test_breakdown_forces_train_out_of_service():
    """KMRL-01 is normally assigned service (verified baseline) -- a
    breakdown override must force it elsewhere."""
    solver, status, assign_vars, reasons = _solve_with_overrides(
        [Override("KMRL-01", "breakdown")]
    )
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(assign_vars[("KMRL-01", SERVICE)]) == 0
    assert "breakdown" in reasons["KMRL-01"].lower()


def test_cert_expired_forces_train_out_of_service_with_distinct_reason():
    solver, status, assign_vars, reasons = _solve_with_overrides(
        [Override("KMRL-01", "cert_expired")]
    )
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(assign_vars[("KMRL-01", SERVICE)]) == 0
    assert "certificate" in reasons["KMRL-01"].lower()
    # Same constraint effect as breakdown, but the REASON text must differ.
    breakdown_reasons = _solve_with_overrides([Override("KMRL-01", "breakdown")])[3]
    assert reasons["KMRL-01"] != breakdown_reasons["KMRL-01"]


def test_maintenance_override_forces_exact_state():
    solver, status, assign_vars, reasons = _solve_with_overrides(
        [Override("KMRL-01", "maintenance")]
    )
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(assign_vars[("KMRL-01", MAINTENANCE)]) == 1
    assert solver.Value(assign_vars[("KMRL-01", SERVICE)]) == 0


def test_cleaning_override_forces_exact_state():
    solver, status, assign_vars, reasons = _solve_with_overrides(
        [Override("KMRL-05", "cleaning")]
    )
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(assign_vars[("KMRL-05", CLEANING)]) == 1


def test_rest_of_fleet_still_hard_constraint_valid_after_override():
    """An override on one train must never break hard-constraint
    validity for the rest of the fleet -- re-run the real validator."""
    from src.solver.validation import validate_plan

    solver, status, assign_vars, reasons = _solve_with_overrides(
        [Override("KMRL-01", "breakdown")]
    )
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    plan = format_plan(solver, assign_vars, TEST_FLEET_6)
    violations = validate_plan(plan, TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    assert violations == [], f"Expected zero violations, got: {violations}"


def test_conflicting_override_is_infeasible_not_a_crash():
    """KMRL-03 has a critical job card (hard-blocks service already).
    Forcing it into service via override must surface as INFEASIBLE,
    not raise an unrelated exception."""
    model, assign_vars = build_model(TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    model.Add(assign_vars[("KMRL-03", SERVICE)] == 1)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status == cp_model.INFEASIBLE


def test_multiple_simultaneous_overrides_all_apply():
    solver, status, assign_vars, reasons = _solve_with_overrides([
        Override("KMRL-01", "breakdown"),
        Override("KMRL-05", "cleaning"),
    ])
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(assign_vars[("KMRL-01", SERVICE)]) == 0
    assert solver.Value(assign_vars[("KMRL-05", CLEANING)]) == 1
    assert set(reasons.keys()) == {"KMRL-01", "KMRL-05"}
