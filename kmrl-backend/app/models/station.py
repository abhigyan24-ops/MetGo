"""
Station model — populated from KMRL's official GTFS open data.

Contains data provided by Kochi Metro Rail Limited.
Source: https://kochimetro.org/open-data/
"""

from sqlalchemy import Column, String, Float, Integer, Boolean
from app.db.session import Base


class Station(Base):
    __tablename__ = "stations"

    # GTFS stop_id is the natural key (e.g. "AMET" for Aluva Metro)
    stop_id = Column(String(20), primary_key=True, index=True)

    # Human-readable name from stops.txt
    stop_name = Column(String(100), nullable=False)

    # Coordinates from GTFS stops.txt (real KMRL data)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Position on the Blue Line (1 = Aluva, 25 = Tripunithura Terminal)
    sequence = Column(Integer, nullable=False)

    # Whether the station has an interchange (e.g. MG Road has bus interchange)
    is_interchange = Column(Boolean, default=False)

    # Distance from Aluva terminus in km (cumulative)
    distance_from_aluva_km = Column(Float, nullable=True)

    def __repr__(self) -> str:
        return f"<Station {self.stop_id}: {self.stop_name} (seq={self.sequence})>"
