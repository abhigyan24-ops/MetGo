"""
Explains WHY a solved plan chose the state it did for a given train,
by evaluating every alternative state and reporting either why it was
hard-infeasible or exactly how much more (or less) it would have cost.

KEY INSIGHT this module relies on: none of the six soft constraints
(cleaning, branding, wear-leveling, shunting, major job card, expiring
soon) depend on any OTHER train's assigned state -- each is purely a
function of one train's own data and its own candidate state (fleet
average mileage, used by wear-leveling, is a constant computed from
raw mileage data, not from anyone's assignment). This means the
penalty a train would incur under a hypothetical state can be computed
in complete isolation from the rest of the plan, using the EXACT SAME
build_*_penalty functions the real solver uses -- not a parallel
reimplementation that could quietly drift out of sync with them.

The only thing that is NOT separable is the stabling hard constraint
(Part 1c/3a): whether a train is legally allowed to leave its bay
depends on whether the trains in front of it, in the same yard line,
are also leaving -- which depends on the rest of the plan. This is
handled by inspecting the already-solved plan directly (not
re-solving), since by the time this module runs, everyone else's
assignment is fixed and known.
"""

from ortools.sat.python import cp_model

from src.constants import PLANNING_DATE, MAX_TRAINS_IN_CLEANING, MAX_TRAINS_IN_MAINTENANCE
from src.models import Train, YardLayout
from src.solver.soft_constraints import (
    build_branding_penalty,
    build_cleaning_penalty,
    build_expiring_soon_penalty,
    build_major_job_card_penalty,
    build_shunting_penalty,
    build_wear_leveling_penalty,
)
from src.solver.states import ALL_STATES, CLEANING, MAINTENANCE, SERVICE, STANDBY


def _blocking_front_train_id(train: Train, all_trains: list, yard_layout: YardLayout):
    """
    Returns the train_id of the FIRST (closest-to-exit) train, in the
    same line, in front of 	rain, that is still standby in the plan --
    or None if no such train exists. Helper for check_hard_feasibility.
    """
    line = yard_layout.line_for_bay(train.current_bay)
    if line is None:
        return None
    trains_by_bay = {t.current_bay: t for t in all_trains}
    my_index = line.bay_order.index(train.current_bay)
    for front_bay in line.bay_order[:my_index]:
        if front_bay in trains_by_bay:
            yield trains_by_bay[front_bay]


def _trains_behind(train: Train, all_trains: list, yard_layout: YardLayout):
    """
    Yields every train, in the same line, DEEPER than 	rain (i.e.
    	rain is in front of them). Used to check the reverse direction
    of the stabling constraint: switching THIS train to standby can
    retroactively block any of these trains that are fixed to a
    non-standby state elsewhere in the plan.
    """
    line = yard_layout.line_for_bay(train.current_bay)
    if line is None:
        return
    trains_by_bay = {t.current_bay: t for t in all_trains}
    my_index = line.bay_order.index(train.current_bay)
    for deeper_bay in line.bay_order[my_index + 1:]:
        if deeper_bay in trains_by_bay:
            yield trains_by_bay[deeper_bay]


