"""
Entry point script — UPDATED IN PART 3a to print the new major-job-card
penalty in the breakdown.
"""

from ortools.sat.python import cp_model

from src.data.test_fleet_6 import TEST_FLEET_6, TEST_YARD_LAYOUT_6
from src.solver.model_builder import build_model
from src.solver.objective import build_total_objective
from src.solver.soft_constraints import (
    build_branding_penalty,
    build_cleaning_penalty,
    build_expiring_soon_penalty,
    build_major_job_card_penalty,
    build_shunting_penalty,
    build_wear_leveling_penalty,
)
from src.solver.plan_formatter import format_plan, print_plan
from src.solver.validation import validate_plan


def run() -> None:
    model, assign_vars = build_model(TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    objective = build_total_objective(TEST_FLEET_6, assign_vars, TEST_YARD_LAYOUT_6)
    model.Minimize(objective)

    solver = cp_model.CpSolver()
    solver.parameters.random_seed = 0
    status = solver.Solve(model)

    print(f"Solver status: {solver.StatusName(status)}")

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("No feasible solution found.")
        return

    print(f"Total objective value (lower is better): {solver.ObjectiveValue()}")

    plan = format_plan(solver, assign_vars, TEST_FLEET_6)
    print_plan(plan)

    print("\nPenalty breakdown:")
    print(f"  Cleaning:        {solver.Value(build_cleaning_penalty(TEST_FLEET_6, assign_vars))}")
    print(f"  Branding:        {solver.Value(build_branding_penalty(TEST_FLEET_6, assign_vars))}")
    print(f"  Wear-leveling:   {solver.Value(build_wear_leveling_penalty(TEST_FLEET_6, assign_vars))}")
    print(f"  Shunting:        {solver.Value(build_shunting_penalty(TEST_FLEET_6, assign_vars, TEST_YARD_LAYOUT_6))}")
    print(f"  Major job card:  {solver.Value(build_major_job_card_penalty(TEST_FLEET_6, assign_vars))}")
    print(f"  Expiring soon:   {solver.Value(build_expiring_soon_penalty(TEST_FLEET_6, assign_vars))}")

    violations = validate_plan(plan, TEST_FLEET_6, TEST_YARD_LAYOUT_6)
    print(f"\nValidation: {len(violations)} hard-constraint violation(s) found.")
    for v in violations:
        print(f"  - {v}")


if __name__ == "__main__":
    run()
