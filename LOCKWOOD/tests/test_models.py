"""
Basic sanity tests for the data models and the hand-written test
dataset. These do NOT test any solver logic (there is none yet) —
they only confirm the data structures are well-formed.
"""

from datetime import date

from src.data.test_fleet_6 import TEST_FLEET_6, TEST_YARD_LAYOUT_6
from src.constants import PLANNING_DATE


def test_fleet_has_six_trains():
    assert len(TEST_FLEET_6) == 6


def test_all_train_ids_unique():
    ids = [t.train_id for t in TEST_FLEET_6]
    assert len(ids) == len(set(ids))


def test_kmrl_02_cert_is_expired_relative_to_planning_date():
    train = next(t for t in TEST_FLEET_6 if t.train_id == "KMRL-02")
    assert train.fitness_cert_expiry < PLANNING_DATE


def test_kmrl_03_has_open_job_card():
    train = next(t for t in TEST_FLEET_6 if t.train_id == "KMRL-03")
    assert train.job_card_severity == "critical"


def test_kmrl_05_cert_expires_after_planning_date():
    train = next(t for t in TEST_FLEET_6 if t.train_id == "KMRL-05")
    assert train.fitness_cert_expiry > PLANNING_DATE


def test_yard_layout_has_six_bays_in_order():
    bays = [bay for line in TEST_YARD_LAYOUT_6.lines.values() for bay in line.bay_order]
    assert len(bays) == 6
