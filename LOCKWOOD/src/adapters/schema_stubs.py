"""
Lightweight stand-in classes mirroring the real database team's
SQLAlchemy models (see the Part 3 project context summary, Section 7
"KEY REAL FIELD NAMES FROM THE DATABASE SCHEMA"). These are NOT the
real ORM classes -- Part 3b works entirely offline, without a live
database connection, so the adapter can be developed and tested here
in isolation. Part 3c (wiring into app/worker/tasks.py) will pass in
real SQLAlchemy query results instead, which expose the same
attribute names by construction, so adapt_train()/adapt_yard_layout()
in db_adapter.py should need ZERO logic changes when that swap
happens -- only these stub definitions get discarded.

ASSUMPTION FLAGGED FOR VERIFICATION: the real schema's CleaningSlot
model's exact field name for "date last cleaned" was never confirmed
in the project context summary (only that the model exists, alongside
Train/FitnessCert/JobCard/BrandingContract). This stub guesses
`completed_at` -- confirm the real field name with the database
teammate before Part 3c, and adjust adapt_train() in db_adapter.py if
it differs. Every other field name below is copied directly from the
confirmed real field list.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class DBFitnessCert:
    expiry_date: date


@dataclass
class DBJobCard:
    status: str    # "OPEN" or "CLOSED"
    severity: str  # "CRITICAL", "MAJOR", or "MINOR"


@dataclass
class DBCleaningSlot:
    completed: bool
    completed_at: Optional[date] = None  # meaningful only when completed=True


@dataclass
class DBBrandingContract:
    hours_target: int
    hours_delivered: int
    is_active: bool


@dataclass
class DBTrain:
    train_id: str  # real format: "T01"-"T25"
    mileage_km: int
    current_bay_id: str
    latest_fitness_cert: Optional[DBFitnessCert]
    job_cards: list = field(default_factory=list)          # list[DBJobCard]
    cleaning_slots: list = field(default_factory=list)      # list[DBCleaningSlot]
    branding_contracts: list = field(default_factory=list)  # list[DBBrandingContract]


@dataclass
class DBYardBay:
    bay_id: str
    line_id: str
    position: int  # 1 = entrance/exit end
    bay_type: str  # "STABLING", "MAINTENANCE", "WASH", "INSPECTION"
