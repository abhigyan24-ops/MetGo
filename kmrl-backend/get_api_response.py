import requests
import json
import time
import io

with io.open("api_responses.txt", "w", encoding="utf-8") as f:
    f.write("=== BASELINE PLAN GENERATION ===\n")
    res_base = requests.post("http://localhost:8000/plan/generate")
    plan_base = res_base.json()
    f.write(json.dumps(plan_base, indent=2) + "\n")

    f.write("\n=== WHAT-IF T09 BREAKDOWN ===\n")
    res_whatif = requests.post("http://localhost:8000/plan/what-if", json={
        "override": {
            "train_id": "T09",
            "status": "breakdown"
        }
    })
    plan_whatif = res_whatif.json()
    f.write(json.dumps(plan_whatif, indent=2) + "\n")
