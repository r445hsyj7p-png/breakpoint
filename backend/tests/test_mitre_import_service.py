import json
from pathlib import Path

from app.models import (
    Control,
    ImportBatchStatus,
    ImportSource,
    MappingSource,
    Technique,
    TechniqueCapabilityMapping,
    TechniqueImportBatch,
)
from app.services.mitre_import import (
    InvalidGitRefError,
    _sort_new_techniques_by_dependency,
    apply_batch,
    compute_diff,
    fetch_bundle_bytes,
    parse_bundle,
    rollback_batch,
)
from scripts.seed import run as run_seed

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "mitre_stix_sample.json"


def _load_fixture_bytes() -> bytes:
    return FIXTURE_PATH.read_bytes()


def test_parse_bundle_extracts_techniques_mitigations_and_relationships():
    bundle = parse_bundle(_load_fixture_bytes())

    assert bundle.bundle_version == "99.9"
    assert len(bundle.techniques) == 7
    # Legacy revoked "mitigation" mit T-artiger ID darf nicht als Mitigation
    # erscheinen (Abschnitt 10e Punkt 3).
    assert len(bundle.mitigations) == 3

    sub = bundle.techniques["attack-pattern--new-001-sub"]
    assert sub.technique_id == "T9001.001"
    assert sub.parent_stix_id == "attack-pattern--new-001"

    assert bundle.mitigates["attack-pattern--new-001"] == [
        "course-of-action--m1032",
        "course-of-action--m1013",
    ]


def test_fetch_bundle_bytes_rejects_path_traversal_ref():
    """Regressionstest: ref kommt unauthentifiziert vom Admin-Endpoint und
    landet direkt in der GitHub-Raw-URL — muss vor Interpolation gegen ein
    enges Muster geprüft werden (Abschnitt 10e Review-Fund)."""
    for bad_ref in ["../../evil/repo/main", "master/../../x", "", "has space", "a\nb"]:
        try:
            fetch_bundle_bytes(ref=bad_ref)
            raise AssertionError(f"sollte InvalidGitRefError auslösen für {bad_ref!r}")
        except InvalidGitRefError:
            pass


def test_fetch_bundle_bytes_accepts_normal_refs_before_network_call(monkeypatch):
    """Ein gültiger Ref darf nicht an der Validierung scheitern — prüft nur
    das Muster, kein echter Netzwerkzugriff (httpx.Client wird gepatcht)."""
    captured_urls = []

    class _FakeResponse:
        content = b"{}"

        def raise_for_status(self):
            pass

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url):
            captured_urls.append(url)
            return _FakeResponse()

    monkeypatch.setattr("app.services.mitre_import.httpx.Client", _FakeClient)
    fetch_bundle_bytes(ref="release/19.2")
    assert captured_urls == [
        "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/release/19.2/enterprise-attack/enterprise-attack.json"
    ]


def test_parse_bundle_ignores_revoked_mitigates_relationship():
    """Regressionstest: MITRE kann eine einzelne mitigates-Zuordnung
    zurückziehen, ohne die Technik oder Mitigation selbst zu revoken (nur
    die Relationship trägt revoked=true). Eine solche zurückgezogene
    Zuordnung darf nicht als Mitigation-Kandidat wiederauftauchen."""
    bundle_dict = {
        "objects": [
            {
                "type": "attack-pattern",
                "id": "attack-pattern--x",
                "name": "X",
                "revoked": False,
                "x_mitre_deprecated": False,
                "external_references": [{"source_name": "mitre-attack", "external_id": "T9005"}],
                "kill_chain_phases": [{"kill_chain_name": "mitre-attack", "phase_name": "persistence"}],
            },
            {
                "type": "course-of-action",
                "id": "course-of-action--x",
                "name": "X Mitigation",
                "revoked": False,
                "x_mitre_deprecated": False,
                "external_references": [{"source_name": "mitre-attack", "external_id": "M1099"}],
            },
            {
                "type": "relationship",
                "id": "relationship--revoked",
                "relationship_type": "mitigates",
                "source_ref": "course-of-action--x",
                "target_ref": "attack-pattern--x",
                "revoked": True,
            },
        ]
    }
    bundle = parse_bundle(json.dumps(bundle_dict).encode())
    assert bundle.mitigates == {}


