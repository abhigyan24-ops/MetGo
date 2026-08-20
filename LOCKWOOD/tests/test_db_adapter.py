"""
Tests for the Part 3b real-schema data adapter (src/adapters/db_adapter.py).
Uses the offline stand-in ORM classes in schema_stubs.py (see that
module's docstring for why -- Part 3b works without a live DB).
"""

from datetime import date, timedelta

from src.adapters.db_adapter import adapt_train, adapt_yard_layout
from src.adapters.schema_stubs import (
    DBBrandingContract,
    DBCleaningSlot,
    DBFitnessCert,
    DBJobCard,
    DBTrain,
    DBYardBay,
)
from src.constants import PLANNING_DATE


def test_adapt_train_maps_basic_fields_directly():
    db_train = DBTrain(
        train_id="T07",
        mileage_km=150000,
        current_bay_id="A3",
        latest_fitness_cert=DBFitnessCert(expiry_date=date(2026, 12, 1)),
    )
    train = adapt_train(db_train)
    assert train.train_id == "T07"
    assert train.mileage_total == 150000
    assert train.current_bay == "A3"
    assert train.fitness_cert_expiry == date(2026, 12, 1)


def test_adapt_train_missing_cert_treated_as_already_expired():
    db_train = DBTrain(
        train_id="T08", mileage_km=100000, current_bay_id="A1",
        latest_fitness_cert=None,
    )
    train = adapt_train(db_train)
    assert train.fitness_cert_expiry < PLANNING_DATE


def test_adapt_train_picks_worst_of_multiple_open_job_cards():
    db_train = DBTrain(
        train_id="T09", mileage_km=100000, current_bay_id="A1",
        latest_fitness_cert=DBFitnessCert(expiry_date=date(2026, 12, 1)),
        job_cards=[
            DBJobCard(status="open", severity="minor"),
            DBJobCard(status="open", severity="critical"),
            DBJobCard(status="closed", severity="critical"),  # closed, ignored
        ],
    )
    train = adapt_train(db_train)
    assert train.job_card_severity == "critical"


def test_adapt_train_no_open_job_cards_gives_none():
    db_train = DBTrain(
        train_id="T10", mileage_km=100000, current_bay_id="A1",
        latest_fitness_cert=DBFitnessCert(expiry_date=date(2026, 12, 1)),
        job_cards=[DBJobCard(status="closed", severity="critical")],
    )
    train = adapt_train(db_train)
    assert train.job_card_severity is None


def test_adapt_train_uses_most_recent_cleaning_slot():
    db_train = DBTrain(
        train_id="T11", mileage_km=100000, current_bay_id="A1",
        latest_fitness_cert=DBFitnessCert(expiry_date=date(2026, 12, 1)),
        cleaning_slots=[
            DBCleaningSlot(completed=True, completed_at=date(2026, 8, 1)),
            DBCleaningSlot(completed=True, completed_at=date(2026, 8, 10)),  # most recent
            DBCleaningSlot(completed=False, completed_at=None),  # not done yet -- must be ignored
        ],
    )
    train = adapt_train(db_train)
    assert train.last_cleaned == date(2026, 8, 10)


def test_adapt_train_no_cleaning_history_is_maximally_overdue():
    db_train = DBTrain(
        train_id="T12", mileage_km=100000, current_bay_id="A1",
        latest_fitness_cert=DBFitnessCert(expiry_date=date(2026, 12, 1)),
    )
    train = adapt_train(db_train)
    assert train.last_cleaned < date(2020, 1, 1)  # sentinel, always overdue


def test_adapt_train_uses_active_branding_contract_only():
    db_train = DBTrain(
        train_id="T13", mileage_km=100000, current_bay_id="A1",
        latest_fitness_cert=DBFitnessCert(expiry_date=date(2026, 12, 1)),
        branding_contracts=[
            DBBrandingContract(hours_target=40, hours_delivered=10, is_active=False),
            DBBrandingContract(hours_target=60, hours_delivered=25, is_active=True),
        ],
    )
    train = adapt_train(db_train)
    assert train.branding_target_hours == 60
    assert train.branding_hours_this_month == 25


def test_adapt_train_no_active_contract_gives_zero_shortfall():
    db_train = DBTrain(
        train_id="T14", mileage_km=100000, current_bay_id="A1",
        latest_fitness_cert=DBFitnessCert(expiry_date=date(2026, 12, 1)),
        branding_contracts=[
            DBBrandingContract(hours_target=40, hours_delivered=10, is_active=False),
        ],
    )
    train = adapt_train(db_train)
    assert train.branding_target_hours == 0
    assert train.branding_hours_this_month == 0


def test_adapt_yard_layout_groups_by_line_and_sorts_by_position():
    db_bays = [
        DBYardBay(bay_id="A2", line_id="L1", position=2, bay_type="STABLING"),
        DBYardBay(bay_id="A1", line_id="L1", position=1, bay_type="STABLING"),
        DBYardBay(bay_id="B1", line_id="L2", position=1, bay_type="STABLING"),
    ]
    layout = adapt_yard_layout(db_bays)
    assert set(layout.lines.keys()) == {"L1", "L2"}
    assert layout.lines["L1"].bay_order == ["A1", "A2"]
    assert layout.lines["L2"].bay_order == ["B1"]


def test_adapt_yard_layout_excludes_non_stabling_bays():
    db_bays = [
        DBYardBay(bay_id="A1", line_id="L1", position=1, bay_type="STABLING"),
        DBYardBay(bay_id="M1", line_id="M1", position=1, bay_type="MAINTENANCE"),
        DBYardBay(bay_id="W1", line_id="W1", position=1, bay_type="WASH"),
    ]
    layout = adapt_yard_layout(db_bays)
    assert set(layout.lines.keys()) == {"L1"}
    assert layout.line_for_bay("M1") is None
    assert layout.line_for_bay("W1") is None


def test_adapt_train_job_card_matching_is_case_insensitive():
    """The real schema's status/severity values are lowercase, but this
    must not silently break if a mixed-case value ever shows up."""
    db_train = DBTrain(
        train_id="T15", mileage_km=100000, current_bay_id="A1",
        latest_fitness_cert=DBFitnessCert(expiry_date=date(2026, 12, 1)),
        job_cards=[DBJobCard(status="Open", severity="Critical")],
    )
    train = adapt_train(db_train)
    assert train.job_card_severity == "critical"


def test_adapt_yard_layout_stabling_match_is_case_insensitive():
    db_bays = [DBYardBay(bay_id="A1", line_id="L1", position=1, bay_type="Stabling")]
    layout = adapt_yard_layout(db_bays)
    assert set(layout.lines.keys()) == {"L1"}
