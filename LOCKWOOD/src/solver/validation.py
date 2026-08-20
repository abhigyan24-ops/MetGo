"""
Independently validates a solved induction plan against every hard
constraint, WITHOUT trusting that the CP-SAT solver enforced them
correctly. This is a deliberate defense-in-depth check: it re-derives
whether each hard constraint actually holds by inspecting the final
plan directly, rather than assuming the solver's internal logic was
correct.

This is the Part 1 "definition of done" checkpoint: a valid plan must
produce ZERO violations from this validator.
"""

from src.constants import PLANNING_DATE, MAX_TRAINS_IN_CLEANING, MAX_TRAINS_IN_MAINTENANCE
from src.models import Train, YardLayout
from src.solver.states import CLEANING, MAINTENANCE, STANDBY


def validate_plan(plan: list[dict], trains: list[Train], yard_layout: YardLayout) -> list[str]:
    """
    Checks a formatted plan (as returned by plan_formatter.format_plan)
    against every hard constraint.

    Args:
        plan: list of {"train_id": ..., "assigned_state": ...} dicts.
        trains: the original list of Train objects (for looking up
            each train's certificate, job card, and bay data).
        yard_layout: the YardLayout the trains are stabled in.

    Returns:
        A list of human-readable violation strings. An empty list
        means the plan is fully valid — zero hard-constraint
        violations.
    """
    violations = []
    plan_by_id = {p["train_id"]: p["assigned_state"] for p in plan}

    # --- Check 1: expired fitness certificate must never be service ---
    for train in trains:
        if train.fitness_cert_expiry < PLANNING_DATE:
            if plan_by_id[train.train_id] == "service":
                violations.append(
                    f"{train.train_id} has an expired fitness certificate "
                    f"but was assigned to service."
                )

    # --- Check 2: open job cards must never be service ---
    for train in trains:
        if train.job_card_severity == "critical":
            if plan_by_id[train.train_id] == "service":
                violations.append(
                    f"{train.train_id} has a critical job "
                    f"card but was assigned to service."
                )

    # --- Check 3: stabling bay adjacency ---
    for deep_train in trains:
        deep_state = plan_by_id[deep_train.train_id]
        if deep_state == STANDBY:
            continue  # not moving, no adjacency concern

        deep_line = yard_layout.line_for_bay(deep_train.current_bay)
        if deep_line is None:
            continue
        deep_index = yard_layout.bay_index(deep_train.current_bay)

        for front_train in trains:
            if front_train.train_id == deep_train.train_id:
                continue
            front_line = yard_layout.line_for_bay(front_train.current_bay)
            if front_line is None or front_line.line_id != deep_line.line_id:
                continue
            front_index = yard_layout.bay_index(front_train.current_bay)
            if front_index < deep_index:
                front_state = plan_by_id[front_train.train_id]
                if front_state == STANDBY:
                    violations.append(
                        f"{deep_train.train_id} (bay {deep_train.current_bay}) "
                        f"was assigned '{deep_state}' but is blocked by "
                        f"{front_train.train_id} (bay {front_train.current_bay}), "
                        f"which remains standby."
                    )

    _check_yard_capacity(plan, violations)
    return violations


def _check_yard_capacity(plan: list[dict], violations: list[str]) -> None:
    """
    Check 4 (Part 5a-fix): no more than MAX_TRAINS_IN_MAINTENANCE trains
    in maintenance, and no more than MAX_TRAINS_IN_CLEANING trains in
    cleaning, simultaneously -- appends to `violations` in place.
    """
    maintenance_count = sum(1 for row in plan if row["assigned_state"] == MAINTENANCE)
    if maintenance_count > MAX_TRAINS_IN_MAINTENANCE:
        violations.append(
            f"{maintenance_count} trains assigned maintenance, exceeding the "
            f"{MAX_TRAINS_IN_MAINTENANCE}-bay maintenance track capacity."
        )

    cleaning_count = sum(1 for row in plan if row["assigned_state"] == CLEANING)
    if cleaning_count > MAX_TRAINS_IN_CLEANING:
        violations.append(
            f"{cleaning_count} trains assigned cleaning, exceeding the "
            f"{MAX_TRAINS_IN_CLEANING}-train wash track capacity."
        )
