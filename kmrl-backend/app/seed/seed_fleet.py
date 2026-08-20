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
    print(f"🏗️  Created Muttom Yard layout: {len(YARD_LAYOUT)} lines, {len(all_bay_ids)} bays")
    
    return all_bay_ids


def generate_trains_with_data(db: Session, available_bays: List[str]) -> None:
    """
    Generate all 25 KMRL trainsets with simulated operational data.
    
    Real parameters: 25 trains, 3 coaches each
    Simulated: certs, job cards, cleaning, branding, yard positions
    """
    
    # Shuffle bays for random assignment
    random.shuffle(available_bays)
    
    trains_needing_critical_jobs = random.sample(range(1, FLEET_SIZE + 1), CRITICAL_JOB_CARD_COUNT)
    trains_expiring_soon = random.sample(
        [t for t in range(1, FLEET_SIZE + 1) if t not in trains_needing_critical_jobs],
        CERT_EXPIRING_SOON_COUNT
    )
    
    today = date.today()
    
    for i in range(1, FLEET_SIZE + 1):
        train_id = f"T{i:02d}"
        
        # Assign a yard bay (first 25 bays)
        current_bay = available_bays[i - 1] if i <= len(available_bays) else None
        
        # Random mileage
        mileage = random.uniform(MILEAGE_MIN_KM, MILEAGE_MAX_KM)
        
        # Create train
        train = Train(
            train_id=train_id,
            coach_count=COACHES_PER_TRAIN,
            current_bay_id=current_bay,
            mileage_km=mileage,
            status=TrainStatus.AVAILABLE,
        )
        db.add(train)
        db.flush()  # Flush to get train in session for FK relationships
        
        # ---------------------------------------------------------------------------
        # Fitness Certificate
        # ---------------------------------------------------------------------------
        if i in trains_expiring_soon:
            # Cert expires in 1-7 days (demo impact)
            days_to_expiry = random.randint(1, 7)
        else:
            # Normal cert: expires in 30-90 days
            days_to_expiry = random.randint(CERT_MIN_DAYS, CERT_MAX_DAYS)
        
        expiry_date = today + timedelta(days=days_to_expiry)
        issued_date = expiry_date - timedelta(days=365)  # Cert valid for 1 year
        
        cert = FitnessCert(
            train_id=train_id,
            cert_ref=f"FC-{train_id}-2026",
            issued_date=issued_date,
            expiry_date=expiry_date,
            is_active=True,
        )
        db.add(cert)
        
        # ---------------------------------------------------------------------------
        # Job Cards
        # ---------------------------------------------------------------------------
        if i in trains_needing_critical_jobs:
            # Critical job card — forces hard constraint maintenance assignment
            jc = JobCard(
                jc_ref=f"JC-{100 + i}",
                train_id=train_id,
                description="Critical pantograph inspection overdue — service prohibited",
                status=JobCardStatus.OPEN,
                severity=JobCardSeverity.CRITICAL,
            )
            db.add(jc)
            train.status = TrainStatus.MAINTENANCE
        
        elif random.random() < JOB_CARD_PROBABILITY:
            # Non-critical job card
            severity = random.choice([JobCardSeverity.MAJOR, JobCardSeverity.MINOR])
            descriptions = {
                JobCardSeverity.MAJOR: [
                    "HVAC system efficiency below target",
                    "Door mechanism requires adjustment",
                    "Brake pad wear approaching service limit",
                ],
                JobCardSeverity.MINOR: [
                    "Interior lighting panel replacement scheduled",
                    "Passenger information display pixel fault",
                    "Seat cushion replacement due",
                ],
            }
            
            jc = JobCard(
                jc_ref=f"JC-{200 + i}",
                train_id=train_id,
                description=random.choice(descriptions[severity]),
                status=JobCardStatus.OPEN,
                severity=severity,
            )
            db.add(jc)
        
        # ---------------------------------------------------------------------------
        # Cleaning Schedule
        # ---------------------------------------------------------------------------
        if random.random() < CLEANING_DUE_PROBABILITY:
            # Cleaning scheduled for tonight
            cleaning = CleaningSlot(
                train_id=train_id,
                scheduled_at=datetime.utcnow() + timedelta(hours=2),
                completed=False,
            )
            db.add(cleaning)
        
        # ---------------------------------------------------------------------------
        # Branding Contract
        # ---------------------------------------------------------------------------
        if random.random() < BRANDING_CONTRACT_PROBABILITY:
            # Under-delivered branding contract (soft constraint: prefer service)
            hours_target = random.uniform(10.0, 15.0)
            hours_delivered = hours_target * random.uniform(0.5, 0.9)  # 50-90% delivered
            
            branding = BrandingContract(
                train_id=train_id,
                contract_ref=f"BRAND-{train_id}-2026",
                advertiser=random.choice([
                    "Kerala Tourism",
                    "Lulu Mall",
                    "Federal Bank",
                    "Malabar Gold",
                    "Wonderla",
                ]),
                start_date=today - timedelta(days=60),
                end_date=today + timedelta(days=30),
                hours_target=hours_target,
                hours_delivered=hours_delivered,
                is_active=True,
            )
            db.add(branding)
    
    # Update bay occupancy
    for i in range(1, FLEET_SIZE + 1):
        train_id = f"T{i:02d}"
        bay_id = available_bays[i - 1] if i <= len(available_bays) else None
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
    
    print(f"✅ Generated {total_trains} trains with:")
    print(f"   • {critical_count} trains with CRITICAL job cards (→ maintenance)")
    print(f"   • {expiring_count} trains with certs expiring within 7 days")
    print(f"   • {branding_count} trains under active branding contracts")
    print(f"   • {cleaning_count} trains with cleaning due")


def print_fleet_summary(db: Session) -> None:
    """Print a human-readable summary of the seeded fleet."""
    
    print("\n" + "=" * 80)
    print("KMRL FLEET SUMMARY — 25 Trainsets (Alstom Metropolis, 3 coaches each)")
    print("=" * 80)
    
    trains = db.query(Train).order_by(Train.train_id).all()
    
    for train in trains:
        cert = train.latest_fitness_cert
        cert_status = f"{cert.days_to_expiry}d" if cert else "NONE"
        if cert and cert.days_to_expiry <= 7:
            cert_status = f"⚠️  {cert_status}"
        
        critical_jobs = [jc for jc in train.job_cards if jc.severity == JobCardSeverity.CRITICAL and jc.status == JobCardStatus.OPEN]
        job_status = f"🔴 CRITICAL x{len(critical_jobs)}" if critical_jobs else "✓"
        
        branding_active = any(bc.is_active for bc in train.branding_contracts)
        branding_marker = "🎨" if branding_active else "  "
        
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
        
        print("\n✅ Fleet seeding complete!")
        print("   Next: Start the services with `docker-compose up -d`")
        print("   Then: Run migrations with `alembic upgrade head`")
        print("   Finally: Start API with `uvicorn app.main:app --reload`")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