def test_compute_diff_against_seeded_db(db_session):
    run_seed()
    bundle = parse_bundle(_load_fixture_bytes())
    diff = compute_diff(db_session, bundle)

    new_ids = {item["technique_id"] for item in diff["new_techniques"]}
    assert new_ids == {"T9001", "T9001.001", "T9003", "T9004"}
    sub_item = next(item for item in diff["new_techniques"] if item["technique_id"] == "T9001.001")
    assert sub_item["parent_technique_id"] == "T9001"

    updated = next(item for item in diff["updated_techniques"] if item["technique_id"] == "T1078")
    assert updated["changes"]["name"]["new"] == "Valid Accounts (Renamed In Fixture)"
    assert "stix_id" in updated["changes"]

    deprecated_ids = {item["technique_id"] for item in diff["newly_deprecated_techniques"]}
    assert deprecated_ids == {"T1003"}

    # T9002 hat eine frei erfundene, nie existierende Taktik-Phase — bleibt
    # unmappbar. T9003 ("stealth") und T9004 ("defense-impairment") lösen
    # dagegen über TACTIC_PHASE_ALIASES korrekt auf (Abschnitt 10f).
    unmapped_ids = {item["technique_id"] for item in diff["unmapped_tactic_phase_techniques"]}
    assert unmapped_ids == {"T9002"}


def test_compute_diff_resolves_renamed_and_new_tactic_via_alias(db_session):
    """Abschnitt 10f: 'stealth' (MITREs Umbenennung von 'Defense Evasion')
    löst auf unsere stabile tactic.id 'defense-evasion' auf; 'defense-
    impairment' (neue 15. Taktik) löst auf die gleichnamige neue Taktik."""
    run_seed()
    bundle = parse_bundle(_load_fixture_bytes())
    diff = compute_diff(db_session, bundle)

    by_id = {item["technique_id"]: item for item in diff["new_techniques"]}
    assert by_id["T9003"]["tactic_id"] == "defense-evasion"
    assert by_id["T9004"]["tactic_id"] == "defense-impairment"

    candidate = next(c for c in diff["mitigation_candidates"] if c["technique_id"] == "T9001")
    assert candidate["capabilities"] == ["MFA"]
    assert candidate["control_labels"] == ["MFA erzwingen"]
    assert {m["m_id"] for m in candidate["mitigations"]} == {"M1032"}  # M1013 hat keinen Crosswalk-Treffer

    skipped_ids = {item["m_id"] for item in diff["skipped_mitigations_without_crosswalk"]}
    assert "M1013" in skipped_ids

    conflict = next(c for c in diff["conflicts"] if c["technique_id"] == "T1078")
    assert conflict["reason"] == "bestehendes spezifisches Mapping wird nicht überschrieben"


def _make_diff_ready_batch(db_session) -> TechniqueImportBatch:
    run_seed()
    bundle = parse_bundle(_load_fixture_bytes())
    diff = compute_diff(db_session, bundle)
    batch = TechniqueImportBatch(
        source=ImportSource.MANUAL_UPLOAD,
        status=ImportBatchStatus.DIFF_READY,
        diff_snapshot=diff,
        bundle_version=diff["bundle_version"],
    )
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)
    return batch


def test_apply_batch_creates_new_techniques_and_mitigation_mapping(db_session):
    batch = _make_diff_ready_batch(db_session)

    apply_batch(db_session, batch, technique_ids=["T9001", "T9001.001"], mitigation_technique_ids=["T9001"])

    technique = db_session.get(Technique, "T9001")
    assert technique is not None
    assert technique.tactic_id == "persistence"
    sub_technique = db_session.get(Technique, "T9001.001")
    assert sub_technique.parent_technique_id == "T9001"

    mapping = db_session.query(TechniqueCapabilityMapping).filter_by(technique_id="T9001").one()
    assert mapping.mapping_source == MappingSource.MITRE_DERIVED
    assert [link.capability.name for link in mapping.capability_links] == ["MFA"]


