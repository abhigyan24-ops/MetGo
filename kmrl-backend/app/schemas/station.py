"""
Station schemas.
Source data: KMRL GTFS open data — contains data provided by Kochi Metro Rail Limited.
"""

from pydantic import BaseModel, Field


class StationOut(BaseModel):
    """Single station on the KMRL Blue Line."""

    stop_id: str = Field(..., examples=["AMET"], description="GTFS stop_id")
    stop_name: str = Field(..., examples=["Aluva"])
    latitude: float = Field(..., examples=[10.1004])
    longitude: float = Field(..., examples=[76.3519])
    sequence: int = Field(..., ge=1, le=25, description="Position on Blue Line (1=Aluva, 25=Tripunithura Terminal)")
    is_interchange: bool = Field(False)
    distance_from_aluva_km: float | None = Field(None, examples=[0.0])

    model_config = {"from_attributes": True}
