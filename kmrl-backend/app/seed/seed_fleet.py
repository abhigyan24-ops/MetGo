"""
Generate 25 realistic KMRL trainsets with simulated operational data.

REAL PARAMETERS (verified KMRL data):
  - Fleet size: 25 trainsets (Alstom Metropolis)
  - Configuration: 3 coaches per trainset

SIMULATED DATA (internal KMRL operations data — not publicly available):
  - Fitness certificate expiry dates (spread 30-90 days, 2-3 close to expiry)
  - Job cards / maintenance work orders (mostly clean, 1-2 critical)
  - Cleaning schedules
  - Branding contracts (subset of trains)
  - Yard bay positions (Muttom Yard layout)

This simulation mirrors what KMRL's real internal systems would produce.

Usage:
  python -m app.seed.seed_fleet
"""

import sys
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List

from sqlalchemy.orm import Session

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.session import SessionLocal
from app.models.train import (
    Train, FitnessCert, JobCard, CleaningSlot, BrandingContract,
    TrainStatus, JobCardStatus, JobCardSeverity,
)
from app.models.yard import YardLine, YardBay, BayType
from app.models.plan import PlanAssignment, ShuntMove, InductionPlan
from app.models.timeseries import MileageSnapshot, CertEvent


# ---------------------------------------------------------------------------
# Simulation parameters
# ---------------------------------------------------------------------------

FLEET_SIZE = 25  # Real KMRL fleet size
COACHES_PER_TRAIN = 3  # Real KMRL configuration (Alstom Metropolis)

# Fitness cert expiry distribution
CERT_MIN_DAYS = 30
CERT_MAX_DAYS = 90
CERT_EXPIRING_SOON_COUNT = 3  # Trains with cert expiring in < 7 days (demo impact)

# Job card distribution
JOB_CARD_PROBABILITY = 0.30  # 30% of trains have at least one job card
CRITICAL_JOB_CARD_COUNT = 2  # Trains with open critical job cards (forces maintenance)

# Branding contract distribution
BRANDING_CONTRACT_PROBABILITY = 0.40  # 40% of trains under branding contracts

# Cleaning schedule
CLEANING_DUE_PROBABILITY = 0.20  # 20% of trains have cleaning due tonight

# Mileage distribution (realistic spread for a metro fleet)
MILEAGE_MIN_KM = 30000
MILEAGE_MAX_KM = 65000


# ---------------------------------------------------------------------------
# Muttom Yard layout (SIMULATED — real layout is internal KMRL data)
# ---------------------------------------------------------------------------

YARD_LAYOUT = {
    # 5 stabling roads
    "L1": {"name": "Stabling Road 1", "bays": 6, "type": BayType.STABLING},
    "L2": {"name": "Stabling Road 2", "bays": 6, "type": BayType.STABLING},
    "L3": {"name": "Stabling Road 3", "bays": 5, "type": BayType.STABLING},
    "L4": {"name": "Stabling Road 4", "bays": 5, "type": BayType.STABLING},
    "L5": {"name": "Stabling Road 5", "bays": 4, "type": BayType.STABLING},
    
    # 1 maintenance track
    "M1": {"name": "Maintenance Track", "bays": 3, "type": BayType.MAINTENANCE},
    
    # 1 wash track
    "W1": {"name": "Wash Bay", "bays": 1, "type": BayType.WASH},
}


def clear_all_fleet_data(db: Session) -> None:
    """Clear all fleet, plan, yard, and related time-series data in correct FK order."""
    db.query(PlanAssignment).delete()
    db.query(ShuntMove).delete()
    db.query(InductionPlan).delete()
    db.query(MileageSnapshot).delete()
    db.query(CertEvent).delete()
    db.query(FitnessCert).delete()
    db.query(JobCard).delete()
    db.query(CleaningSlot).delete()
    db.query(BrandingContract).delete()
    # Break circular FK between YardBay.occupied_by and Train.current_bay_id
    db.query(YardBay).update({YardBay.occupied_by: None})
    db.query(Train).update({Train.current_bay_id: None})
    db.flush()
    db.query(Train).delete()
    db.query(YardBay).delete()
    db.query(YardLine).delete()
    db.commit()


