"""
Smoke-test: verify MIN_SERVICE_TRAINS is a genuine hard constraint,
not a soft preference. Constructs a minimal fleet where critical job
cards block enough trains that the floor cannot be met, and asserts
the solver returns INFEASIBLE (not a degraded feasible plan).
"""
import sys
from pathlib import Path
from datetime import date

# Resolve Lockwood path
for parent in Path(__file__).resolve().parents:
    candidate = parent / "LOCKWOOD"
    if candidate.exists() and (candidate / "src").exists():
        sys.path.insert(0, str(candidate))
        break

from ortools.sat.python import cp_model
from src.constants import MIN_SERVICE_TRAINS
from src.models import Train, YardLayout, YardLine
from src.solver.model_builder import build_model

future_date = date(2030, 1, 1)
n = MIN_SERVICE_TRAINS + 2  # fleet slightly larger than floor, but all blocked

# All trains have critical job cards => none can go to SERVICE
trains = [
    Train(
        train_id=f"T{i:02d}",
        fitness_cert_expiry=future_date,
        last_cleaned=date(2026, 1, 1),
        branding_hours_this_month=0,
        branding_target_hours=60,
        current_bay=f"B{i:02d}",
        mileage_total=10000,
        job_card_severity="critical",
    )
    for i in range(1, n + 1)
]

# Minimal yard: single line with enough bays
yard = YardLayout(lines={
    "L1": YardLine(
        line_id="L1",
        bay_order=[f"B{i:02d}" for i in range(1, n + 1)]
    )
})

model, assign_vars = build_model(trains, yard)
solver = cp_model.CpSolver()
status = solver.Solve(model)

print(f"Fleet size: {n} trains, all blocked by critical job cards")
print(f"MIN_SERVICE_TRAINS floor = {MIN_SERVICE_TRAINS}")
print(f"Solver status = {solver.StatusName(status)}")
assert status not in (cp_model.OPTIMAL, cp_model.FEASIBLE), (
    f"FAIL: solver should have returned INFEASIBLE but got {solver.StatusName(status)}"
)
print("PASS: solver correctly returned INFEASIBLE — hard constraint is genuine, not soft")