def check_hard_feasibility(train: Train, candidate_state: str, plan: list, all_trains: list, yard_layout: YardLayout):
    """
    Returns a human-readable reason string if candidate_state is
    hard-infeasible for 	rain, or None if it's legal.

    "Legal" here means: if every OTHER train's assignment is held
    exactly as given in plan, would swapping just this one train to
    candidate_state still satisfy every hard constraint? This has
    TWO directions for the stabling constraint, not just one:
      1. 	rain might itself be blocked by a front train that's
         standby (checked below, unchanged from the original design).
      2. Switching 	rain TO standby can retroactively block a DEEPER
         train that's fixed to a non-standby state in plan -- that
         deeper train's plan assignment silently assumed 	rain was
         NOT standby, so making it standby breaks that assumption.
         This direction was missed in an earlier draft of this
         function and caught by
         test_explain_decision_chosen_state_is_cheapest_feasible_option,
         which is exactly why that test exists.
    """
    if candidate_state == SERVICE:
        if train.fitness_cert_expiry < PLANNING_DATE:
            days_expired = (PLANNING_DATE - train.fitness_cert_expiry).days
            return f"Fitness certificate expired {days_expired} day(s) ago -- service is legally prohibited."
        if train.job_card_severity == "critical":
            return "An open CRITICAL-severity job card legally prohibits service."

    if candidate_state != STANDBY:
        plan_by_id = {row["train_id"]: row["assigned_state"] for row in plan}
        for front_train in _blocking_front_train_id(train, all_trains, yard_layout):
            if plan_by_id.get(front_train.train_id) == STANDBY:
                return (
                    f"Blocked by {front_train.train_id} (bay {front_train.current_bay}), "
                    f"which is in front of this train in the yard and remains standby -- "
                    f"this train cannot physically leave its bay."
                )

    if candidate_state == STANDBY:
        plan_by_id = {row["train_id"]: row["assigned_state"] for row in plan}
        for deeper_train in _trains_behind(train, all_trains, yard_layout):
            deeper_state = plan_by_id.get(deeper_train.train_id)
            if deeper_state is not None and deeper_state != STANDBY:
                return (
                    f"Switching to standby would block {deeper_train.train_id} "
                    f"(bay {deeper_train.current_bay}), which is behind this train "
                    f"in the yard and is assigned '{deeper_state}' in this plan -- "
                    f"it needs this train to also leave its bay."
                )

    # Yard capacity (Part 5a-fix): switching THIS train into cleaning or
    # maintenance can push the fleet over the real physical capacity of
    # that resource, even though this train's own bay/cert/job-card
    # situation is otherwise fine. Only checked if this train is not
    # ALREADY in that state in the given plan (a no-op switch never
    # changes the count).
    plan_by_id = {row["train_id"]: row["assigned_state"] for row in plan}
    my_current_state = plan_by_id.get(train.train_id)

    if candidate_state == MAINTENANCE and my_current_state != MAINTENANCE:
        other_maintenance_count = sum(1 for s in plan_by_id.values() if s == MAINTENANCE)
        if other_maintenance_count >= MAX_TRAINS_IN_MAINTENANCE:
            return (
                f"The maintenance track is already at capacity "
                f"({other_maintenance_count}/{MAX_TRAINS_IN_MAINTENANCE} trains) in this plan -- "
                f"there is no free bay for this train."
            )

    if candidate_state == CLEANING and my_current_state != CLEANING:
        other_cleaning_count = sum(1 for s in plan_by_id.values() if s == CLEANING)
        if other_cleaning_count >= MAX_TRAINS_IN_CLEANING:
            return (
                f"The wash track is already at capacity "
                f"({other_cleaning_count}/{MAX_TRAINS_IN_CLEANING} trains) in this plan -- "
                f"there is no free slot for this train."
            )

    return None


