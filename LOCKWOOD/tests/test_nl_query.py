"""
Tests for Part 4b's natural-language query layer. Every assertion here
checks against numbers already independently verified in Part 4a
(see tests/test_decision_breakdown.py and the Part 4a prompt's
Section 5 reference output) -- this file does not introduce any new
numeric ground truth, only checks that answer_query() reports those
same numbers correctly in prose.
"""

from src.data.test_fleet_6 import TEST_FLEET_6, TEST_YARD_LAYOUT_6
from src.solver.model_builder import build_model
from src.solver.nl_query import answer_query
from src.solver.objective import build_total_objective
from src.solver.plan_formatter import format_plan
from ortools.sat.python import cp_model


def _solve_test_fleet():
    model, assign_vars = build_model(TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    model.Minimize(build_total_objective(TEST_FLEET_6, assign_vars, TEST_YARD_LAYOUT_6))
    solver = cp_model.CpSolver()
    solver.Solve(model)
    return format_plan(solver, assign_vars, TEST_FLEET_6)


def test_why_is_train_in_state_matches_and_reports_correct_cost():
    plan = _solve_test_fleet()
    result = answer_query("Why is KMRL-03 in cleaning?", plan, TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    assert result["matched_pattern"] == "why_state"
    assert "cost of 10" in result["answer"]
    assert "branding: 8" in result["answer"]
    assert "shunting: 2" in result["answer"]


def test_why_is_train_query_is_case_insensitive_on_train_id():
    plan = _solve_test_fleet()
    result = answer_query("why is kmrl-01 in service?", plan, TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    assert result["matched_pattern"] == "why_state"
    assert "KMRL-01" in result["answer"]


def test_why_isnt_train_in_state_reports_hard_block_reason():
    plan = _solve_test_fleet()
    result = answer_query("Why isn't KMRL-02 in standby?", plan, TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    assert result["matched_pattern"] == "why_not_state"
    assert "cannot be assigned standby" in result["answer"]
    assert "KMRL-03" in result["answer"]  # names the actual blocking train


def test_why_cant_train_be_in_state_matches_same_pattern():
    plan = _solve_test_fleet()
    result = answer_query("Why can't KMRL-03 be in service?", plan, TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    assert result["matched_pattern"] == "why_not_state"
    assert "critical" in result["answer"].lower()


def test_which_trains_are_in_state_lists_correct_trains():
    plan = _solve_test_fleet()
    result = answer_query("Which trains are in service?", plan, TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    assert result["matched_pattern"] == "which_trains_in_state"
    assert result["trains"] == ["KMRL-01", "KMRL-05", "KMRL-06"]


def test_which_trains_have_critical_job_cards():
    plan = _solve_test_fleet()
    result = answer_query("Which trains have critical job cards?", plan, TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    assert result["matched_pattern"] == "which_trains_severity"
    assert result["trains"] == ["KMRL-03"]


def test_which_trains_have_major_job_cards_none_found():
    plan = _solve_test_fleet()
    result = answer_query("Which trains have major job cards?", plan, TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    assert result["matched_pattern"] == "which_trains_severity"
    assert result["trains"] == []
    assert "no trains" in result["answer"].lower()


def test_hypothetical_query_reports_exact_penalty_delta():
    plan = _solve_test_fleet()
    result = answer_query("What would happen if KMRL-06 were in maintenance?", plan, TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    assert result["matched_pattern"] == "hypothetical"
    assert "22 more" in result["answer"]
    assert "34 vs 12" in result["answer"]


def test_hypothetical_query_reports_hard_block_when_infeasible():
    plan = _solve_test_fleet()
    result = answer_query("What would happen if KMRL-03 were in service?", plan, TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    assert result["matched_pattern"] == "hypothetical"
    assert "cannot be assigned service" in result["answer"]


def test_unparseable_query_returns_fallback_with_none_pattern():
    plan = _solve_test_fleet()
    result = answer_query("What is the weather today?", plan, TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    assert result["matched_pattern"] is None
    assert "couldn't parse" in result["answer"].lower()


def test_unknown_train_id_falls_through_to_fallback():
    plan = _solve_test_fleet()
    result = answer_query("Why is KMRL-99 in service?", plan, TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    assert result["matched_pattern"] is None


def test_asking_about_already_true_state_says_so():
    plan = _solve_test_fleet()
    result = answer_query("Why isn't KMRL-03 in cleaning?", plan, TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    assert result["matched_pattern"] == "why_not_state"
    assert "IS currently assigned cleaning" in result["answer"]