def seed_yard_layout(db: Session) -> List[str]:
    """
    Create the Muttom Yard layout in Postgres.
    Returns a list of all bay IDs for train placement.
    
    SIMULATED layout: ~4-6 stabling lines × 4-6 bays each, plus maintenance and wash.
    Position 1 = entrance end (easiest to pull out), higher positions require shunting.
    """
    all_bay_ids = []
    bay_counter = 1
    
    for line_id, config in YARD_LAYOUT.items():
        # Create line
        line = YardLine(
            line_id=line_id,
            line_name=config["name"],
            bay_count=config["bays"],
            line_type=config["type"],
        )
        db.add(line)
        
        # Create bays for this line
        for position in range(1, config["bays"] + 1):
            if line_id.startswith("M"):
                bay_id = f"M{position:02d}"
            elif line_id.startswith("W"):
                bay_id = f"W{position:02d}"
            else:
                bay_id = f"B{bay_counter:02d}"
                bay_counter += 1
            
            bay = YardBay(
                bay_id=bay_id,
                line_id=line_id,
                position=position,
                bay_type=config["type"],
                is_active=True,
                occupied_by=None,  # Will be populated when trains are created
            )
            db.add(bay)
            all_bay_ids.append(bay_id)
    
    db.commit()
    print(f"[OK] Created Muttom Yard layout: {len(YARD_LAYOUT)} lines, {len(all_bay_ids)} bays")
    
    return all_bay_ids


