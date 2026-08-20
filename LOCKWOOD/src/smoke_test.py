"""
Minimal OR-Tools CP-SAT smoke test.

Purpose: verify that OR-Tools is installed correctly and the CP-SAT
solver runs successfully in this environment, BEFORE any real train
induction planning logic is built on top of it (that starts in
Part 1b). This script has no connection to the actual train problem.
"""

from ortools.sat.python import cp_model


def run_smoke_test() -> bool:
    """
    Builds and solves a trivial 2-variable constraint problem.
    Returns True if the solver ran successfully and found a solution,
    False otherwise.
    """
    model = cp_model.CpModel()

    x = model.NewBoolVar("x")
    y = model.NewBoolVar("y")
    model.Add(x + y == 1)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print(
            f"OR-Tools CP-SAT is working correctly. "
            f"x={solver.Value(x)}, y={solver.Value(y)}, "
            f"status={solver.StatusName(status)}"
        )
        return True

    print("Smoke test FAILED — solver did not find a feasible solution.")
    return False


if __name__ == "__main__":
    success = run_smoke_test()
    if not success:
        raise SystemExit(1)
