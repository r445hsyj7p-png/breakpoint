from app.models import (
    Capability,
    Control,
    Tactic,
    TacticDefaultMapping,
    Technique,
    TechniqueCapabilityMapping,
)
from scripts.seed import run as run_seed
from scripts.seed_data import (
    ALL_CAPABILITIES,
    KB,
    TACTIC_DEFAULTS,
    TACTIC_GROUPS,
    TACTIC_NAME_OVERRIDES,
)


def test_seed_populates_tactics_and_techniques(db_session):
    run_seed()

    assert db_session.query(Tactic).count() == 15
    assert db_session.query(Capability).count() == len(ALL_CAPABILITIES)
    assert db_session.query(Control).count() > 0
    assert db_session.query(TechniqueCapabilityMapping).count() == len(KB)
    assert db_session.query(TacticDefaultMapping).count() == len(TACTIC_DEFAULTS)

    # Jede Taktik aus dem Prototyp muss als eigene Zeile existieren — mit dem
    # ggf. per TACTIC_NAME_OVERRIDES aktualisierten Anzeigenamen (Abschnitt 10f).
    tactic_names = {t.name for t in db_session.query(Tactic).all()}
    expected_names = {TACTIC_NAME_OVERRIDES.get(name, name) for name in TACTIC_GROUPS}
    assert tactic_names == expected_names


def test_seed_is_idempotent(db_session):
    run_seed()
    first_count = db_session.query(Technique).count()
    run_seed()
    second_count = db_session.query(Technique).count()
    assert first_count == second_count


def test_sub_technique_parent_fallback(db_session):
    run_seed()
    sub = db_session.get(Technique, "T1078.004")
    assert sub is not None
    assert sub.parent_technique_id == "T1078"


def test_multi_tactic_technique_uses_earliest_kill_chain_tactic(db_session):
    """T1078 gehört im Prototyp zu vier Taktiken (Initial Access, Persistence,
    Privilege Escalation, Defense Evasion). Schritt 1 löst das deterministisch auf
    die früheste in Kill-Chain-Reihenfolge auf — siehe scripts/seed.py."""
    run_seed()
    technique = db_session.get(Technique, "T1078")
    assert technique.tactic_id == "initial-access"


def test_renamed_tactic_keeps_stable_id_but_shows_current_mitre_name(db_session):
    """Abschnitt 10f: MITRE hat 'Defense Evasion' in 'Stealth' umbenannt.
    Unsere interne tactic.id bleibt stabil ('defense-evasion'), nur der
    Anzeigename folgt MITRE."""
    run_seed()
    tactic = db_session.get(Tactic, "defense-evasion")
    assert tactic is not None
    assert tactic.name == "Stealth"


def test_new_defense_impairment_tactic_is_seeded(db_session):
    run_seed()
    tactic = db_session.get(Tactic, "defense-impairment")
    assert tactic is not None
    assert tactic.name == "Defense Impairment"
    assert db_session.get(TacticDefaultMapping, "defense-impairment") is not None


def test_reseed_self_heals_stale_tactic_name(db_session):
    """Der Re-Seed läuft idempotent bei jedem Container-Start (docker-
    entrypoint.sh) — er muss auch einen bereits gesäten, noch nicht
    umbenannten Anzeigenamen auf einer bestehenden Zeile korrigieren."""
    run_seed()
    tactic = db_session.get(Tactic, "defense-evasion")
    tactic.name = "Defense Evasion"
    db_session.commit()

    run_seed()

    db_session.expire_all()
    assert db_session.get(Tactic, "defense-evasion").name == "Stealth"
