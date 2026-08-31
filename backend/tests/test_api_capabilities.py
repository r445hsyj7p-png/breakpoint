from fastapi.testclient import TestClient

from app.main import app
from scripts.seed import run as run_seed
from scripts.seed_data import ALL_CAPABILITIES


def test_lists_all_capabilities_with_ids(db_session):
    run_seed()
    client = TestClient(app)
    response = client.get("/api/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == len(ALL_CAPABILITIES)
    assert all(isinstance(c["id"], int) for c in body)
    assert {c["name"] for c in body} == set(ALL_CAPABILITIES)
