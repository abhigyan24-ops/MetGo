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

    return (
        cleaning_penalty
        + branding_penalty
        + wear_leveling_penalty
        + shunting_penalty
        + major_job_card_penalty
        + expiring_soon_penalty
    )
