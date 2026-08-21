"""
Builds the CP-SAT decision variables and hard constraints for MetGo —
the KMRL train induction planning problem.

UPDATED IN PART 3a:
  - Hard constraint 2 (job cards) now checks job_card_severity ==
    "critical" specifically, replacing the old "any open job card"
    rule.
  - Hard constraint 3 (stabling adjacency) is now scoped PER LINE —
    the pairwise implication only applies between two trains on the
    SAME line. Trains on different lines never block each other.

Hard constraint 1 (fitness certificate) is unchanged from Part 1b.
"""

from ortools.sat.python import cp_model

from src.constants import PLANNING_DATE, MAX_TRAINS_IN_CLEANING, MAX_TRAINS_IN_MAINTENANCE, MIN_SERVICE_TRAINS
from src.models import Train, YardLayout
from src.solver.states import ALL_STATES, CLEANING, MAINTENANCE, SERVICE, STANDBY, BREAKDOWN


def build_model(trains: list[Train], yard_layout: YardLayout, overrides: list = None) -> tuple[cp_model.CpModel, dict]:
    """
    Builds a CP-SAT model for the given list of trains and multi-line
    yard layout, including decision variables and all three hard
    constraints.

    Args:
        trains: list of Train objects to plan for.
        yard_layout: the YardLayout (multi-line, Part 3a) describing
            bay positions.

    Returns:
        A tuple of (model, assign_vars) where:
            - model is the constructed cp_model.CpModel.
            - assign_vars is a dict mapping (train_id, state) -> BoolVar,
              for every train and every state in ALL_STATES.
    """
    model = cp_model.CpModel()
    assign_vars = {}

    # --- Decision variables ---
    for train in trains:
        for state in ALL_STATES:
            var_name = f"{train.train_id}_{state}"
            assign_vars[(train.train_id, state)] = model.NewBoolVar(var_name)

    # --- Structural constraint: exactly one state per train ---
    for train in trains:
        state_vars_for_train = [
            assign_vars[(train.train_id, state)] for state in ALL_STATES
        ]
        model.AddExactlyOne(state_vars_for_train)

    # --- Hard constraint 1: expired fitness certificate blocks service ---
    for train in trains:
        if train.fitness_cert_expiry < PLANNING_DATE:
            service_var = assign_vars[(train.train_id, SERVICE)]
            model.Add(service_var == 0)

    # --- Hard constraint 2 (Part 3a): CRITICAL job card blocks service ---
    # Only "critical" hard-blocks. "major" is a soft constraint
    # (build_major_job_card_penalty, Part 3a). "minor" and None have
    # no effect here at all.
    for train in trains:
        if train.job_card_severity == "critical":
            service_var = assign_vars[(train.train_id, SERVICE)]
            model.Add(service_var == 0)

    # --- Hard constraint 3 (Part 3a): per-line stabling adjacency ---
    # For every pair of trains on the SAME line where "front" is
    # closer to that line's exit than "deep": if "front" stays standby
    # (blocking), "deep" must also stay standby. Trains on DIFFERENT
    # lines get no implication between them at all.
        for deep_train in trains:
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
                    front_standby_var = assign_vars[
                        (front_train.train_id, STANDBY)
                    ]
                    deep_standby_var = assign_vars[
                        (deep_train.train_id, STANDBY)
                    ]

                    model.AddImplication(
                        front_standby_var,
                        deep_standby_var
                    )
    # --- Hard constraint 4: yard capacity (Part 5a-fix) ---
    # No more than MAX_TRAINS_IN_MAINTENANCE trains can occupy the
    # maintenance state simultaneously.
    # CLARIFICATION: This capacity limit (3) is strictly scoped to the 3
    # Major Repair Line (M1) bays, which is a CONFIRMED real fact. The other
    # maintenance-type zones in the yard graph (Inspection, Overhaul, Wheel
    # Profiling) are for topological richness and do not increase this solver
    # capacity limit for the MAINTENANCE state.
    # No more than MAX_TRAINS_IN_CLEANING trains can occupy the wash
    # track simultaneously (a flagged ASSUMPTION -- see constants.py).
    # Without this, nothing physically stops the solver from assigning
    # every train in the fleet to the same state at once, which is
    # exactly what was observed against the real 25-train seeded
    # database once every train looked equally "never cleaned": the
    # solver correctly, but uselessly, put all 25 trains in cleaning
    # simultaneously, since nothing made that illegal.
    maintenance_vars = [assign_vars[(t.train_id, MAINTENANCE)] for t in trains]
    model.Add(sum(maintenance_vars) <= MAX_TRAINS_IN_MAINTENANCE)

    cleaning_vars = [assign_vars[(t.train_id, CLEANING)] for t in trains]
    model.Add(sum(cleaning_vars) <= MAX_TRAINS_IN_CLEANING)

    # --- Hard constraint 5: minimum service-level floor ---
    # Guarantees that the solver cannot produce a plan with fewer trains
    # in service than MIN_SERVICE_TRAINS, derived from KMRL's published
    # line length (27.96 km), average operating speed (35 km/h), and
    # off-peak headway (10 min). Full calculation is in constants.py.
    #
    # This is a HARD constraint (not a soft penalty) — if the fleet has
    # too many trains simultaneously blocked by critical job cards,
    # expired fitness certs, or yard capacity limits to satisfy this floor,
    # the solver will report INFEASIBLE, which is surfaced to the caller in
    # tasks.py as status="INFEASIBLE". That is the correct behavior: a
    # plan that silently violates the service floor is worse than no plan.
    #
    # The guard (len(trains) >= MIN_SERVICE_TRAINS) prevents the solver
    # from being trivially infeasible in test scenarios with fewer than
    # MIN_SERVICE_TRAINS trains seeded.
    if len(trains) >= MIN_SERVICE_TRAINS:
        service_vars = [assign_vars[(t.train_id, SERVICE)] for t in trains]
        model.Add(sum(service_vars) >= MIN_SERVICE_TRAINS)

    # --- Hard constraint 6: BREAKDOWN only via override ---
    # Prevents the solver from choosing BREAKDOWN as an escape hatch when
    # other constraints are tight. If a train doesn't have an explicit
    # breakdown override, its BREAKDOWN variable is structurally forced to 0.
    overrides = overrides or []
    breakdown_overrides = {o.train_id for o in overrides if o.override_type == "breakdown"}
    for train in trains:
        if train.train_id not in breakdown_overrides:
            model.Add(assign_vars[(train.train_id, BREAKDOWN)] == 0)

    return model, assign_vars
