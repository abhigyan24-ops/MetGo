"""
MetGo backend API integration & unit tests.
"""

import pytest
from fastapi.testclient import TestClient
from app.worker.celery_app import celery_app

# Enable eager execution for Celery tasks in tests
celery_app.conf.task_always_eager = True
celery_app.conf.task_eager_propagates = True

from app.main import app
from app.db.session import SessionLocal
from app.models.train import Train
from app.models.yard import YardBay
from app.services.explainability import ExplainabilityEngine
from app.services.yard_graph import YardGraphService


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_health_endpoints(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}

    res_root = client.get("/")
    assert res_root.status_code == 200
    assert res_root.json()["status"] == "ok"


def test_get_trains(client):
    res = client.get("/trains/")
    assert res.status_code == 200
    trains = res.json()
    assert len(trains) == 25
    assert any(t["train_id"] == "T01" for t in trains)

    res_single = client.get("/trains/T01")
    assert res_single.status_code == 200
    assert res_single.json()["train_id"] == "T01"


def test_get_stations(client):
    res = client.get("/stations/")
    assert res.status_code == 200
    stations = res.json()
    assert len(stations) >= 20


def test_plan_generation_and_explain(client):
    res = client.post("/plan/generate")
    assert res.status_code == 200
    data = res.json()
    assert "plan_id" in data
    assert len(data["assignments"]) == 25
    plan_id = data["plan_id"]

    # Explain endpoint
    res_exp = client.get(f"/plan/{plan_id}/explain/T01")
    assert res_exp.status_code == 200
    exp_data = res_exp.json()
    assert exp_data["train_id"] == "T01"
    assert "assigned_state" in exp_data
    assert "explanation" in exp_data
    assert isinstance(exp_data["constraints_considered"], list)


def test_what_if_override(client):
    override_payload = {
        "override": {
            "train_id": "T05",
            "status": "maintenance"
        }
    }
    res = client.post("/plan/what-if", json=override_payload)
    assert res.status_code == 200
    data = res.json()
    assert "plan_id" in data
    assignments = {a["train_id"]: a["state"] for a in data["assignments"]}
    assert assignments["T05"] == "maintenance"


def test_explainability_engine_direct(db_session):
    engine = ExplainabilityEngine(db_session)
    t = db_session.query(Train).filter(Train.train_id == "T01").first()
    assert t is not None
    details = engine._extract_constraint_details(t)
    assert "fitness_cert" in details
    assert "cleaning" in details
    assert "branding" in details


def test_yard_graph_service():
    svc = YardGraphService()
    assert svc.neo4j is not None
