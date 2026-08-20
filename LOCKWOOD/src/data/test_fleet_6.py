"""
Hand-written 6-train test dataset — UPDATED IN PART 3a for the
multi-line yard redesign.

The yard is now 2 small lines instead of 1: "LA" (3 bays: A1, A2, A3)
and "LB" (3 bays: B1, B2, B3). The 6 trains split evenly, 3 per line.
All certificate, cleaning, branding, and mileage values are IDENTICAL
to the original Part 1a dataset — only current_bay (now a bay_id
string) and the job-card field (now job_card_severity) have changed.

Edge cases preserved:
  - KMRL-02: expired fitness certificate.
  - KMRL-03: job_card_severity="critical" (was open_job_cards=1) —
    must still never be assigned service.
  - KMRL-05: certificate expires the day AFTER PLANNING_DATE (boundary
    case).

New edge case this task proves: KMRL-01 (Line A, entrance, index 0)
and KMRL-06 (Line B, deepest, index 2) are on DIFFERENT lines and must
NOT block each other — under the old single-line model they would
have.
"""

from datetime import date

from src.constants import PLANNING_DATE
from src.models import Train, YardLine, YardLayout

TEST_FLEET_6 = [
    Train(
        train_id="KMRL-01",
        fitness_cert_expiry=date(2026, 11, 20),
        job_card_severity=None,
        last_cleaned=date(2026, 8, 10),
        branding_hours_this_month=45,
        branding_target_hours=60,
        current_bay="A1",
        mileage_total=182000,
    ),
    Train(
        train_id="KMRL-02",
        fitness_cert_expiry=date(2026, 8, 1),  # EXPIRED before planning date
        job_card_severity=None,
        last_cleaned=date(2026, 8, 12),
        branding_hours_this_month=30,
        branding_target_hours=60,
        current_bay="A2",
        mileage_total=210500,
    ),
    Train(
        train_id="KMRL-03",
        fitness_cert_expiry=date(2026, 12, 1),
        job_card_severity="critical",  # must never be assigned service
        last_cleaned=date(2026, 8, 9),
        branding_hours_this_month=52,
        branding_target_hours=60,
        current_bay="A3",
        mileage_total=175300,
    ),
    Train(
        train_id="KMRL-04",
        fitness_cert_expiry=date(2026, 9, 5),
        job_card_severity=None,
        last_cleaned=date(2026, 8, 11),
        branding_hours_this_month=60,
        branding_target_hours=60,
        current_bay="B1",
        mileage_total=198700,
    ),
    Train(
        train_id="KMRL-05",
        fitness_cert_expiry=date(2026, 8, 16),  # expires day AFTER planning date
        job_card_severity=None,
        last_cleaned=date(2026, 8, 13),
        branding_hours_this_month=15,
        branding_target_hours=60,
        current_bay="B2",
        mileage_total=205900,
    ),
    Train(
        train_id="KMRL-06",
        fitness_cert_expiry=date(2026, 10, 10),
        job_card_severity=None,
        last_cleaned=date(2026, 8, 1),  # most overdue for cleaning in the fleet
        branding_hours_this_month=38,
        branding_target_hours=60,
        current_bay="B3",
        mileage_total=190100,
    ),
]

TEST_YARD_LAYOUT_6 = YardLayout(lines={
    "LA": YardLine(line_id="LA", bay_order=["A1", "A2", "A3"]),
    "LB": YardLine(line_id="LB", bay_order=["B1", "B2", "B3"]),
})
