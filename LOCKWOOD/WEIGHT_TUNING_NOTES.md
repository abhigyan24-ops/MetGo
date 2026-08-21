# Lockwood Weight & Constraint Tuning Notes

This file documents deliberate simplifications and known next steps in the
MetGo CP-SAT model, so they don't silently get lost between implementation
sessions.

---

## [SIMPLIFICATION] Flat service-level floor (no time-of-day planning windows)

**Added:** 2026-08-21  
**Constant:** `MIN_SERVICE_TRAINS = 15` in `src/constants.py`  
**Constraint location:** `src/solver/model_builder.py`, Hard Constraint 5

### What it does now
A single hard floor of **15 trains** is applied to the entire planning window —
the solver must put at least 15 trains into the `SERVICE` state or the plan is
infeasible.

### Why 15
Derived from KMRL's published figures (27.96 km line, 35 km/h average speed):

| Scenario | Trains required | Hard floor? |
|:---|:---|:---|
| 5-min rush-hour peak | 21 | No — too likely to cause infeasibility |
| **7-min sustained peak** | **15** | **Yes — current floor** |
| 10-min off-peak | 11 | No — too permissive, doesn't enforce peak commitment |

15 (7-minute sustained peak headway) is the deliberate middle ground: it
commits to real peak-hour service levels without risking spurious infeasibility
when a modest number of trains are simultaneously hard-blocked by critical job
cards or expired fitness certs.

### What it doesn't do (known simplification)
The model currently has **no concept of time-of-day**. A real KMRL planning
system would run different service-count floors depending on the planning window:
- **Peak windows (7–10 AM, 5–8 PM):** 15–21 trains in service
- **Off-peak windows:** 11 trains minimum

Because the induction plan covers the full service day, a proper implementation
should distinguish these windows and apply separate floors per slot.

### Logged next step
> Add time-of-day-aware service floor constraints: split the planning horizon
> into peak (7–10 AM, 5–8 PM) and off-peak windows, apply `sum(service_vars) >= 15`
> during peak slots and `sum(service_vars) >= 11` during off-peak slots.
> This requires the model to know which trains operate during which time windows,
> which in turn requires per-slot decision variables rather than the current
> single-assignment-per-train design.
>
> Estimated scope: medium (model architecture change, not just a constant tweak).

---

## [CONFIRMED ASSUMPTION] Turnback buffer at terminals

**Used in:** service floor calculation above  
**Value:** 3 min per terminal × 2 terminals = 6 min added to round-trip cycle time

The 3-minute-per-terminal turnback buffer is a standard rapid-transit operational
default. KMRL's actual turnback dwell times are operationally confidential and
not published. If the real value differs materially, `MIN_SERVICE_TRAINS` should
be recalculated with the corrected round-trip cycle.

---

## [CONFIRMED FACT] Yard capacity limits

**Constants:** `MAX_TRAINS_IN_MAINTENANCE = 3`, `MAX_TRAINS_IN_CLEANING = 2`

`MAX_TRAINS_IN_MAINTENANCE = 3` is confirmed from seed data (maintenance track
has exactly 3 bays).

`MAX_TRAINS_IN_CLEANING = 2` is an assumption (wash track capacity not
definitively documented); this is a conservative placeholder. If the real
capacity is 1 or 3, update this constant and the model adapts automatically.

---

## [RECONSTRUCTED — NOT ORIGINAL TEXT] Cleaning penalty investigation

**Status:** The original documentation of this investigation was lost (overwritten 
2026-08-21, never committed to git, unrecoverable from history). What follows is 
reconstructed from a summary written by an outside reviewer who read the original 
file before it was lost — it is NOT the original analysis, wording, or data. 
Treat this as a rough pointer to what was investigated, not as source-of-truth 
documentation. If the original reasoning matters for a real decision, the 
investigation should be re-run rather than relied on.

**What was investigated:** a comparison between two approaches to weighting the 
cleaning-urgency soft constraint — a flat penalty (same cost regardless of how 
overdue a train's cleaning is) versus a penalty that scales proportionally with 
days overdue.

**What was found:** a real trade-off between cleaning urgency and service 
availability — i.e., weighting cleaning more aggressively (via the proportional 
approach) pulled trains out of service sooner to get them cleaned, at some cost 
to service-count optimization elsewhere in the objective function. The exact 
magnitude of this trade-off and which approach was ultimately favored are not 
recoverable.

**Known follow-on from this investigation:** this is where the missing 
min-service-level constraint was originally flagged as a gap — since addressed 
above (MIN_SERVICE_TRAINS = 15).

**Recommended next step:** if precise cleaning-penalty tuning matters going 
forward, re-run this comparison properly (flat vs. proportional, measured against 
the current MIN_SERVICE_TRAINS=15 floor) and document it fresh, rather than 
treating this reconstruction as sufficient.

---

## [CONFIRMED FACT & ESTIMATE] Muttom Yard Structural Modeling

**Status:** Updated to reflect the real functional zones of the KMRL Muttom Depot.

**Sourced from Real Documents:**
The following elements of the yard geometry are confirmed facts derived from KMRL's detailed project reports (DPR) and environmental impact assessments:
- The depot covers 15.12 hectares.
- The presence of the following functional zones: Stabling lines, Scheduled inspection lines, Overhaul workshop, Major-repair bays, Wheel-profiling facility, and heavy cleaning/wash facility.
- `MAX_TRAINS_IN_MAINTENANCE = 3` represents the 3 bays in the Major Repair Line (M1).

**Reasonable Estimates:**
Exact bay-by-bay blueprints are not public. The bay counts for the other functional zones are structurally honest estimates configured to support a 25-train fleet:
- 26 Stabling bays across 5 lines (L1-L5)
- 2 Scheduled Inspection bays (I1)
- 1 Overhaul Workshop bay (O1)
- 1 Wheel Profiling Siding (P1)
- 2 Wash/Cleaning bays (W1)

**Solver Clarification:**
The 3-bay limit for `MAINTENANCE` in the CP-SAT solver strictly scopes to the Major Repair Line (M1). The other maintenance-type zones (I1, O1, P1) are mapped to `BayType.MAINTENANCE` for physical yard-graph richness (so they appear in the digital twin and allow shunting), but they do not expand the solver's 3-train limit for the actual `MAINTENANCE` state.
