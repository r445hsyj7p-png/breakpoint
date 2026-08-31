from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from scripts.seed import run as run_seed

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "mitre_stix_sample.json"


def _upload_fixture(client: TestClient) -> dict:
    with FIXTURE_PATH.open("rb") as f:
        response = client.post(
            "/api/admin/mitre-import/upload",
            files={"file": ("mitre_stix_sample.json", f, "application/json")},
            params={"triggered_by": "Alex"},
        )
    return response


def test_upload_creates_batch_and_computes_diff_synchronously_in_test_client(db_session):
    """TestClient führt BackgroundTasks vor der Rückgabe von client.post()
    aus (analog Sales-Briefing-Tests) — der Diff ist direkt danach über GET
    verfügbar, kein Polling nötig im Test."""
    run_seed()
    client = TestClient(app)

    upload_resp = _upload_fixture(client)
    assert upload_resp.status_code == 202
    body = upload_resp.json()
    assert body["status"] == "diff_pending"
    batch_id = body["id"]

    get_resp = client.get(f"/api/admin/mitre-import/batches/{batch_id}")
    assert get_resp.status_code == 200
    batch = get_resp.json()
    assert batch["status"] == "diff_ready"
    assert batch["bundle_version"] == "99.9"
    assert batch["triggered_by"] == "Alex"
    diff = batch["diff_snapshot"]
    assert {"T9001", "T9001.001", "T9003", "T9004"} == {
        t["technique_id"] for t in diff["new_techniques"]
    }
    assert any(c["technique_id"] == "T9001" for c in diff["mitigation_candidates"])
    assert any(c["technique_id"] == "T1078" for c in diff["conflicts"])


def test_fetch_endpoint_uses_injected_bundle_via_monkeypatched_fetch(db_session, monkeypatch):
    monkeypatch.setattr(
        "app.services.mitre_import.fetch_bundle_bytes", lambda ref="master", timeout=90.0: FIXTURE_PATH.read_bytes()
    )
    run_seed()
    client = TestClient(app)

    resp = client.post("/api/admin/mitre-import/fetch")
    assert resp.status_code == 202
    batch_id = resp.json()["id"]

    batch = client.get(f"/api/admin/mitre-import/batches/{batch_id}").json()
    assert batch["status"] == "diff_ready"
    assert batch["source"] == "github_raw"


def test_get_unknown_batch_returns_404(db_session):
    run_seed()
    client = TestClient(app)
    response = client.get("/api/admin/mitre-import/batches/999999")
    assert response.status_code == 404


def test_apply_and_rollback_full_lifecycle(db_session):
    run_seed()
    client = TestClient(app)
    batch_id = _upload_fixture(client).json()["id"]

    apply_resp = client.post(
        f"/api/admin/mitre-import/batches/{batch_id}/apply",
        json={"technique_ids": ["T9001", "T9001.001"], "mitigation_technique_ids": ["T9001"]},
    )
    assert apply_resp.status_code == 200
    applied = apply_resp.json()
    assert applied["status"] == "applied"
    assert applied["applied_at"] is not None

    techniques_resp = client.get("/api/techniques")
    technique_ids = {t["technique_id"] for t in techniques_resp.json()["techniques"]}
    assert "T9001" in technique_ids

    rollback_resp = client.post(f"/api/admin/mitre-import/batches/{batch_id}/rollback")
    assert rollback_resp.status_code == 200
    assert rollback_resp.json()["status"] == "rolled_back"

    techniques_resp_after = client.get("/api/techniques")
    technique_ids_after = {t["technique_id"] for t in techniques_resp_after.json()["techniques"]}
    assert "T9001" not in technique_ids_after


def test_rollback_rejected_for_batch_that_is_not_the_latest_applied(db_session):
    run_seed()
    client = TestClient(app)
    first_batch_id = _upload_fixture(client).json()["id"]
    client.post(
        f"/api/admin/mitre-import/batches/{first_batch_id}/apply",
        json={"technique_ids": ["T1003"], "mitigation_technique_ids": []},
    )

    second_batch_id = _upload_fixture(client).json()["id"]
    client.post(
        f"/api/admin/mitre-import/batches/{second_batch_id}/apply",
        json={"technique_ids": [], "mitigation_technique_ids": []},
    )

    response = client.post(f"/api/admin/mitre-import/batches/{first_batch_id}/rollback")
    assert response.status_code == 409


def test_apply_rejects_batch_not_in_diff_ready_state(db_session):
    run_seed()
    client = TestClient(app)
    batch_id = _upload_fixture(client).json()["id"]
    client.post(
        f"/api/admin/mitre-import/batches/{batch_id}/apply",
        json={"technique_ids": [], "mitigation_technique_ids": []},
    )

    second_apply = client.post(
        f"/api/admin/mitre-import/batches/{batch_id}/apply",
        json={"technique_ids": [], "mitigation_technique_ids": []},
    )
    assert second_apply.status_code == 409


def test_list_batches_returns_newest_first(db_session):
    run_seed()
    client = TestClient(app)
    first_id = _upload_fixture(client).json()["id"]
    second_id = _upload_fixture(client).json()["id"]

    batches = client.get("/api/admin/mitre-import/batches").json()
    ids_in_order = [b["id"] for b in batches]
    assert ids_in_order.index(second_id) < ids_in_order.index(first_id)
