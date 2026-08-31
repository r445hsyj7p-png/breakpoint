from fastapi.testclient import TestClient

from app.main import app
from app.models.mapping import EffortLevel, ImpactLevel, MappingSource, TechniqueCapabilityMapping
from app.models.technique import Technique
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


def test_mitre_derived_mapping_is_reported_as_such_not_specific(db_session):
    """Regressionstest analog test_analyzer_service.py: list_techniques()
    las mapping_source früher nur als 'existiert eine Zeile in
    technique_capability_mapping?' statt den tatsächlichen Wert zu prüfen —
    seit Schritt 6 (mitre_derived, Abschnitt 6a.3 Punkt 5) wäre das falsch."""
    run_seed()
    db_session.add(
        TechniqueCapabilityMapping(
            technique_id="T1595",  # ohne KB-Eintrag im Seed
            mapping_source=MappingSource.MITRE_DERIVED,
            impact=ImpactLevel.MITTEL,
            effort=EffortLevel.NIEDRIG,
        )
    )
    db_session.commit()

    client = TestClient(app)
    body = client.get("/api/techniques").json()
    by_id = {t["technique_id"]: t for t in body["techniques"]}
    assert by_id["T1595"]["mapping_source"] == "mitre_derived"


def test_deprecated_techniques_are_hidden_by_default_and_shown_on_request(db_session):
    run_seed()
    db_session.get(Technique, "T1595").deprecated = True
    db_session.commit()

    client = TestClient(app)
    default_body = client.get("/api/techniques").json()
    assert "T1595" not in {t["technique_id"] for t in default_body["techniques"]}

    included_body = client.get("/api/techniques", params={"include_deprecated": "true"}).json()
    included = {t["technique_id"]: t for t in included_body["techniques"]}
    assert included["T1595"]["deprecated"] is True
