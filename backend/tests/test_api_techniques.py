from fastapi.testclient import TestClient

from app.main import app
from scripts.seed import run as run_seed
from scripts.seed_data import KB, TACTIC_GROUPS


def _unique_technique_count() -> int:
    seen: set[str] = set()
    for entries in TACTIC_GROUPS.values():
        for code, _ in entries:
            seen.add(code)
    return len(seen)


def test_lists_full_catalog_with_correct_total(db_session):
    run_seed()
    client = TestClient(app)
    response = client.get("/api/techniques")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == _unique_technique_count()
    assert len(body["techniques"]) == body["total"]


def test_kb_techniques_are_marked_specific(db_session):
    run_seed()
    client = TestClient(app)
    body = client.get("/api/techniques").json()
    by_id = {t["technique_id"]: t for t in body["techniques"]}
    for code in KB:
        assert by_id[code]["mapping_source"] == "specific"


def test_technique_without_kb_entry_is_tactic_default(db_session):
    run_seed()
    client = TestClient(app)
    body = client.get("/api/techniques").json()
    by_id = {t["technique_id"]: t for t in body["techniques"]}
    assert by_id["T1595"]["mapping_source"] == "tactic_default"


def test_filter_by_tactic_name(db_session):
    run_seed()
    client = TestClient(app)
    body = client.get("/api/techniques", params={"tactic": "Reconnaissance"}).json()
    assert body["total"] > 0
    assert all(t["tactic_name"] == "Reconnaissance" for t in body["techniques"])


def test_filter_by_status(db_session):
    run_seed()
    client = TestClient(app)
    body = client.get("/api/techniques", params={"status": "specific"}).json()
    assert body["total"] == len(KB)
    assert all(t["mapping_source"] == "specific" for t in body["techniques"])


def test_search_by_id_and_name_case_insensitive(db_session):
    run_seed()
    client = TestClient(app)
    body = client.get("/api/techniques", params={"q": "phishing"}).json()
    assert any(t["technique_id"] == "T1566.001" for t in body["techniques"])

    body_by_code = client.get("/api/techniques", params={"q": "t1078"}).json()
    assert {t["technique_id"] for t in body_by_code["techniques"]} == {"T1078", "T1078.004"}
