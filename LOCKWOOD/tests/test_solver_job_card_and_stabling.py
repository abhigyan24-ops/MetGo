"""
Tests verifying Part 3a: the severity-based job card hard constraint,
and the per-line stabling adjacency hard constraint (replacing the old
open_job_cards / single-line tests from Part 1c, which no longer apply
to the new data shapes).
"""

from ortools.sat.python import cp_model

from src.data.test_fleet_6 import TEST_FLEET_6, TEST_YARD_LAYOUT_6
from src.solver.model_builder import build_model
from src.solver.states import MAINTENANCE, SERVICE, STANDBY


# --- Job card severity tests ---

def test_kmrl_03_never_assigned_service():
    """KMRL-03 has job_card_severity='critical' — must never be assigned service."""
    model, assign_vars = build_model(TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(assign_vars[("KMRL-03", SERVICE)]) == 0


def test_kmrl_03_forced_to_service_is_infeasible():
    model, assign_vars = build_model(TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    model.Add(assign_vars[("KMRL-03", SERVICE)] == 1)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status == cp_model.INFEASIBLE


# --- Per-line stabling adjacency tests ---

def test_same_line_blocking_still_enforced():
    """
    KMRL-04 is Line B's entrance bay (B1). If it stays standby, it
    still blocks KMRL-06 (Line B, deepest bay B3) — same-line blocking
    must still work exactly as Part 1c intended.
    """
    model, assign_vars = build_model(TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    model.Add(assign_vars[("KMRL-04", STANDBY)] == 1)
    model.Add(assign_vars[("KMRL-06", SERVICE)] == 1)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status == cp_model.INFEASIBLE


def test_different_line_does_not_block():
    """
    KMRL-01 is Line A's entrance bay (A1). KMRL-06 is Line B's deepest
    bay (B3) — a DIFFERENT line. Under the OLD single-line model these
    would have blocked each other; under the new per-line model they
    must NOT.
    """
    model, assign_vars = build_model(TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    model.Add(assign_vars[("KMRL-01", STANDBY)] == 1)
    model.Add(assign_vars[("KMRL-06", SERVICE)] == 1)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_deep_train_allowed_when_all_same_line_front_trains_also_move():
    """
    If every train in front of KMRL-06 ON ITS OWN LINE (i.e. just
    KMRL-04 and KMRL-05, both Line B) is also moving out, KMRL-06
    should be free to be assigned service. Line A's trains are
    irrelevant to this — they're on a different line entirely.
    """
    model, assign_vars = build_model(TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    model.Add(assign_vars[("KMRL-04", MAINTENANCE)] == 1)
    model.Add(assign_vars[("KMRL-05", MAINTENANCE)] == 1)
    model.Add(assign_vars[("KMRL-06", SERVICE)] == 1)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
