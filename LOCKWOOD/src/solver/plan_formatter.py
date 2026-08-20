"""
Formats a solved CP-SAT plan into a clean, structured representation
for printing or downstream use (e.g. later API responses).

Scope for this task (Part 1c): a simple structured formatter only.
No explainability text is generated here — that is a later task.
"""

from ortools.sat.python import cp_model

from src.models import Train
from src.solver.states import ALL_STATES


def format_plan(solver: cp_model.CpSolver, assign_vars: dict, trains: list[Train]) -> list[dict]:
    """
    Extracts the solved assignment into a list of plain dictionaries,
    one per train, in the same order as the input `trains` list.

    Args:
        solver: a CpSolver instance that has already solved the model.
        assign_vars: the (train_id, state) -> BoolVar dict from build_model.
        trains: the list of Train objects the model was built for.

    Returns:
        A list of dicts, each shaped like:
            {"train_id": "KMRL-01", "assigned_state": "service"}
    """
    plan = []
    for train in trains:
        assigned_state = None
        for state in ALL_STATES:
            if solver.Value(assign_vars[(train.train_id, state)]) == 1:
                assigned_state = state
                break
        plan.append({"train_id": train.train_id, "assigned_state": assigned_state})
    return plan


def print_plan(plan: list[dict]) -> None:
    """Prints a formatted plan (as returned by format_plan) to the console."""
    print("\nInduction Plan:")
    for entry in plan:
        print(f"  {entry['train_id']}: {entry['assigned_state']}")
