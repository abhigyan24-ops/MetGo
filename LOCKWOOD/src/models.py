"""
Core data models for MetGo — KMRL train induction planning.

UPDATED IN PART 3a: the yard model has been redesigned from a single
flat line (Part 1a's deliberate simplification) to a multi-line
layout, matching the real Muttom Yard topology confirmed from the
database team's seed data: 5 independent stabling lines, a
maintenance track, and a wash track. This is a justified break from
Part 1a's previously-frozen file — real integration requires it.
Every file depending on the old flat YardLayout shape has been updated
in this same task.

Train.current_bay has also changed type: from an integer bay number
(Part 1a's simplification) to a bay_id STRING (e.g. "A1"), matching
the real database schema's YardBay.bay_id field.

Train.open_job_cards has been REMOVED and replaced by
Train.job_card_severity, matching the real schema's job card severity
tiers (critical / major / minor). Only "critical" hard-blocks service
(Part 1b/1c's rule updated); "major" becomes a new soft constraint
(this task); "minor" has no scheduling effect.
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Train:
    """
    Represents a single trainset and everything the induction planner
    needs to know about it for one planning night.

    Fields:
        train_id: Unique identifier (lockwood's "KMRL-XX" format is
            kept for continuity with existing tests; translation to
            the real "T01"-"T25" format happens in the data-adapter
            layer built in Part 3b, not here).
        fitness_cert_expiry: as before (Part 1a).
        job_card_severity: one of "critical", "major", "minor", or
            None (no open job card). Replaces the old open_job_cards
            int count.
        last_cleaned: as before.
        branding_hours_this_month, branding_target_hours: as before.
        current_bay: CHANGED in Part 3a — a bay_id STRING (e.g. "A1"),
            not an int bay number.
        mileage_total: as before.
    """
    train_id: str
    fitness_cert_expiry: date
    last_cleaned: date
    branding_hours_this_month: int
    branding_target_hours: int
    current_bay: str
    mileage_total: int
    job_card_severity: str = None


@dataclass
class YardLine:
    """
    One line within the yard — a stabling road, maintenance track, or
    wash track. Bays are ordered from the entrance/exit end (index 0)
    to the deepest bay (last index). The Part 1c stabling-blocking
    logic only ever applies WITHIN a single line — trains on different
    lines never block each other.

    Fields:
        line_id: Unique identifier, e.g. "LA", "LB".
        bay_order: Ordered list of bay_id strings, entrance-end first.
    """
    line_id: str
    bay_order: list = field(default_factory=list)


@dataclass
class YardLayout:
    """
    The full multi-line yard layout, replacing Part 1a's single flat
    line. Real Muttom Yard (per the database team's seed data) has 5
    stabling lines (6, 6, 5, 5, 4 bays) plus a maintenance track and a
    wash track — lockwood's test yard (Section on test_fleet_6.py)
    uses a small 2-line version for testability.

    Fields:
        lines: dict mapping line_id -> YardLine.
    """
    lines: dict = field(default_factory=dict)

    def line_for_bay(self, bay_id: str):
        """Returns the YardLine that contains the given bay_id, or None."""
        for line in self.lines.values():
            if bay_id in line.bay_order:
                return line
        return None

    def bay_index(self, bay_id: str) -> int:
        """
        Returns the position of bay_id within its own line (0 =
        entrance/exit end). Raises ValueError if the bay isn't found
        in any line.
        """
        line = self.line_for_bay(bay_id)
        if line is None:
            raise ValueError(f"Bay {bay_id!r} not found in any yard line")
        return line.bay_order.index(bay_id)
