"""
Train fleet schemas — matches the shared API contract exactly.

The TrainResource schema is the canonical cross-track contract shape
agreed between Track A (solver), Track B (backend), and Track C (frontend).
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional, Union

from pydantic import BaseModel, Field

from app.models.train import JobCardSeverity, JobCardStatus, TrainStatus


# ---------------------------------------------------------------------------
# Sub-schemas
# ---------------------------------------------------------------------------

class JobCardOut(BaseModel):
    """Individual maintenance job card."""
    id: Union[str, int] = Field(..., examples=["JC-114"], description="Job card reference number or ID")
    jc_ref: Optional[str] = Field(None, examples=["JC-114"])
    status: JobCardStatus = Field(..., examples=["open"])
    severity: JobCardSeverity = Field(..., examples=["critical"])
    description: str = Field(..., examples=["Pantograph inspection overdue"])

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_jobcard(cls, jc) -> "JobCardOut":
        return cls(
            id=jc.jc_ref,
            status=jc.status,
            severity=jc.severity,
            description=jc.description,
        )


class FitnessCertOut(BaseModel):
    cert_ref: str = Field(..., examples=["FC-T09-2026"])
    expiry_date: date
    days_to_expiry: int
    is_expiring_soon: bool
    is_expired: bool

    model_config = {"from_attributes": True}


class BrandingContractOut(BaseModel):
    contract_ref: str
    advertiser: Optional[str] = None
    hours_target: float
    hours_delivered: float
    hours_remaining: float
    is_under_target: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Canonical TrainResource — the locked API contract shape
# ---------------------------------------------------------------------------

class TrainResource(BaseModel):
    """
    Canonical train resource — this is the exact shape agreed with Track A and Track C.
    Do not change field names without updating all three tracks.
    """
    train_id: str = Field(..., examples=["T09"])
    fitness_cert_expiry: Optional[date] = Field(
        None, examples=["2026-08-20"],
        description="Expiry date of the current active fitness certificate"
    )
    job_cards: List[JobCardOut] = Field(
        default_factory=list,
        description="All open job cards for this train"
    )
    cleaning_due: bool = Field(
        False,
        description="True if a cleaning slot is scheduled and not yet completed"
    )
    branding_hours_target: float = Field(0.0, examples=[12.0])
    branding_hours_delivered: float = Field(0.0, examples=[9.0])
    current_bay: Optional[str] = Field(None, examples=["B14"])
    mileage: float = Field(0.0, examples=[48210.0], description="Cumulative mileage in km")


# ---------------------------------------------------------------------------
# Summary list endpoint
# ---------------------------------------------------------------------------

class TrainOut(BaseModel):
    """Lightweight summary for the train list endpoint."""
    train_id: str
    status: TrainStatus
    current_bay_id: Optional[str] = None
    mileage_km: float
    coach_count: int

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Full detail endpoint
# ---------------------------------------------------------------------------

class TrainDetail(BaseModel):
    """Full train detail including all related records."""
    train_id: str
    status: TrainStatus
    coach_count: int
    current_bay_id: Optional[str] = None
    mileage_km: float

    fitness_certs: List[FitnessCertOut] = []
    job_cards: List[JobCardOut] = []
    cleaning_due: bool = False
    branding_contracts: List[BrandingContractOut] = []

    model_config = {"from_attributes": True}
