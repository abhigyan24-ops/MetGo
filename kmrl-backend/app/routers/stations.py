"""
Station endpoints — exposes the 25 real KMRL stations loaded from GTFS data.
Contains data provided by Kochi Metro Rail Limited.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.station import Station
from app.schemas.station import StationOut

router = APIRouter()


@router.get("/", response_model=List[StationOut], summary="List all 25 KMRL stations")
def list_stations(db: Session = Depends(get_db)):
    """
    Return all 25 stations on KMRL's Blue Line (Aluva ↔ Tripunithura Terminal).
    Source: KMRL GTFS open data — contains data provided by Kochi Metro Rail Limited.
    """
    stations = db.query(Station).order_by(Station.sequence).all()
    return stations