def test_sort_new_techniques_by_dependency_orders_parent_before_child():
    """Regressionstest: bundle.techniques (und damit new_techniques) folgt
    der rohen STIX-Objektreihenfolge, die eine Sub-Technique vor ihrer
    neuen Eltern-Technik auflisten kann. Ohne Sortierung würde
    apply_batch()s INSERT-Reihenfolge die FK-Constraint verletzen
    (empirisch verifiziert: SQLAlchemy ordnet roh gesetzte
    Self-Referential-FK-Spalten nicht automatisch um)."""
    child_first = [
        {"technique_id": "T9001.001", "parent_technique_id": "T9001"},
        {"technique_id": "T9001", "parent_technique_id": None},
    ]
    ordered = _sort_new_techniques_by_dependency(child_first)
    assert [item["technique_id"] for item in ordered] == ["T9001", "T9001.001"]


def test_apply_batch_inserts_parent_before_child_even_in_reversed_diff_order(db_session):
    """Integrationstest der obigen Sortierlogik direkt in apply_batch():
    manipuliert die new_techniques-Liste des Diffs auf Kind-vor-Eltern, wie
    es ein echtes STIX-Bundle liefern könnte, und prüft, dass apply_batch()
    trotzdem ohne FK-Fehler durchläuft."""
    batch = _make_diff_ready_batch(db_session)
    new_techniques = batch.diff_snapshot["new_techniques"]
    reversed_order = sorted(new_techniques, key=lambda item: item["technique_id"] != "T9001.001")
    batch.diff_snapshot = {**batch.diff_snapshot, "new_techniques": reversed_order}

    apply_batch(db_session, batch, technique_ids=["T9001", "T9001.001"], mitigation_technique_ids=[])

    assert db_session.get(Technique, "T9001") is not None
    assert db_session.get(Technique, "T9001.001").parent_technique_id == "T9001"


def test_apply_batch_nulls_parent_ref_when_new_parent_technique_was_not_selected(db_session):
    """Regressionstest (per Live-E2E-Check entdeckt): 'neue Technik
    übernehmen' ist pro Technik einzeln abwählbar. Wählt ein Admin die
    Sub-Technique T9001.001 aus, aber nicht ihre ebenfalls neue
    Eltern-Technik T9001, würde parent_technique_id='T9001' auf eine nie
    angelegte Zeile zeigen und die FK-Constraint verletzen. apply_batch()
    muss die Sub-Technique stattdessen ohne Eltern-Verknüpfung anlegen."""
    batch = _make_diff_ready_batch(db_session)

    apply_batch(db_session, batch, technique_ids=["T9001.001"], mitigation_technique_ids=[])

    assert db_session.get(Technique, "T9001") is None
    sub_technique = db_session.get(Technique, "T9001.001")
    assert sub_technique is not None
    assert sub_technique.parent_technique_id is None


def test_apply_batch_skips_mitigation_candidate_whose_technique_was_not_selected(db_session):
    """Regressionstest: Diff-Ansicht erlaubt unabhängige Checkboxen für
    'neue Technik übernehmen' und 'Mitigation übernehmen'. Wählt ein Admin
    nur die Mitigation für T9001 aus, ohne die Technik selbst zu
    übernehmen, darf apply_batch() keinen FK-Fehler werfen, sondern muss
    den Kandidaten stillschweigend überspringen."""
    batch = _make_diff_ready_batch(db_session)

    apply_batch(db_session, batch, technique_ids=[], mitigation_technique_ids=["T9001"])

    assert db_session.get(Technique, "T9001") is None
    assert db_session.query(TechniqueCapabilityMapping).filter_by(technique_id="T9001").one_or_none() is None
    assert batch.status == ImportBatchStatus.APPLIED


def test_apply_batch_never_overwrites_existing_specific_mapping(db_session):
    """T1078 hat ein conflicts-Eintrag im Diff (bestehendes 'specific'-
    Mapping) — selbst wenn ein Aufrufer versucht, es trotzdem als Mitigation
    zu übernehmen (z. B. per Bug im Frontend), darf apply_batch() das
    defensiv verhindern (Abschnitt 6a.3 Punkt 6)."""
    batch = _make_diff_ready_batch(db_session)
    before = db_session.query(TechniqueCapabilityMapping).filter_by(technique_id="T1078").one()
    before_capabilities = sorted(link.capability.name for link in before.capability_links)

    apply_batch(db_session, batch, technique_ids=["T1078"], mitigation_technique_ids=["T1078"])

    after = db_session.query(TechniqueCapabilityMapping).filter_by(technique_id="T1078").one()
    assert after.mapping_source == MappingSource.SPECIFIC
    assert sorted(link.capability.name for link in after.capability_links) == before_capabilities
    # Technique-Update (Name/stix_id) wird trotzdem übernommen — nur das
    # Mapping bleibt unangetastet.
    assert after.technique.name == "Valid Accounts (Renamed In Fixture)"


