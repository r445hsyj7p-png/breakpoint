from fastapi.testclient import TestClient

from app.main import app
from scripts.seed import run as run_seed


def test_analyze_example_chain_from_prototype(db_session):
    run_seed()
    client = TestClient(app)
    response = client.post(
        "/api/analyze", json={"codes": "T1566.001\nT1078\nT1021.001\nT1059.001"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["input_codes"] == ["T1566.001", "T1078", "T1021.001", "T1059.001"]
    assert len(body["techniques"]) == 4
    assert body["unknown_codes"] == []
    assert all(t["mapping_source"] == "specific" for t in body["techniques"])
    assert len(body["prioritized_measures"]) > 0


def test_analyze_empty_input_returns_empty_result_not_error(db_session):
    run_seed()
    client = TestClient(app)
    response = client.post("/api/analyze", json={"codes": "   "})
    assert response.status_code == 200
    body = response.json()
    assert body["techniques"] == []
    assert body["unknown_codes"] == []
    assert body["prioritized_measures"] == []


def test_analyze_unknown_code_is_not_an_error(db_session):
    run_seed()
    client = TestClient(app)
    response = client.post("/api/analyze", json={"codes": "T9999.999"})
    assert response.status_code == 200
    assert response.json()["unknown_codes"] == ["T9999.999"]
