from app.models import (
    Capability,
    Control,
    Tactic,
    TacticDefaultMapping,
    Technique,
    TechniqueCapabilityMapping,
)
from scripts.seed import run as run_seed
from scripts.seed_data import ALL_CAPABILITIES, KB, TACTIC_DEFAULTS, TACTIC_GROUPS


def test_seed_populates_tactics_and_techniques(db_session):
    run_seed()

    assert db_session.query(Tactic).count() == 14
    assert db_session.query(Capability).count() == len(ALL_CAPABILITIES)
    assert db_session.query(Control).count() > 0
    assert db_session.query(TechniqueCapabilityMapping).count() == len(KB)
    assert db_session.query(TacticDefaultMapping).count() == len(TACTIC_DEFAULTS)

    # Jede Taktik aus dem Prototyp muss als eigene Zeile existieren.
    tactic_names = {t.name for t in db_session.query(Tactic).all()}
    assert tactic_names == set(TACTIC_GROUPS.keys())


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
