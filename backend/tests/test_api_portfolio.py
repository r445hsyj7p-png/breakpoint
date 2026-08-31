from fastapi.testclient import TestClient

from app.main import app
from app.models import Capability
from scripts.seed import run as run_seed


def _capability_id(db_session, name: str) -> int:
    return db_session.query(Capability.id).filter_by(name=name).scalar()


def test_create_and_list_technology(db_session):
    run_seed()
    client = TestClient(app)
    mfa_id = _capability_id(db_session, "MFA")

    response = client.post(
        "/api/portfolio/technologies",
        json={"name": "Okta", "type": "Identity", "capability_ids": [mfa_id]},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Okta"
    assert body["active"] is True
    assert body["capabilities"] == ["MFA"]

    listed = client.get("/api/portfolio/technologies").json()
    assert [t["name"] for t in listed] == ["Okta"]


def test_create_dedupes_duplicate_capability_ids(db_session):
    """Regressionstest: doppelte IDs im Payload dürfen keinen IntegrityError
    auslösen (zusammengesetzter Primärschlüssel würde sonst doppelt eingefügt)."""
    run_seed()
    client = TestClient(app)
    mfa_id = _capability_id(db_session, "MFA")

    response = client.post(
        "/api/portfolio/technologies",
        json={"name": "Okta", "type": "Identity", "capability_ids": [mfa_id, mfa_id]},
    )
    assert response.status_code == 201
    assert response.json()["capabilities"] == ["MFA"]


def test_create_rejects_unknown_capability_id(db_session):
    run_seed()
    client = TestClient(app)
    response = client.post(
        "/api/portfolio/technologies",
        json={"name": "Okta", "type": "Identity", "capability_ids": [999999]},
    )
    assert response.status_code == 422


def test_update_rejects_unknown_capability_id(db_session):
    run_seed()
    client = TestClient(app)
    created = client.post("/api/portfolio/technologies", json={"name": "Okta", "type": "Identity"}).json()

    response = client.patch(
        f"/api/portfolio/technologies/{created['id']}", json={"capability_ids": [999999]}
    )
    assert response.status_code == 422


def test_create_rejects_empty_name(db_session):
    run_seed()
    client = TestClient(app)
    response = client.post("/api/portfolio/technologies", json={"name": "", "type": "Identity"})
    assert response.status_code == 422


def test_deactivate_is_soft_delete(db_session):
    run_seed()
    client = TestClient(app)
    created = client.post("/api/portfolio/technologies", json={"name": "Okta", "type": "Identity"}).json()

    deactivate_resp = client.post(f"/api/portfolio/technologies/{created['id']}/deactivate")
    assert deactivate_resp.status_code == 200
    assert deactivate_resp.json()["active"] is False

    # Standardliste zeigt nur aktive Technologien ...
    assert client.get("/api/portfolio/technologies").json() == []
    # ... die Zeile bleibt aber in der DB (kein Hard-Delete, Abschnitt 6a.1).
    all_technologies = client.get("/api/portfolio/technologies", params={"include_inactive": True}).json()
    assert len(all_technologies) == 1


def test_update_records_history_per_changed_field(db_session):
    run_seed()
    client = TestClient(app)
    mfa_id = _capability_id(db_session, "MFA")
    pam_id = _capability_id(db_session, "PAM")
    created = client.post(
        "/api/portfolio/technologies",
        json={"name": "Okta", "type": "Identity", "capability_ids": [mfa_id]},
    ).json()

    patch_resp = client.patch(
        f"/api/portfolio/technologies/{created['id']}",
        json={"name": "Okta Verify", "capability_ids": [mfa_id, pam_id]},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Okta Verify"
    assert set(patch_resp.json()["capabilities"]) == {"MFA", "PAM"}

    history = client.get(f"/api/portfolio/technologies/{created['id']}/history").json()
    fields_changed = {entry["field_changed"] for entry in history}
    # 2 Einträge aus dem Anlegen (name, capabilities — type war nicht leer,
    # zählt aber auch) + 2 aus dem Update (name, capabilities).
    assert "name" in fields_changed
    assert "capabilities" in fields_changed
    name_entries = [e for e in history if e["field_changed"] == "name"]
    assert any(e["old_value"] == "Okta" and e["new_value"] == "Okta Verify" for e in name_entries)


def test_patch_without_changes_does_not_record_history(db_session):
    run_seed()
    client = TestClient(app)
    created = client.post("/api/portfolio/technologies", json={"name": "Okta", "type": "Identity"}).json()
    history_before = client.get(f"/api/portfolio/technologies/{created['id']}/history").json()

    client.patch(f"/api/portfolio/technologies/{created['id']}", json={"name": "Okta"})

    history_after = client.get(f"/api/portfolio/technologies/{created['id']}/history").json()
    assert len(history_after) == len(history_before)


def test_technology_not_found_returns_404(db_session):
    run_seed()
    client = TestClient(app)
    assert client.patch("/api/portfolio/technologies/999999", json={"name": "X"}).status_code == 404
    assert client.post("/api/portfolio/technologies/999999/deactivate").status_code == 404
    assert client.get("/api/portfolio/technologies/999999/history").status_code == 404


def test_coverage_shows_gaps_for_uncovered_capabilities(db_session):
    run_seed()
    client = TestClient(app)

    coverage_before = client.get("/api/portfolio/coverage").json()
    assert "MFA" in coverage_before["gaps"]

    mfa_id = _capability_id(db_session, "MFA")
    client.post(
        "/api/portfolio/technologies",
        json={"name": "Okta", "type": "Identity", "capability_ids": [mfa_id]},
    )

    coverage_after = client.get("/api/portfolio/coverage").json()
    assert "MFA" not in coverage_after["gaps"]
    mfa_row = next(r for r in coverage_after["rows"] if r["capability"] == "MFA")
    assert mfa_row["covering_technologies"] == ["Okta"]


def test_deactivated_technology_no_longer_counts_as_coverage(db_session):
    run_seed()
    client = TestClient(app)
    mfa_id = _capability_id(db_session, "MFA")
    created = client.post(
        "/api/portfolio/technologies",
        json={"name": "Okta", "type": "Identity", "capability_ids": [mfa_id]},
    ).json()

    client.post(f"/api/portfolio/technologies/{created['id']}/deactivate")

    coverage = client.get("/api/portfolio/coverage").json()
    assert "MFA" in coverage["gaps"]
