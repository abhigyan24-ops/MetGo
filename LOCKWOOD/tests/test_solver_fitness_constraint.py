"""
Tests verifying Part 1b's fitness-certificate hard constraint.

NOTE: as of Part 1c, build_model() requires a yard_layout argument
(needed for the stabling-adjacency constraint added in this task).
This file has been updated to pass TEST_YARD_LAYOUT_6 accordingly —
the tests themselves are otherwise unchanged from Part 1b.
"""

from ortools.sat.python import cp_model

from src.data.test_fleet_6 import TEST_FLEET_6, TEST_YARD_LAYOUT_6
from src.solver.model_builder import build_model
from src.solver.states import ALL_STATES, SERVICE


def _solve(trains, yard_layout):
    model, assign_vars = build_model(trains, yard_layout)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    return solver, status, assign_vars


def test_solver_finds_a_feasible_solution():
    solver, status, _ = _solve(TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_every_train_assigned_exactly_one_state():
    solver, status, assign_vars = _solve(TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

    for train in TEST_FLEET_6:
        total = sum(
            solver.Value(assign_vars[(train.train_id, state)])
            for state in ALL_STATES
        )
        assert total == 1, f"{train.train_id} was not assigned exactly one state"


def test_kmrl_02_never_assigned_service():
    solver, status, assign_vars = _solve(TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(assign_vars[("KMRL-02", SERVICE)]) == 0


def test_kmrl_05_is_not_blocked_from_service():
    model, assign_vars = build_model(TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    model.Add(assign_vars[("KMRL-05", SERVICE)] == 1)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_kmrl_02_forced_to_service_is_infeasible():
    model, assign_vars = build_model(TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    model.Add(assign_vars[("KMRL-02", SERVICE)] == 1)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status == cp_model.INFEASIBLE