def generate_trains_with_data(db: Session, available_bays: List[str]) -> None:
    """
    Generate all 25 KMRL trainsets with balanced, realistic operational data.
    
    Real parameters: 25 trains, 3 coaches each
    Balanced distribution:
      - 2 Critical job cards (T04, T12 -> Maintenance)
      - 1 Expired fitness cert (T09 -> Cannot service)
      - 2 Expiring soon certs (T05 in 3d, T17 in 5d)
      - 2 Cleaning due tonight (T08, T21 -> Cleaning bay)
      - 1 Major job card (T19 -> Soft maintenance preference)
      - 2 Minor job cards (T10, T15 -> OK for service)
      - 8 Active branding contracts with delivery shortfall (T01, T02, T07, T11, T14, T18, T22, T25 -> Service priority)
      - Rest healthy & available (leading to ~16 Service, ~4 Standby, ~3 Maintenance, ~2 Cleaning)
    """
    today = date.today()

    # Pre-planned designated roles for balanced demo and operations
    critical_job_trains = {
        4: "Critical pantograph inspection overdue — service prohibited",
        12: "Traction motor insulation resistance low — critical safety block",
    }
    expired_cert_trains = [9]         # Expired 3 days ago
    expiring_soon_trains = {5: 3, 17: 5} # (train_num: days_to_expiry)
    cleaning_due_trains = [8, 21]
    major_job_trains = {19: "HVAC compressor efficiency degraded — major service"}
    minor_job_trains = {
        10: "Interior LED display panel pixel fault",
        15: "Driver cabin seat height adjustment sticking",
    }
    branding_trains = {
        1: ("Kerala Tourism", 15.0, 8.5),
        2: ("Lulu Mall Kochi", 14.0, 7.0),
        7: ("Federal Bank", 12.0, 6.0),
        11: ("Malabar Gold", 15.0, 9.0),
        14: ("Wonderla Amusement Park", 10.0, 4.0),
        18: ("Muthoot Finance", 12.0, 7.5),
        22: ("Cochin Shipyard", 14.0, 8.0),
        25: ("Kalyan Silks", 15.0, 9.5),
    }

    # Deterministic yard bay allocation for realistic stabling
    # available_bays contains Stabling (B01-B26), Maintenance (M01-M03), Wash (W01)
    stabling_bays = [b for b in available_bays if b.startswith('B')]
    maint_bays = [b for b in available_bays if b.startswith('M')]
    wash_bays = [b for b in available_bays if b.startswith('W')]
    
    # Assign bays: Put maintenance trains in M bays or front stabling, wash in W bays, rest in stabling
    bay_map = {}
    stabling_idx = 0
    maint_idx = 0
    wash_idx = 0

    for i in range(1, FLEET_SIZE + 1):
        if i in critical_job_trains and maint_idx < len(maint_bays):
            bay_map[i] = maint_bays[maint_idx]
            maint_idx += 1
        elif i in cleaning_due_trains and wash_idx < len(wash_bays):
            bay_map[i] = wash_bays[wash_idx]
            wash_idx += 1
        elif stabling_idx < len(stabling_bays):
            bay_map[i] = stabling_bays[stabling_idx]
            stabling_idx += 1
        else:
            bay_map[i] = available_bays[i - 1]

    for i in range(1, FLEET_SIZE + 1):
        train_id = f"T{i:02d}"
        current_bay = bay_map.get(i)

        # Realistic mileage curve (30,000 km to 65,000 km)
        base_mileage = 35000 + (i * 1150) % 28000
        if i in [10, 16, 23, 24]: # higher mileage trains
            base_mileage += 8000

        train = Train(
            train_id=train_id,
            coach_count=COACHES_PER_TRAIN,
            current_bay_id=current_bay,
            mileage_km=float(base_mileage),
            status=TrainStatus.AVAILABLE if i not in critical_job_trains else TrainStatus.MAINTENANCE,
        )
        db.add(train)
        db.flush()

        # 1. Fitness Certificate
        if i in expired_cert_trains:
            expiry_date = today - timedelta(days=3)
        elif i in expiring_soon_trains:
            expiry_date = today + timedelta(days=expiring_soon_trains[i])
        else:
            expiry_date = today + timedelta(days=30 + ((i * 7) % 60))
        
        issued_date = expiry_date - timedelta(days=365)
        cert = FitnessCert(
            train_id=train_id,
            cert_ref=f"FC-{train_id}-2026",
            issued_date=issued_date,
            expiry_date=expiry_date,
            is_active=True,
        )
        db.add(cert)

        # 2. Job Cards
        if i in critical_job_trains:
            jc = JobCard(
                jc_ref=f"JC-{100 + i}",
                train_id=train_id,
                description=critical_job_trains[i],
                status=JobCardStatus.OPEN,
                severity=JobCardSeverity.CRITICAL,
            )
            db.add(jc)
        elif i in major_job_trains:
            jc = JobCard(
                jc_ref=f"JC-{200 + i}",
                train_id=train_id,
                description=major_job_trains[i],
                status=JobCardStatus.OPEN,
                severity=JobCardSeverity.MAJOR,
            )
            db.add(jc)
        elif i in minor_job_trains:
            jc = JobCard(
                jc_ref=f"JC-{300 + i}",
                train_id=train_id,
                description=minor_job_trains[i],
                status=JobCardStatus.OPEN,
                severity=JobCardSeverity.MINOR,
            )
            db.add(jc)

        # 3. Cleaning Schedule
        if i in cleaning_due_trains:
            # Overdue cleaning: scheduled for tonight, last completed 4-5 days ago
            cleaning = CleaningSlot(
                train_id=train_id,
                scheduled_at=datetime.utcnow() + timedelta(hours=2),
                completed=False,
            )
            db.add(cleaning)
        else:
            # Recently cleaned 1-2 days ago
            last_clean_days = 1 if i % 2 == 0 else 2
            cleaning = CleaningSlot(
                train_id=train_id,
                scheduled_at=datetime.utcnow() - timedelta(days=last_clean_days),
                completed_at=today - timedelta(days=last_clean_days),
                completed=True,
            )
            db.add(cleaning)

        # 4. Branding Contract
        if i in branding_trains:
            advertiser, target_h, delivered_h = branding_trains[i]
            branding = BrandingContract(
                train_id=train_id,
                contract_ref=f"BRAND-{train_id}-2026",
                advertiser=advertiser,
                start_date=today - timedelta(days=45),
                end_date=today + timedelta(days=45),
                hours_target=target_h,
                hours_delivered=delivered_h,
                is_active=True,
            )
            db.add(branding)

    # Update bay occupancy
    for i in range(1, FLEET_SIZE + 1):
        train_id = f"T{i:02d}"
        bay_id = bay_map.get(i)
        if bay_id:
            db.query(YardBay).filter(YardBay.bay_id == bay_id).update({"occupied_by": train_id})

    db.commit()
    
    # Summary
    total_trains = db.query(Train).count()
    critical_count = db.query(JobCard).filter(
        JobCard.status == JobCardStatus.OPEN,
        JobCard.severity == JobCardSeverity.CRITICAL
    ).count()
    expiring_count = db.query(FitnessCert).filter(
        FitnessCert.is_active == True,
        FitnessCert.expiry_date <= today + timedelta(days=7)
    ).count()
    branding_count = db.query(BrandingContract).filter(BrandingContract.is_active == True).count()
    cleaning_count = db.query(CleaningSlot).filter(CleaningSlot.completed == False).count()
    
    print(f"[OK] Generated {total_trains} trains with:")
    print(f"   * {critical_count} trains with CRITICAL job cards (-> maintenance)")
    print(f"   * {expiring_count} trains with certs expiring within 7 days")
    print(f"   * {branding_count} trains under active branding contracts")
    print(f"   * {cleaning_count} trains with cleaning due")


