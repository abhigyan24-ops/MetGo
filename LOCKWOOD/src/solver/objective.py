"""
Combines all six soft-constraint penalties (as of Part 3b) into a
single weighted objective expression.
"""

from src.models import Train, YardLayout
from src.solver.soft_constraints import (
    build_branding_penalty,
    build_cleaning_penalty,
    build_expiring_soon_penalty,
    build_major_job_card_penalty,
    build_shunting_penalty,
    build_wear_leveling_penalty,
)


def build_total_objective(trains: list[Train], assign_vars: dict, yard_layout: YardLayout):
    """Sum of all six soft-constraint penalties. Does not call model.Minimize()."""
    cleaning_penalty = build_cleaning_penalty(trains, assign_vars)
    branding_penalty = build_branding_penalty(trains, assign_vars)
    wear_leveling_penalty = build_wear_leveling_penalty(trains, assign_vars)
    shunting_penalty = build_shunting_penalty(trains, assign_vars, yard_layout)
    major_job_card_penalty = build_major_job_card_penalty(trains, assign_vars)
    expiring_soon_penalty = build_expiring_soon_penalty(trains, assign_vars)

    # Penalty to ensure BREAKDOWN is never chosen organically.
    # A massive penalty guarantees the solver only pays it when an override
    # hard-constrains BREAKDOWN to 1. Otherwise, it dodges the penalty by
    # choosing any other state.
    from src.solver.states import BREAKDOWN
    breakdown_vars = [assign_vars[(t.train_id, BREAKDOWN)] for t in trains]
    breakdown_penalty = sum(breakdown_vars) * 999999

    return (
        cleaning_penalty
        + branding_penalty
        + wear_leveling_penalty
        + shunting_penalty
        + major_job_card_penalty
        + expiring_soon_penalty
        + breakdown_penalty
    )
