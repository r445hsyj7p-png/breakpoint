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
from app.services.mitre_import import apply_batch, compute_diff, parse_bundle, rollback_batch
from scripts.seed import run as run_seed

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "mitre_stix_sample.json"


def _load_fixture_bytes() -> bytes:
    return FIXTURE_PATH.read_bytes()


def test_parse_bundle_extracts_techniques_mitigations_and_relationships():
    bundle = parse_bundle(_load_fixture_bytes())

    assert bundle.bundle_version == "99.9"
    assert len(bundle.techniques) == 5
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


def test_compute_diff_against_seeded_db(db_session):
    run_seed()
    bundle = parse_bundle(_load_fixture_bytes())
    diff = compute_diff(db_session, bundle)

    new_ids = {item["technique_id"] for item in diff["new_techniques"]}
    assert new_ids == {"T9001", "T9001.001"}
    sub_item = next(item for item in diff["new_techniques"] if item["technique_id"] == "T9001.001")
    assert sub_item["parent_technique_id"] == "T9001"

    updated = next(item for item in diff["updated_techniques"] if item["technique_id"] == "T1078")
    assert updated["changes"]["name"]["new"] == "Valid Accounts (Renamed In Fixture)"
    assert "stix_id" in updated["changes"]

    deprecated_ids = {item["technique_id"] for item in diff["newly_deprecated_techniques"]}
    assert deprecated_ids == {"T1003"}

    unmapped_ids = {item["technique_id"] for item in diff["unmapped_tactic_phase_techniques"]}
    assert unmapped_ids == {"T9002"}

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
    assert [link.control.label for link in mapping.control_links] == ["MFA erzwingen"]

    assert batch.status == ImportBatchStatus.APPLIED
    assert batch.applied_at is not None


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
