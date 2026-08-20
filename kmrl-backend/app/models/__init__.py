# Import all models here so Alembic autogenerate picks them up
from app.models.station import Station
from app.models.train import Train, JobCard, FitnessCert, CleaningSlot, BrandingContract
from app.models.yard import YardLine, YardBay
from app.models.plan import InductionPlan, PlanAssignment, ShuntMove
from app.models.timeseries import MileageSnapshot, CertEvent
