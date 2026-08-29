from fastapi.testclient import TestClient

from app.main import app
from scripts.seed import run as run_seed


def test_create_engagement_rejects_empty_name(db_session):
    run_seed()
    client = TestClient(app)
    response = client.post("/api/engagements", json={"name": ""})
    assert response.status_code == 422


def test_list_engagements_returns_newest_first(db_session):
    run_seed()
    client = TestClient(app)
    client.post("/api/engagements", json={"name": "Erstes"})
    client.post("/api/engagements", json={"name": "Zweites"})

    body = client.get("/api/engagements").json()
    assert [e["name"] for e in body] == ["Zweites", "Erstes"]


def test_engagement_lifecycle_create_findings_analysis(db_session):
    run_seed()
    client = TestClient(app)

    create_resp = client.post("/api/engagements", json={"name": "Red Team Assessment 2026"})
    assert create_resp.status_code == 201
    engagement_id = create_resp.json()["id"]

    findings_resp = client.post(
        f"/api/engagements/{engagement_id}/findings",
        json={"codes": "T1566.001, T1078, T9999.999"},
    )
    assert findings_resp.status_code == 200
    findings_body = findings_resp.json()
    assert set(findings_body["added_technique_ids"]) == {"T1566.001", "T1078"}
    assert findings_body["unknown_codes"] == ["T9999.999"]

    analysis_resp = client.get(f"/api/engagements/{engagement_id}/analysis")
    assert analysis_resp.status_code == 200
    analysis_body = analysis_resp.json()
    assert {t["technique_id"] for t in analysis_body["techniques"]} == {"T1566.001", "T1078"}


def test_adding_same_finding_twice_is_idempotent(db_session):
    run_seed()
    client = TestClient(app)
    engagement_id = client.post("/api/engagements", json={"name": "Test"}).json()["id"]

    client.post(f"/api/engagements/{engagement_id}/findings", json={"codes": "T1078"})
    client.post(f"/api/engagements/{engagement_id}/findings", json={"codes": "T1078"})

    analysis = client.get(f"/api/engagements/{engagement_id}/analysis").json()
    assert len(analysis["techniques"]) == 1


def test_findings_for_unknown_engagement_returns_404(db_session):
    run_seed()
    client = TestClient(app)
    response = client.post("/api/engagements/999999/findings", json={"codes": "T1078"})
    assert response.status_code == 404


def test_analysis_for_unknown_engagement_returns_404(db_session):
    run_seed()
    client = TestClient(app)
    response = client.get("/api/engagements/999999/analysis")
    assert response.status_code == 404


def test_analysis_scoped_to_own_engagement(db_session):
    """Zwei Engagements dürfen sich nicht gegenseitig ihre Findings zeigen."""
    run_seed()
    client = TestClient(app)
    engagement_a = client.post("/api/engagements", json={"name": "A"}).json()["id"]
    engagement_b = client.post("/api/engagements", json={"name": "B"}).json()["id"]

    client.post(f"/api/engagements/{engagement_a}/findings", json={"codes": "T1078"})
    client.post(f"/api/engagements/{engagement_b}/findings", json={"codes": "T1003"})

    analysis_a = client.get(f"/api/engagements/{engagement_a}/analysis").json()
    assert {t["technique_id"] for t in analysis_a["techniques"]} == {"T1078"}


def test_analysis_input_codes_ordering_is_deterministic_regardless_of_insertion_order(db_session):
    """GET .../analysis liest über SELECT DISTINCT ohne explizite Reihenfolge aus
    der finding-Tabelle — ohne ORDER BY liefert Postgres dafür keine garantierte,
    stabile Reihenfolge. Zwei Engagements, denen dieselben Codes in
    unterschiedlicher Reihenfolge hinzugefügt werden, müssen trotzdem dieselbe
    input_codes-Reihenfolge in der Antwort liefern."""
    run_seed()
    client = TestClient(app)
    engagement_a = client.post("/api/engagements", json={"name": "A"}).json()["id"]
    engagement_b = client.post("/api/engagements", json={"name": "B"}).json()["id"]

    client.post(f"/api/engagements/{engagement_a}/findings", json={"codes": "T1078, T1003, T1055"})
    client.post(f"/api/engagements/{engagement_b}/findings", json={"codes": "T1055, T1078, T1003"})

    codes_a = client.get(f"/api/engagements/{engagement_a}/analysis").json()["input_codes"]
    codes_b = client.get(f"/api/engagements/{engagement_b}/analysis").json()["input_codes"]
    assert codes_a == codes_b == sorted(codes_a)