def print_fleet_summary(db: Session) -> None:
    """Print a human-readable summary of the seeded fleet."""
    
    print("\n" + "=" * 80)
    print("KMRL FLEET SUMMARY -- 25 Trainsets (Alstom Metropolis, 3 coaches each)")
    print("=" * 80)
    
    trains = db.query(Train).order_by(Train.train_id).all()
    
    for train in trains:
        cert = train.latest_fitness_cert
        cert_status = f"{cert.days_to_expiry}d" if cert else "NONE"
        if cert and cert.days_to_expiry <= 7:
            cert_status = f"[!] {cert_status}"
        
        critical_jobs = [jc for jc in train.job_cards if jc.severity == JobCardSeverity.CRITICAL and jc.status == JobCardStatus.OPEN]
        job_status = f"[CRITICAL x{len(critical_jobs)}]" if critical_jobs else "[OK]"
        
        branding_active = any(bc.is_active for bc in train.branding_contracts)
        branding_marker = "[BRAND]" if branding_active else "       "
        
        print(
            f"{train.train_id}  Bay:{train.current_bay_id or 'N/A':4s}  "
            f"Cert:{cert_status:8s}  Jobs:{job_status:20s}  "
            f"{branding_marker}  {train.mileage_km:>7.0f}km"
        )
    
    print("=" * 80)


def main():
    """Main entry point."""
    
    print("=" * 80)
    print("KMRL Fleet Data Seeder (SIMULATED)")
    print("=" * 80)
    print("Real parameters: 25 trainsets, 3 coaches each (Alstom Metropolis)")
    print("Simulated: certs, job cards, cleaning, branding, yard layout")
    print("(Maintenance/yard data is internal KMRL data, not publicly available)")
    print("=" * 80)
    print()
    
    db = SessionLocal()
    try:
        # Step 0: Clear existing data in correct FK order
        print("Step 0: Clearing existing fleet and yard data...")
        clear_all_fleet_data(db)

        # Step 1: Create yard layout
        print("Step 1: Creating Muttom Yard layout...")
        available_bays = seed_yard_layout(db)
        
        # Step 2: Generate trains
        print("\nStep 2: Generating 25 trainsets with operational data...")
        generate_trains_with_data(db, available_bays)
        
        # Step 3: Summary
        print_fleet_summary(db)
        
        print("\n[OK] Fleet seeding complete!")
        print("   Next: Start the services with `docker-compose up -d`")
        print("   Then: Run migrations with `alembic upgrade head`")
        print("   Finally: Start API with `uvicorn app.main:app --reload`")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