def evaluate_state_for_train(
    train: Train,
    candidate_state: str,
    plan: list,
    all_trains: list,
    yard_layout: YardLayout,
) -> dict:
    """
    Evaluates one candidate state for one train, against an already-
    solved plan (everyone else's assignment held fixed).

    Returns:
        {
          "state": candidate_state,
          "feasible": bool,
          "hard_block_reason": str | None,
          "soft_penalty_total": int | None,   # None if infeasible
          "soft_penalty_breakdown": dict | None,  # None if infeasible
        }
    """
    hard_block_reason = check_hard_feasibility(train, candidate_state, plan, all_trains, yard_layout)
    if hard_block_reason is not None:
        return {
            "state": candidate_state,
            "feasible": False,
            "hard_block_reason": hard_block_reason,
            "soft_penalty_total": None,
            "soft_penalty_breakdown": None,
        }

    # Soft-constraint penalties are per-train separable (see module
    # docstring), so a trivial single-train, single-variable CP-SAT
    # model -- forcing this ONE train to candidate_state -- is enough
    # to read off the exact real penalty via the SAME production
    # build_*_penalty functions the actual solver used. This is a
    # single-variable model; solving it is effectively instantaneous.
    model = cp_model.CpModel()
    assign_vars = {}
    for state in ALL_STATES:
        assign_vars[(train.train_id, state)] = model.NewBoolVar(f"{train.train_id}_{state}")
    model.AddExactlyOne(assign_vars[(train.train_id, s)] for s in ALL_STATES)
    model.Add(assign_vars[(train.train_id, candidate_state)] == 1)

    penalty_exprs = {
        "cleaning": build_cleaning_penalty([train], assign_vars),
        "branding": build_branding_penalty([train], assign_vars),
        "wear_leveling": build_wear_leveling_penalty([train], assign_vars),
        "shunting": build_shunting_penalty([train], assign_vars, yard_layout),
        "major_job_card": build_major_job_card_penalty([train], assign_vars),
        "expiring_soon": build_expiring_soon_penalty([train], assign_vars),
    }
    total_expr = sum(penalty_exprs.values())
    model.Minimize(total_expr)  # trivial: only one variable is free, already fixed above

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE), (
        f"Unexpected solver status {solver.StatusName(status)} evaluating "
        f"{train.train_id} -> {candidate_state}; this should never happen "
        f"for a single-variable model with no conflicting constraints."
    )

    breakdown = {name: solver.Value(expr) for name, expr in penalty_exprs.items()}
    total = sum(breakdown.values())

    return {
        "state": candidate_state,
        "feasible": True,
        "hard_block_reason": None,
        "soft_penalty_total": total,
        "soft_penalty_breakdown": breakdown,
    }


def explain_decision(train_id: str, plan: list, all_trains: list, yard_layout: YardLayout) -> dict:
    """
    The main entry point: explains why 	rain_id was assigned the
    state it was, by evaluating every state (chosen and alternatives)
    and reporting exact penalty deltas or hard-block reasons for each.

    Returns:
        {
          "train_id": "...",
          "chosen_state": "...",
          "chosen_state_penalty": int,
          "alternatives": {
              "<other_state>": {
                  "feasible": bool,
                  "hard_block_reason": str | None,
                  "penalty_total": int | None,
                  "penalty_delta": int | None,  # positive = would have cost MORE
              },
              ...
          },
        }
    """
    trains_by_id = {t.train_id: t for t in all_trains}
    train = trains_by_id[train_id]
    plan_by_id = {row["train_id"]: row["assigned_state"] for row in plan}
    chosen_state = plan_by_id[train_id]

    evaluations = {
        state: evaluate_state_for_train(train, state, plan, all_trains, yard_layout)
        for state in ALL_STATES
    }
    chosen_eval = evaluations[chosen_state]
    assert chosen_eval["feasible"], (
        f"{train_id}'s own solved state ({chosen_state}) evaluated as "
        f"infeasible -- this would mean the original plan itself was "
        f"invalid, which validate_plan() should already have caught."
    )
    chosen_penalty = chosen_eval["soft_penalty_total"]

    alternatives = {}
    for state, evaluation in evaluations.items():
        if state == chosen_state:
            continue
        if evaluation["feasible"]:
            alternatives[state] = {
                "feasible": True,
                "hard_block_reason": None,
                "penalty_total": evaluation["soft_penalty_total"],
                "penalty_delta": evaluation["soft_penalty_total"] - chosen_penalty,
            }
        else:
            alternatives[state] = {
                "feasible": False,
                "hard_block_reason": evaluation["hard_block_reason"],
                "penalty_total": None,
                "penalty_delta": None,
            }

    return {
        "train_id": train_id,
        "chosen_state": chosen_state,
        "chosen_state_penalty": chosen_penalty,
        "chosen_state_penalty_breakdown": chosen_eval["soft_penalty_breakdown"],
        "alternatives": alternatives,
    }
