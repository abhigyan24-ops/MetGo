import urllib.request
import json
import sys
from pathlib import Path

# Resolve Lockwood and confirm MIN_SERVICE_TRAINS
for parent in Path(__file__).resolve().parents:
    candidate = parent / "LOCKWOOD"
    if candidate.exists() and (candidate / "src").exists():
        sys.path.insert(0, str(candidate))
        break

from src.constants import MIN_SERVICE_TRAINS
print(f"Active MIN_SERVICE_TRAINS = {MIN_SERVICE_TRAINS}")
print()

# Test 1: baseline plan
req = urllib.request.Request('http://localhost:8000/plan/generate', method='POST')
with urllib.request.urlopen(req) as resp:
    plan = json.loads(resp.read().decode())

service = [a for a in plan['assignments'] if a['state'] == 'service']
standby = [a for a in plan['assignments'] if a['state'] == 'standby']
maint   = [a for a in plan['assignments'] if a['state'] == 'maintenance']
clean   = [a for a in plan['assignments'] if a['state'] == 'cleaning']

print('=== BASELINE PLAN ===')
print('Plan ID:', plan['plan_id'])
print(f'Service   ({len(service)}): {[a["train_id"] for a in service]}')
print(f'Standby   ({len(standby)}): {[a["train_id"] for a in standby]}')
print(f'Maintenance ({len(maint)}): {[a["train_id"] for a in maint]}')
print(f'Cleaning  ({len(clean)}): {[a["train_id"] for a in clean]}')
print(f'Hard floor (MIN_SERVICE_TRAINS={MIN_SERVICE_TRAINS}) satisfied: {len(service) >= MIN_SERVICE_TRAINS}')
if len(service) < MIN_SERVICE_TRAINS:
    print(f'  *** SHORTFALL: {MIN_SERVICE_TRAINS - len(service)} trains short of floor ***')

print()

# Test 2: what-if T09 breakdown
payload = json.dumps({'override': {'train_id': 'T09', 'status': 'breakdown'}}).encode()
req2 = urllib.request.Request(
    'http://localhost:8000/plan/what-if',
    data=payload,
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    with urllib.request.urlopen(req2) as resp:
        plan2 = json.loads(resp.read().decode())
    service2 = [a for a in plan2['assignments'] if a['state'] == 'service']
    t09 = next(a for a in plan2['assignments'] if a['train_id'] == 'T09')
    print('=== WHAT-IF: T09 BREAKDOWN ===')
    print('Plan ID:', plan2['plan_id'])
    print(f'Service count: {len(service2)} (floor={MIN_SERVICE_TRAINS}, satisfied={len(service2) >= MIN_SERVICE_TRAINS})')
    print(f'T09: state={t09["state"]}, reason={t09["reason"]!r}, constraint_type={t09["constraint_type"]!r}')
    if len(service2) < MIN_SERVICE_TRAINS:
        print(f'  *** SHORTFALL: {MIN_SERVICE_TRAINS - len(service2)} trains short of floor ***')
except Exception as e:
    print('=== WHAT-IF: T09 BREAKDOWN ===')
    print(f'RESULT: INFEASIBLE or ERROR — {e}')
    print('(This is the correct behavior if removing T09 from service cannot satisfy floor)')
