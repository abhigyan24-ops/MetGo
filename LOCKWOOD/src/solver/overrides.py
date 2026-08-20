"""
Native, first-class disruption/override modeling for the KMRL train
induction planning problem.

Replaces the Part 3c ad-hoc hack (a single hardcoded model.Add() line
living inside app/worker/tasks.py) with a real, testable mechanism in
lockwood itself, matching all four scenario types the actual frontend
what-if simulator sends: breakdown, maintenance, cleaning, cert_expired.
"""

from dataclasses import dataclass

from src.solver.states import CLEANING, MAINTENANCE, SERVICE

VALID_OVERRIDE_TYPES = {"breakdown", "maintenance", "cleaning", "cert_expired"}


@dataclass
class Override:
    """
    A single manual override: force a train's state away from what the
    solver would otherwise freely choose.

    Fields:
        train_id: the train this override applies to.
        override_type: one of VALID_OVERRIDE_TYPES.
            "breakdown"     -> train cannot be assigned SERVICE (hard).
            "cert_expired"  -> train cannot be assigned SERVICE (hard) --
                                same constraint effect as breakdown, but
                                a DIFFERENT real-world reason, so it is
                                kept as a distinct override_type for
                                reporting/explainability purposes.
            "maintenance"   -> train is force-assigned MAINTENANCE.
            "cleaning"      -> train is force-assigned CLEANING.
    """
    train_id: str
    override_type: str

    def __post_init__(self):
        if self.override_type not in VALID_OVERRIDE_TYPES:
            raise ValueError(
                f"Unknown override_type {self.override_type!r}; "
                f"must be one of {sorted(VALID_OVERRIDE_TYPES)}"
            )


def apply_overrides(model, assign_vars, overrides):
    """
    Applies a list of Override objects directly onto an already-built
    CP-SAT model (as returned by model_builder.build_model()), adding
    one additional hard constraint per override.

    Must be called AFTER build_model() and BEFORE model.Minimize() /
    solver.Solve() -- overrides are additional hard constraints, and
    like every other hard constraint in this system, they take
    precedence over all soft-constraint optimization.

    Args:
        model: the cp_model.CpModel returned by build_model().
        assign_vars: the (train_id, state) -> BoolVar dict.
        overrides: list of Override objects. An empty list or None is
            valid and applies no constraints (baseline plan, no
            disruption).

    Returns:
        A dict mapping train_id -> human-readable override reason
        string, for every train an override was applied to. Callers
        (e.g. explainability, Part 5c) can use this to report WHY a
        train's assignment was forced, distinct from the solver's own
        optimization reasoning.

    Raises:
        ValueError: if an override references a train_id not present
            in assign_vars (e.g. a stale or typo'd ID).
    """
    if not overrides:
        return {}

    reasons = {}
    for override in overrides:
        if (override.train_id, SERVICE) not in assign_vars:
            raise ValueError(
                f"Override references unknown train_id {override.train_id!r} "
                f"-- not present in this model's assign_vars."
            )

        if override.override_type == "breakdown":
            model.Add(assign_vars[(override.train_id, SERVICE)] == 0)
            reasons[override.train_id] = "Manual override: reported breakdown -- service prohibited."
        elif override.override_type == "cert_expired":
            model.Add(assign_vars[(override.train_id, SERVICE)] == 0)
            reasons[override.train_id] = "Manual override: fitness certificate simulated as expired -- service prohibited."
        elif override.override_type == "maintenance":
            model.Add(assign_vars[(override.train_id, MAINTENANCE)] == 1)
            reasons[override.train_id] = "Manual override: forced to maintenance."
        elif override.override_type == "cleaning":
            model.Add(assign_vars[(override.train_id, CLEANING)] == 1)
            reasons[override.train_id] = "Manual override: forced to cleaning."

    return reasons
