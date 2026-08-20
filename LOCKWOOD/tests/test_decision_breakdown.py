"""
Tests for Part 4a's decision-breakdown module -- the foundation for
real, numbers-grounded explainability (why THIS state and not another).
"""

from datetime import date

from src.constants import PLANNING_DATE
from src.data.test_fleet_6 import TEST_FLEET_6, TEST_YARD_LAYOUT_6
from src.models import Train, YardLayout, YardLine
from src.solver.decision_breakdown import check_hard_feasibility, evaluate_state_for_train, explain_decision
from src.solver.model_builder import build_model
from src.solver.objective import build_total_objective
from src.solver.plan_formatter import format_plan
from ortools.sat.python import cp_model


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


def _solve_test_fleet():
    model, assign_vars = build_model(TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    model.Minimize(build_total_objective(TEST_FLEET_6, assign_vars, TEST_YARD_LAYOUT_6))
    solver = cp_model.CpSolver()
    solver.Solve(model)
    return format_plan(solver, assign_vars, TEST_FLEET_6)


def test_expired_cert_reports_hard_block_for_service():
    train = make_train("X1", fitness_cert_expiry=date(2026, 8, 1))  # expired before PLANNING_DATE
    plan = [{"train_id": "X1", "assigned_state": "maintenance"}]
    reason = check_hard_feasibility(train, "service", plan, [train], YardLayout(lines={}))
    assert reason is not None
    assert "expired" in reason.lower()


def test_critical_job_card_reports_hard_block_for_service():
    train = make_train("X1", job_card_severity="critical")
    plan = [{"train_id": "X1", "assigned_state": "cleaning"}]
    reason = check_hard_feasibility(train, "service", plan, [train], YardLayout(lines={}))
    assert reason is not None
    assert "critical" in reason.lower()


def test_stabling_block_reports_blocking_train_id():
    front = make_train("FRONT", current_bay="B1")
    deep = make_train("DEEP", current_bay="B2")
    yard = YardLayout(lines={"L1": YardLine(line_id="L1", bay_order=["B1", "B2"])})
    plan = [{"train_id": "FRONT", "assigned_state": "standby"}, {"train_id": "DEEP", "assigned_state": "standby"}]
    reason = check_hard_feasibility(deep, "service", plan, [front, deep], yard)
    assert reason is not None
    assert "FRONT" in reason


def test_stabling_does_not_block_when_front_train_also_leaves():
    front = make_train("FRONT", current_bay="B1")
    deep = make_train("DEEP", current_bay="B2")
    yard = YardLayout(lines={"L1": YardLine(line_id="L1", bay_order=["B1", "B2"])})
    plan = [{"train_id": "FRONT", "assigned_state": "service"}, {"train_id": "DEEP", "assigned_state": "standby"}]
    reason = check_hard_feasibility(deep, "service", plan, [front, deep], yard)
    assert reason is None


def test_different_line_never_blocks():
    t1 = make_train("A", current_bay="B1")
    t2 = make_train("B", current_bay="C1")
    yard = YardLayout(lines={
        "L1": YardLine(line_id="L1", bay_order=["B1"]),
        "L2": YardLine(line_id="L2", bay_order=["C1"]),
    })
    plan = [{"train_id": "A", "assigned_state": "standby"}, {"train_id": "B", "assigned_state": "standby"}]
    reason = check_hard_feasibility(t2, "service", plan, [t1, t2], yard)
    assert reason is None


def test_evaluate_state_for_train_matches_actual_solver_penalty():
    """The evaluated penalty for a train's ACTUAL chosen state must
    exactly match its real contribution to the solved objective --
    proving evaluate_state_for_train reuses the real penalty functions
    correctly, not a drifted reimplementation."""
    plan = _solve_test_fleet()
    plan_by_id = {row["train_id"]: row["assigned_state"] for row in plan}
    kmrl03 = next(t for t in TEST_FLEET_6 if t.train_id == "KMRL-03")
    result = evaluate_state_for_train(kmrl03, plan_by_id["KMRL-03"], plan, TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    assert result["feasible"] is True
    # KMRL-03 is cleaning: branding shortfall (8) + shunting (bay index 2) = 10
    assert result["soft_penalty_total"] == 10
    assert result["soft_penalty_breakdown"]["branding"] == 8
    assert result["soft_penalty_breakdown"]["shunting"] == 2


def test_explain_decision_chosen_state_is_cheapest_feasible_option():
    """For every train in the real verified reference plan, the chosen
    state's penalty must be <= every feasible alternative's penalty --
    this is what "optimal" means, and it's a real property this test
    can check mechanically rather than trust by construction."""
    plan = _solve_test_fleet()
    for row in plan:
        result = explain_decision(row["train_id"], plan, TEST_FLEET_6, TEST_YARD_LAYOUT_6)
        for alt_state, alt in result["alternatives"].items():
            if alt["feasible"]:
                assert alt["penalty_total"] >= result["chosen_state_penalty"], (
                    f"{row['train_id']}: chosen state {result['chosen_state']} "
                    f"(penalty {result['chosen_state_penalty']}) was NOT the "
                    f"cheapest -- {alt_state} would cost {alt['penalty_total']}"
                )


def test_explain_decision_reports_kmrl03_service_as_hard_blocked():
    plan = _solve_test_fleet()
    result = explain_decision("KMRL-03", plan, TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    assert result["alternatives"]["service"]["feasible"] is False
    assert "critical" in result["alternatives"]["service"]["hard_block_reason"].lower()


def test_penalty_delta_is_positive_when_alternative_is_worse():
    plan = _solve_test_fleet()
    result = explain_decision("KMRL-06", plan, TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    # KMRL-06 chose service; standby should cost strictly more (it's overdue
    # for cleaning and would still be penalized in standby).
    assert result["alternatives"]["standby"]["penalty_delta"] > 0
