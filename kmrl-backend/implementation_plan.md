# Ground Yard Geometry in Real Muttom Depot Functional Zones

This plan updates the yard layout to reflect real Muttom depot functional zones, shifting from synthetic line names to structurally honest real names and counts, while clearly demarcating known facts from reasonable estimates.

## Proposed Changes

### 1. Update Yard Geometry Seed Data
#### [MODIFY] [seed_fleet.py](file:///c:/Users/abhig/OneDrive/Desktop/MetGo/kmrl-backend/app/seed/seed_fleet.py)
Update the `YARD_LAYOUT` dictionary to include the realistic functional zones:
- **Stabling Lines**: Retain the 5 existing stabling roads (L1-L5) with 26 bays total (6,6,5,5,4), which handles the 25-train fleet capacity.
- **Major Repair Line**: The existing 3 bays (M1) will be explicitly named "Major Repair Line".
- **Scheduled Inspection Line**: New line `I1` (2 bays) of type `MAINTENANCE`.
- **Overhaul Workshop**: New line `O1` (1 bay) of type `MAINTENANCE`.
- **Wheel Profiling Siding**: New line `P1` (1 bay) of type `MAINTENANCE`.
- **Cleaning/Wash Line**: Expand `W1` from 1 bay to 2 bays, named "Washing/Cleaning Line".

*Note on Adjacency*: The existing Neo4j `yard_graph.py` logic automatically wires all position-1 bays to a central `YARD_NECK` and chains higher positions linearly. This star/ladder topology is structurally reasonable for depot layouts and avoids full-mesh arbitrary connections.

*Clarification on Maintenance Scoping*: `MAX_TRAINS_IN_MAINTENANCE = 3` remains strictly scoped to the 3 Major Repair Line (M1) bays in the solver (`model_builder.py`). The new Inspection (I1), Overhaul (O1), and Wheel Profiling (P1) bays are included purely for yard topology and digital-twin richness. They do not increase the solver's `MAINTENANCE` state capacity limit.

### 2. Update Documentation
#### [MODIFY] [WEIGHT_TUNING_NOTES.md](file:///c:/Users/abhig/OneDrive/Desktop/MetGo/LOCKWOOD/WEIGHT_TUNING_NOTES.md)
Append a new section detailing the Muttom yard structural modeling.
- **Sourced from Real Documents**: 15.12 hectares, the presence of specific functional zones (Stabling, Inspection, Overhaul, Major repairs, Wheel-profiling, Wash), and the `MAX_TRAINS_IN_MAINTENANCE=3` limit which corresponds to the 3 Major Repair bays.
- **Estimates**: The exact bay counts for Stabling (26), Inspection (2), Overhaul (1), Wheel Profiling (1), and Wash (2) are structurally reasonable estimates to support a 25-train fleet, as exact track blueprints are not public.

## Verification Plan

### Automated Tests
1. Re-seed the database using `python -m app.seed.seed_fleet`
2. Sync the Neo4j graph using `python -m app.services.yard_graph`
3. Restart Celery and FastAPI servers to pick up the new layout.
4. Run the full pytest suite in `LOCKWOOD/` (`pytest tests/`) to ensure no existing stabling logic or constraints broke with the new functional layout.
5. Run `python test_breakdown_enforcement.py` and `python get_api_response.py` to ensure the solver perfectly handles the new yard geometry without crashing and still satisfies adjacency constraints.