def test_apply_batch_reuses_existing_control_for_shared_label(db_session):
    """M1032 hat control_label 'MFA erzwingen' — derselbe Control, der im
    Seed-KB bereits für T1078 existiert. Der Import darf keinen doppelten
    Control mit demselben (category, label) anlegen (UniqueConstraint),
    sondern muss den bestehenden wiederverwenden (Abschnitt 10e.2)."""
    run_seed()
    existing_count = db_session.query(Control).filter_by(category="prevent", label="MFA erzwingen").count()
    assert existing_count == 1

    bundle = parse_bundle(_load_fixture_bytes())
    diff = compute_diff(db_session, bundle)
    batch = TechniqueImportBatch(
        source=ImportSource.MANUAL_UPLOAD, status=ImportBatchStatus.DIFF_READY, diff_snapshot=diff
    )
    db_session.add(batch)
    db_session.commit()

    apply_batch(db_session, batch, technique_ids=["T9001"], mitigation_technique_ids=["T9001"])

    assert db_session.query(Control).filter_by(category="prevent", label="MFA erzwingen").count() == 1


def test_apply_batch_marks_technique_deprecated(db_session):
    batch = _make_diff_ready_batch(db_session)
    apply_batch(db_session, batch, technique_ids=["T1003"], mitigation_technique_ids=[])
    assert db_session.get(Technique, "T1003").deprecated is True


def test_apply_batch_rejects_non_diff_ready_batch(db_session):
    run_seed()
    batch = TechniqueImportBatch(source=ImportSource.MANUAL_UPLOAD, status=ImportBatchStatus.DIFF_PENDING)
    db_session.add(batch)
    db_session.commit()

    try:
        apply_batch(db_session, batch, technique_ids=[], mitigation_technique_ids=[])
        raise AssertionError("sollte ValueError auslösen")
    except ValueError:
        pass


def test_rollback_restores_pre_apply_state_for_new_technique_and_mapping(db_session):
    batch = _make_diff_ready_batch(db_session)
    apply_batch(db_session, batch, technique_ids=["T9001", "T9001.001"], mitigation_technique_ids=["T9001"])
    assert db_session.get(Technique, "T9001") is not None

    rollback_batch(db_session, batch)

    assert db_session.get(Technique, "T9001") is None
    assert db_session.get(Technique, "T9001.001") is None
    assert db_session.query(TechniqueCapabilityMapping).filter_by(technique_id="T9001").one_or_none() is None
    assert batch.status == ImportBatchStatus.ROLLED_BACK
    assert batch.rolled_back_at is not None


def test_rollback_restores_updated_technique_fields(db_session):
    batch = _make_diff_ready_batch(db_session)
    original_name = db_session.get(Technique, "T1078").name
    apply_batch(db_session, batch, technique_ids=["T1078"], mitigation_technique_ids=[])
    assert db_session.get(Technique, "T1078").name == "Valid Accounts (Renamed In Fixture)"

    rollback_batch(db_session, batch)

    technique = db_session.get(Technique, "T1078")
    assert technique.name == original_name
    assert technique.stix_id is None


def test_rollback_restores_deprecated_flag(db_session):
    batch = _make_diff_ready_batch(db_session)
    apply_batch(db_session, batch, technique_ids=["T1003"], mitigation_technique_ids=[])
    assert db_session.get(Technique, "T1003").deprecated is True

    rollback_batch(db_session, batch)

    assert db_session.get(Technique, "T1003").deprecated is False


def test_rollback_rejects_non_applied_batch(db_session):
    batch = _make_diff_ready_batch(db_session)
    try:
        rollback_batch(db_session, batch)
        raise AssertionError("sollte ValueError auslösen")
    except ValueError:
        pass
