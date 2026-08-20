"""
Shared constants for MetGo — the KMRL train induction planning system.
"""

from datetime import date

# The night we are generating an induction plan for.
PLANNING_DATE = date(2026, 8, 15)

# Fixed monthly branding exposure target, in hours, used by every train.
BRANDING_TARGET_HOURS = 60

# Total number of bays in the small test yard used for Part 1 development.
# NOTE: this is a simplified linear test yard, NOT the real Muttom Yard
# layout — that full layout is out of scope for this task.
TEST_YARD_TOTAL_BAYS = 6

# --- Yard capacity (Part 5a-fix) ---
# Physical limits on how many trains can simultaneously occupy a
# non-stabling resource, grounded in the real Muttom Yard facts
# established from the database team's seed data.
#
# MAX_TRAINS_IN_MAINTENANCE is a CONFIRMED real fact: the maintenance
# track has exactly 3 bays (see the project context summary, Section 2).
#
# MAX_TRAINS_IN_CLEANING is an ASSUMPTION, not a confirmed fact — the
# real yard has "a wash track" (singular, per the same source), but no
# exact simultaneous-train capacity was ever given. 2 is a conservative
# placeholder pending confirmation with the database team; this is
# exactly the kind of flagged-not-fabricated assumption used previously
# for CleaningSlot.completed_at in Part 3c. If the real number differs,
# only this constant needs to change — everything that reads it
# (model_builder.py, validation.py, decision_breakdown.py) adapts
# automatically.
MAX_TRAINS_IN_MAINTENANCE = 3
MAX_TRAINS_IN_CLEANING = 2
