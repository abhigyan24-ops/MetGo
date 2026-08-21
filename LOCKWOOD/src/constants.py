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

# --- Service level floor ---
# Hard minimum number of trains that must be in the SERVICE state.
#
# DERIVED FROM KMRL PUBLISHED FIGURES (not assumed):
#   Line length:        27.96 km  (Aluva ↔ Tripunithura, KMRL corporate site)
#   Average op speed:   35 km/h   (KMRL technical specification)
#   Peak headway:       5 min     (KMRL timetable, peak 7–10 AM / 5–8 PM)
#   Sustained peak:     7 min     (KMRL timetable, broader peak window)
#   Off-peak headway:   10 min    (KMRL timetable)
#
# CALCULATION:
#   One-way trip time   = 27.96 / 35 = 0.799 h = 47.9 min ≈ 48 min
#   Turnback buffer     = 3 min per terminal × 2 = 6 min   [ASSUMPTION — not
#                         publicly documented; standard rapid-transit default]
#   Round-trip cycle    = 48 × 2 + 6 = 102 min
#
#   Trains @ 5-min peak headway  = ⌈102/5⌉  = ⌈20.4⌉  = 21  trains
#   Trains @ 7-min peak headway  = ⌈102/7⌉  = ⌈14.6⌉  = 15  trains
#   Trains @ 10-min off-peak     = ⌈102/10⌉ = ⌈10.2⌉  = 11  trains
#
# CHOSEN FLOOR: 15 trains (7-minute sustained peak headway figure).
#
# Rationale for 15 over the other candidates:
#   - 11 (off-peak minimum) was the previous value but guarantees nothing
#     close to KMRL's actual peak-hour service commitment, since soft
#     constraints organically push service count above 11 anyway — the
#     constraint only binds in pathological failure scenarios, not at the
#     operationally relevant service level.
#   - 21 (5-minute rush-hour peak) is the tightest operational case but
#     leaves zero slack for maintenance, cleaning, or standby when the
#     fleet has any trains simultaneously blocked by hard constraints
#     (e.g. T04, T12 in the current test seed have critical job cards).
#     With a 25-train fleet and 2 hard-blocked, only 3 trains remain for
#     maintenance + cleaning combined, which the yard capacity constraints
#     (MAX 3 maintenance, MAX 2 cleaning) would strain under.
#   - 15 (7-minute sustained peak) is the defensible middle ground:
#     it commits to maintaining genuine peak-hour headway under the
#     typical peak window (not just the tightest 5-min rush), while
#     leaving 10 trains for standby/maintenance/cleaning, which is
#     realistic for nightly operations with a 25-train fleet.
#
# KNOWN SIMPLIFICATION: this is a single flat floor applied across the
# entire planning window. The model does not currently distinguish
# peak vs. off-peak time-of-day slots. Proper time-of-day-aware floors
# (15–21 at peak, 11 off-peak) are a logged next step — see
# WEIGHT_TUNING_NOTES.md for the tracking note.
MIN_SERVICE_TRAINS = 15
