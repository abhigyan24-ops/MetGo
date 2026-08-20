"""
TimescaleDB hypertables for time-series data.

These tables are converted to hypertables at startup via
app/db/session.py:create_timescale_hypertables().

TimescaleDB Community Edition is used — free, self-hosted via Docker.
No paid Timescale Cloud tier is required.
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class MileageSnapshot(Base):
    """
    Periodic mileage reading per trainset.
    Used for wear-leveling: assign trains with lower cumulative mileage to
    longer / more demanding service runs.

    Hypertable partition key: recorded_at (time dimension).
    SIMULATED data — realistic mileage spread across the 25-train fleet.
    """
    __tablename__ = "mileage_snapshots"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    train_id    = Column(String(10), ForeignKey("trains.train_id"), nullable=False, index=True)
    mileage_km  = Column(Float, nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, index=True)
    source      = Column(String(30), default="simulated")  # "simulated" | "live"

    train = relationship("Train")

    def __repr__(self) -> str:
        return f"<MileageSnapshot {self.train_id} {self.mileage_km:.0f}km @ {self.recorded_at}>"


class CertEvent(Base):
    """
    Fitness certificate countdown events.
    One row per cert-check event — recorded each time the planner evaluates
    cert status. Enables a time-series dashboard of cert health across the fleet.

    Hypertable partition key: event_at (time dimension).
    SIMULATED data.
    """
    __tablename__ = "cert_events"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    train_id     = Column(String(10), ForeignKey("trains.train_id"), nullable=False, index=True)
    cert_ref     = Column(String(30), nullable=False)
    days_to_expiry = Column(Integer, nullable=False)
    event_at     = Column(DateTime(timezone=True), nullable=False, index=True)
    event_type   = Column(String(30), nullable=False)   # "check" | "expiry_warning" | "expired"
    notes        = Column(Text, nullable=True)

    train = relationship("Train")

    def __repr__(self) -> str:
        return (
            f"<CertEvent {self.train_id} cert={self.cert_ref} "
            f"days={self.days_to_expiry} [{self.event_type}]>"
        )
