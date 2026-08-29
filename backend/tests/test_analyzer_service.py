from app.models import Technique
from app.services.analyzer import analyze, resolve_technique
from scripts.seed import run as run_seed


def test_specific_mapping_resolves_directly(db_session):
    run_seed()
    result = resolve_technique(db_session, "T1078")
    assert result is not None
    assert result.mapping_source == "specific"
    assert result.resolved_via_technique_id == "T1078"
    assert "MFA" in result.capabilities


def test_unmapped_technique_falls_back_to_tactic_default(db_session):
    run_seed()
    # T1595 (Active Scanning, Reconnaissance) hat kein KB-Eintrag.
    result = resolve_technique(db_session, "T1595")
    assert result is not None
    assert result.mapping_source == "tactic_default"
    assert result.resolved_via_technique_id is None
    assert result.tactic_name == "Reconnaissance"


def test_unknown_code_resolves_to_none(db_session):
    run_seed()
    assert resolve_technique(db_session, "T9999.999") is None


def test_analyze_reports_unknown_codes_without_failing(db_session):
    run_seed()
    result = analyze(db_session, ["T1078", "T9999.999"])
    assert result.unknown_codes == ["T9999.999"]
    assert [t.technique_id for t in result.techniques] == ["T1078"]


def test_sub_technique_falls_back_to_parent_not_to_unrelated_sibling(db_session):
    """Regressionstest für den im Prototyp gefundenen Bug (docs/projektauftrag.md
    Abschnitt 5): getMapping() im Prototyp sucht per Präfix-Vergleich nach
    IRGENDEINEM KB-Eintrag mit gleicher Basis-ID und kann so fälschlich das
    Mapping eines unverwandten Geschwister-Codes übernehmen. Die korrigierte
    Logik darf ausschließlich über parent_technique_id traversieren.

    Kein Fall im aktuellen Seed-Datensatz eignet sich dafür 1:1 (jede geseedete
    Sub-Technique hat bereits ihr eigenes KB-Mapping) — daher wird hier gezielt
    eine synthetische Sub-Technique ohne eigenes Mapping angelegt, deren Parent
    (T1078) ein spezifisches Mapping hat, das sich klar von dem eines
    tatsächlichen Geschwister-Codes (T1078.004) unterscheidet."""
    run_seed()
    synthetic_child = Technique(
        id="T1078.099",
        name="Valid Accounts: Synthetic Test Sub-Technique",
        tactic_id="initial-access",
        parent_technique_id="T1078",
    )
    db_session.add(synthetic_child)
    db_session.commit()

    result = resolve_technique(db_session, "T1078.099")
    assert result is not None
    assert result.mapping_source == "specific"
    assert result.resolved_via_technique_id == "T1078"
    # T1078 hat "Identity Monitoring" als Capability, T1078.004 stattdessen
    # "Cloud Identity Monitoring" — das unterscheidet die beiden Mappings
    # eindeutig voneinander.
    assert "Identity Monitoring" in result.capabilities
    assert "Cloud Identity Monitoring" not in result.capabilities


def test_prioritization_aggregates_shared_control_across_techniques(db_session):
    """T1078 und T1078.004 teilen sich den Control 'MFA erzwingen' (prevent).
    chain_coverage_count muss beide Techniken zählen und die Maßnahme muss vor
    Maßnahmen liegen, die nur eine einzelne Technik abdecken."""
    run_seed()
    result = analyze(db_session, ["T1078", "T1078.004"])
    shared = next(m for m in result.prioritized_measures if m.label == "MFA erzwingen")
    assert shared.chain_coverage_count == 2
    assert set(shared.affected_technique_ids) == {"T1078", "T1078.004"}
    assert shared.priority_rank == 1


def test_prioritization_ranking_is_independent_of_input_order(db_session):
    run_seed()
    forward = analyze(db_session, ["T1078", "T1078.004"])
    backward = analyze(db_session, ["T1078.004", "T1078"])
    forward_ranked_labels = [m.label for m in forward.prioritized_measures]
    backward_ranked_labels = [m.label for m in backward.prioritized_measures]
    assert forward_ranked_labels == backward_ranked_labels
