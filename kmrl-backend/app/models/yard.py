"""
Yard models — Muttom Yard graph representation.

SIMULATED layout — the exact bay-by-bay engineering drawings of Muttom Yard
are internal KMRL data. This model captures a physically consistent simplified
layout: N stabling lines, each with M bays in sequence, where pulling a
rear-bay train requires shunting the ones parked in front of it.

The full relational topology (ADJACENT_TO / BLOCKS relationships) is stored in
Neo4j (see app/services/yard_graph.py). These SQLAlchemy models hold the
reference data that Postgres needs (bay metadata, current occupant).
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime,
    ForeignKey, Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class BayType(str, enum.Enum):
    STABLING   = "stabling"    # normal overnight stabling bay
    MAINTENANCE = "maintenance" # maintenance pit / workshop bay
    WASH        = "wash"        # automatic train wash
    INSPECTION  = "inspection"  # periodic inspection bay


class YardLine(Base):
    """
    A stabling road / siding inside Muttom Yard.
    Each line contains several bays in sequence (1 = entrance end).

    SIMULATED: 5 stabling lines + 1 maintenance track + 1 wash track.
    """
    __tablename__ = "yard_lines"

    line_id   = Column(String(10), primary_key=True)   # e.g. "L1", "L2", … "M1", "W1"
    line_name = Column(String(50), nullable=False)      # e.g. "Stabling Road 1"
    bay_count = Column(Integer, nullable=False)
    line_type = Column(SAEnum(BayType), default=BayType.STABLING, nullable=False)

    bays = relationship("YardBay", back_populates="yard_line", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<YardLine {self.line_id} ({self.bay_count} bays)>"


class YardBay(Base):
    """
    Individual parking bay within a yard line.

    Position 1 is the entrance-end bay (first out / no shunting needed).
    Higher position numbers are deeper — pulling those trains requires
    shunting every lower-position train out of the way first.

    SIMULATED layout.
    """
    __tablename__ = "yard_bays"

    bay_id   = Column(String(10), primary_key=True)    # e.g. "B01"–"B30", "M01"–"M06"
    line_id  = Column(String(10), ForeignKey("yard_lines.line_id"), nullable=False, index=True)

    # Position within the line — 1 = entrance (easiest to pull out)
    position = Column(Integer, nullable=False)

    bay_type  = Column(SAEnum(BayType), default=BayType.STABLING, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Current occupant (nullable = bay is empty)
    occupied_by = Column(
        String(10),
        ForeignKey("trains.train_id", use_alter=True, name="fk_bay_train"),
        nullable=True,
    )

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    yard_line      = relationship("YardLine", back_populates="bays")
    occupying_train = relationship(
        "Train",
        foreign_keys=[occupied_by],
        # Don't cascade — the train record owns itself
    )

    @property
    def is_occupied(self) -> bool:
        return self.occupied_by is not None

    @property
    def shunts_needed(self) -> int:
        """
        Number of trains that must move before this bay can be accessed.
        Equals position - 1 (position 1 needs 0 shunts).
        """
        return max(0, self.position - 1)

    def __repr__(self) -> str:
        occ = self.occupied_by or "empty"
        return f"<YardBay {self.bay_id} pos={self.position} [{occ}]>"
