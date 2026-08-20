"""
Soft-constraint penalty builders for the KMRL train induction
planning problem.

UPDATED IN PART 3a:
  - build_shunting_penalty now uses yard_layout.bay_index(), which is
    per-line aware, instead of the old flat bay_order.index() lookup.
  - build_major_job_card_penalty is NEW: penalizes assigning SERVICE
    to a train with an open MAJOR-severity job card.
"""

from src.constants import PLANNING_DATE
from src.models import Train, YardLayout
from src.solver.soft_constraint_config import (
    BRANDING_PENALTY_WEIGHT,
    CLEANING_OVERDUE_DAYS,
    CLEANING_PENALTY_WEIGHT,
    EXPIRING_SOON_DAYS,
    EXPIRING_SOON_PENALTY_WEIGHT,
    MAJOR_JOB_CARD_PENALTY_WEIGHT,
    SHUNTING_PENALTY_WEIGHT,
    WEAR_LEVELING_PENALTY_WEIGHT,
)
from src.solver.states import CLEANING, MAINTENANCE, SERVICE, STANDBY


def build_cleaning_penalty(trains: list[Train], assign_vars: dict):
    """Unchanged from Part 2a. Flat penalty per overdue train not assigned CLEANING."""
    penalty_terms = []
    for train in trains:
        days_since_cleaned = (PLANNING_DATE - train.last_cleaned).days
        if days_since_cleaned > CLEANING_OVERDUE_DAYS:
            not_cleaning_var = assign_vars[(train.train_id, CLEANING)].Not()
            penalty_terms.append(CLEANING_PENALTY_WEIGHT * not_cleaning_var)
    return sum(penalty_terms) if penalty_terms else 0


def build_branding_penalty(trains: list[Train], assign_vars: dict):
    """Unchanged from Part 2a. Penalty proportional to branding-hour shortfall."""
    penalty_terms = []
    for train in trains:
        shortfall = train.branding_target_hours - train.branding_hours_this_month
        if shortfall > 0:
            not_service_var = assign_vars[(train.train_id, SERVICE)].Not()
            penalty_terms.append(BRANDING_PENALTY_WEIGHT * shortfall * not_service_var)
    return sum(penalty_terms) if penalty_terms else 0


def build_wear_leveling_penalty(trains: list[Train], assign_vars: dict):
    """Unchanged from Part 2b. Penalizes above-average-mileage trains in service."""
    if not trains:
        return 0
    avg_mileage = sum(t.mileage_total for t in trains) / len(trains)
    penalty_terms = []
    for train in trains:
        deviation = train.mileage_total - avg_mileage
        if deviation > 0:
            deviation_thousands = int(deviation // 1000)
            if deviation_thousands > 0:
                service_var = assign_vars[(train.train_id, SERVICE)]
                penalty_terms.append(
                    WEAR_LEVELING_PENALTY_WEIGHT * deviation_thousands * service_var
                )
    return sum(penalty_terms) if penalty_terms else 0


def build_shunting_penalty(
    trains: list[Train],
    assign_vars: dict,
    yard_layout: YardLayout,
):
    """
    Calculates the shunting penalty for trains on stabling lines.

    Trains whose current bay is not present in the stabling yard layout
    (for example, a wash or maintenance bay) are skipped because they
    do not have a stabling-line position for shunting calculation.
    """
    penalty_terms = []

    for train in trains:
        try:
            bay_index = yard_layout.bay_index(train.current_bay)
        except ValueError:
            continue

        if bay_index > 0:
            not_standby_var = assign_vars[
                (train.train_id, STANDBY)
            ].Not()

            penalty_terms.append(
                SHUNTING_PENALTY_WEIGHT
                * bay_index
                * not_standby_var
            )   

    return sum(penalty_terms) if penalty_terms else 0


def build_major_job_card_penalty(trains: list[Train], assign_vars: dict):
    """
    NEW IN PART 3a. Penalizes assigning SERVICE to a train with an
    open MAJOR-severity job card. Unlike CRITICAL (a hard block in
    model_builder.py), MAJOR is a preference to route the train toward
    maintenance, not an absolute prohibition.

    Args:
        trains: list of Train objects.
        assign_vars: the (train_id, state) -> BoolVar dict.

    Returns:
        A CP-SAT linear expression representing total major-job-card
        penalty. Not added to any model here — the caller decides.
    """
    penalty_terms = []
    for train in trains:
        if train.job_card_severity == "major":
            service_var = assign_vars[(train.train_id, SERVICE)]
            penalty_terms.append(MAJOR_JOB_CARD_PENALTY_WEIGHT * service_var)
    return sum(penalty_terms) if penalty_terms else 0


def build_expiring_soon_penalty(trains: list[Train], assign_vars: dict):
    """
    Builds the fitness-cert-expiring-soon soft-constraint penalty
    expression (new in Part 3b).

    A cert that has ALREADY expired is hard-blocked from service
    entirely (model_builder.py) and is never considered here. A cert
    that is not yet expired but will expire within EXPIRING_SOON_DAYS
    days of PLANNING_DATE is still fully legal for any state -- this
    is a soft preference to route it toward MAINTENANCE proactively
    (so a fresh certificate can be arranged) before it actually
    expires, not a prohibition. A flat penalty of
    EXPIRING_SOON_PENALTY_WEIGHT is added whenever such a train is
    assigned any state OTHER than MAINTENANCE.

    Args:
        trains: list of Train objects.
        assign_vars: the (train_id, state) -> BoolVar dict.

    Returns:
        A CP-SAT linear expression representing total expiring-soon
        penalty. Not added to any model here -- the caller decides.
    """
    penalty_terms = []
    for train in trains:
        days_until_expiry = (train.fitness_cert_expiry - PLANNING_DATE).days
        if 0 <= days_until_expiry <= EXPIRING_SOON_DAYS:
            not_maintenance_var = assign_vars[(train.train_id, MAINTENANCE)].Not()
            penalty_terms.append(EXPIRING_SOON_PENALTY_WEIGHT * not_maintenance_var)
    return sum(penalty_terms) if penalty_terms else 0
