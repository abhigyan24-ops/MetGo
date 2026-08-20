"""
Train fleet models.

Fleet size (25 trainsets) and train configuration (3 coaches each, Alstom Metropolis)
are real KMRL operational parameters.

Fitness certificates, job cards, cleaning slots, and branding contracts are
SIMULATED — this data is internal to KMRL and not publicly available.
The simulation mirrors the shape KMRL's real systems would produce.
"""

import enum
from datetime import date, datetime

from sqlalchemy import (
    Column, String, Integer, Float, Boolean,
    Date, DateTime, ForeignKey, Enum as SAEnum, Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class TrainStatus(str, enum.Enum):
    """Operational status of a trainset at planning time."""
    AVAILABLE   = "available"
    MAINTENANCE = "maintenance"
    SERVICE     = "service"
    STANDBY     = "standby"
    BREAKDOWN   = "breakdown"
    CLEANING    = "cleaning"


class JobCardStatus(str, enum.Enum):
    OPEN   = "open"
    CLOSED = "closed"


class JobCardSeverity(str, enum.Enum):
    """
    critical  → hard constraint; legally blocks service assignment
    major     → soft constraint; strongly discourages service
    minor     → informational; no scheduling impact
    """
    CRITICAL = "critical"
    MAJOR    = "major"
    MINOR    = "minor"


# ---------------------------------------------------------------------------
# Train
# ---------------------------------------------------------------------------

class Train(Base):
    __tablename__ = "trains"

    # T01 – T25 (matches the real 25-trainset KMRL fleet)
    train_id = Column(String(10), primary_key=True, index=True)

    # Alstom Metropolis — 3 coaches per trainset (real parameter)
    coach_count = Column(Integer, default=3, nullable=False)

    # Current yard position (foreign key to YardBay)
    current_bay_id = Column(String(10), ForeignKey("yard_bays.bay_id"), nullable=True)

    # Accumulated mileage in km (simulated realistic spread across fleet)
    mileage_km = Column(Float, default=0.0, nullable=False)

    # Computed/cached status — updated by the planning engine
    status = Column(SAEnum(TrainStatus), default=TrainStatus.AVAILABLE, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    fitness_certs    = relationship("FitnessCert",      back_populates="train", cascade="all, delete-orphan")
    job_cards        = relationship("JobCard",           back_populates="train", cascade="all, delete-orphan")
    cleaning_slots   = relationship("CleaningSlot",      back_populates="train", cascade="all, delete-orphan")
    branding_contracts = relationship("BrandingContract", back_populates="train", cascade="all, delete-orphan")
    current_bay      = relationship("YardBay",           foreign_keys=[current_bay_id])

    @property
    def has_critical_job_card(self) -> bool:
        return any(
            jc.status == JobCardStatus.OPEN and jc.severity == JobCardSeverity.CRITICAL
            for jc in self.job_cards
        )

    @property
    def latest_fitness_cert(self) -> "FitnessCert | None":
        active = [c for c in self.fitness_certs if c.is_active]
        return max(active, key=lambda c: c.expiry_date) if active else None

    def __repr__(self) -> str:
        return f"<Train {self.train_id} status={self.status.value}>"


# ---------------------------------------------------------------------------
# FitnessCert
# ---------------------------------------------------------------------------

class FitnessCert(Base):
    """
    Fitness certificate per trainset.

    SIMULATED data — expiry dates are spread across the next 30–90 days
    with 2–3 trains deliberately close to expiry for demo impact.
    """
    __tablename__ = "fitness_certs"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    train_id  = Column(String(10), ForeignKey("trains.train_id"), nullable=False, index=True)
    cert_ref  = Column(String(30), nullable=False)        # e.g. "FC-T09-2026"
    issued_date  = Column(Date, nullable=False)
    expiry_date  = Column(Date, nullable=False)
    is_active    = Column(Boolean, default=True, nullable=False)

    train = relationship("Train", back_populates="fitness_certs")

    @property
    def days_to_expiry(self) -> int:
        return (self.expiry_date - date.today()).days

    @property
    def is_expiring_soon(self) -> bool:
        """True if expiry is within 7 days — triggers a soft constraint."""
        return 0 <= self.days_to_expiry <= 7

    @property
    def is_expired(self) -> bool:
        return self.days_to_expiry < 0

    def __repr__(self) -> str:
        return f"<FitnessCert {self.cert_ref} expires={self.expiry_date}>"


# ---------------------------------------------------------------------------
# JobCard
# ---------------------------------------------------------------------------

class JobCard(Base):
    """
    Maintenance job / work order per trainset.

    SIMULATED — most trains have no open job cards; a handful have open
    non-critical cards; 1–2 have open critical cards (hard constraint).
    """
    __tablename__ = "job_cards"

    id       = Column(Integer, primary_key=True, autoincrement=True)
    jc_ref   = Column(String(20), nullable=False, unique=True)    # e.g. "JC-114"
    train_id = Column(String(10), ForeignKey("trains.train_id"), nullable=False, index=True)

    description = Column(Text, nullable=False)
    status      = Column(SAEnum(JobCardStatus),   default=JobCardStatus.OPEN,     nullable=False)
    severity    = Column(SAEnum(JobCardSeverity), default=JobCardSeverity.MINOR,   nullable=False)

    raised_at  = Column(DateTime(timezone=True), server_default=func.now())
    closed_at  = Column(DateTime(timezone=True), nullable=True)

    train = relationship("Train", back_populates="job_cards")

    def __repr__(self) -> str:
        return f"<JobCard {self.jc_ref} [{self.severity.value}/{self.status.value}]>"


# ---------------------------------------------------------------------------
# CleaningSlot
# ---------------------------------------------------------------------------

class CleaningSlot(Base):
    """
    Cleaning schedule record per trainset.

    SIMULATED — tracks whether a train requires cleaning before its next
    service assignment. Cleaning is a soft constraint in the planner.
    """
    __tablename__ = "cleaning_slots"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    train_id   = Column(String(10), ForeignKey("trains.train_id"), nullable=False, index=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    completed    = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    notes        = Column(Text, nullable=True)

    train = relationship("Train", back_populates="cleaning_slots")

    def __repr__(self) -> str:
        return f"<CleaningSlot train={self.train_id} done={self.completed}>"


# ---------------------------------------------------------------------------
# BrandingContract
# ---------------------------------------------------------------------------

class BrandingContract(Base):
    """
    Advertisement / branding wrap contract per trainset.

    SIMULATED — tracks target vs. delivered service hours under a branding
    contract. Under-delivery is a soft constraint: prefer assigning this
    train to service to meet the contract hours target.
    """
    __tablename__ = "branding_contracts"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    train_id     = Column(String(10), ForeignKey("trains.train_id"), nullable=False, index=True)
    contract_ref = Column(String(30), nullable=False)    # e.g. "BRAND-T14-2026"
    advertiser   = Column(String(100), nullable=True)
    start_date   = Column(Date, nullable=False)
    end_date     = Column(Date, nullable=False)

    # Hours-delivered vs. hours-target fields (used for soft constraint)
    hours_target    = Column(Float, nullable=False, default=0.0)
    hours_delivered = Column(Float, nullable=False, default=0.0)

    is_active = Column(Boolean, default=True, nullable=False)

    train = relationship("Train", back_populates="branding_contracts")

    @property
    def hours_remaining(self) -> float:
        return max(0.0, self.hours_target - self.hours_delivered)

    @property
    def is_under_target(self) -> bool:
        return self.hours_delivered < self.hours_target

    def __repr__(self) -> str:
        return (
            f"<BrandingContract {self.contract_ref} "
            f"{self.hours_delivered:.1f}/{self.hours_target:.1f}h>"
        )
