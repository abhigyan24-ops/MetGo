"""
Fleet endpoints — list all trains and get individual train details.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.train import Train, JobCard, FitnessCert
from app.schemas.train import TrainOut, TrainDetail

router = APIRouter()


@router.get("", response_model=List[TrainOut], include_in_schema=False)
@router.get("/", response_model=List[TrainOut], summary="List all trains")
def list_trains(db: Session = Depends(get_db)):
    """Return summary of all 25 trains in the KMRL fleet."""
    trains = db.query(Train).order_by(Train.train_id).all()
    return trains


@router.get("/{train_id}", response_model=TrainDetail, summary="Get train details")
def get_train(train_id: str, db: Session = Depends(get_db)):
    """Return full detail for a single train including job cards and certs."""
    train = db.query(Train).filter(Train.train_id == train_id).first()
    if not train:
        raise HTTPException(status_code=404, detail=f"Train {train_id} not found")
    return train
