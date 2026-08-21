import sys
import os
from datetime import date

# Add LOCKWOOD to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "LOCKWOOD")))

from src.models import Train, YardLayout
from src.solver.model_builder import build_model
from src.solver.states import SERVICE, STANDBY, CLEANING, MAINTENANCE, BREAKDOWN
from src.solver.overrides import Override, apply_overrides
from ortools.sat.python import cp_model

def run_stress_test():
    t1 = Train(
        train_id="T01",
        current_bay="W01",
        fitness_cert_expiry=date(2027, 1, 1),
        job_card_severity=None,
        last_cleaned=date(2026, 1, 1),
        branding_hours_this_month=10,
        branding_target_hours=100,
        mileage_total=1000
    )
    
    yard_layout = YardLayout(lines={})
    
    # We will build the model, and then manually add hard constraints blocking ALL normal states
    # to simulate an edge case where a train has no valid operational state.
    model, assign_vars = build_model([t1], yard_layout, overrides=[])
    
    # Force block all normal states
    model.Add(assign_vars[("T01", SERVICE)] == 0)
    model.Add(assign_vars[("T01", STANDBY)] == 0)
    model.Add(assign_vars[("T01", MAINTENANCE)] == 0)
    model.Add(assign_vars[("T01", CLEANING)] == 0)
    
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    print("=== STRESS TEST WITH NO OVERRIDE ===")
    print("Solver Status:", solver.StatusName(status))
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("T01 State:", [s for s in [SERVICE, STANDBY, MAINTENANCE, CLEANING, BREAKDOWN] if solver.Value(assign_vars[("T01", s)]) == 1][0])
    print("Expected: INFEASIBLE (since BREAKDOWN is structurally forbidden and all other states are blocked)\n")
    
    # Now build a model WITH a breakdown override
    print("=== STRESS TEST WITH OVERRIDE ===")
    overrides = [Override("T01", "breakdown")]
    model2, assign_vars2 = build_model([t1], yard_layout, overrides=overrides)
    
    # Apply override (this adds BREAKDOWN == 1)
    apply_overrides(model2, assign_vars2, overrides)
    
    # Also block normal states just to be safe
    model2.Add(assign_vars2[("T01", SERVICE)] == 0)
    model2.Add(assign_vars2[("T01", STANDBY)] == 0)
    model2.Add(assign_vars2[("T01", MAINTENANCE)] == 0)
    model2.Add(assign_vars2[("T01", CLEANING)] == 0)
    
    solver2 = cp_model.CpSolver()
    status2 = solver2.Solve(model2)
    
    print("Solver Status:", solver2.StatusName(status2))
    if status2 in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("T01 State:", [s for s in [SERVICE, STANDBY, MAINTENANCE, CLEANING, BREAKDOWN] if solver2.Value(assign_vars2[("T01", s)]) == 1][0])
    print("Expected: OPTIMAL/FEASIBLE and T01 State: breakdown")

if __name__ == "__main__":
    run_stress_test()
