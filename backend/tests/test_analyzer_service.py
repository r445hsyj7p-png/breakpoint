from app.models import Capability, PortfolioTechnology, PortfolioTechnologyCapability, Technique
from app.services.analyzer import analyze, resolve_technique
from scripts.seed import run as run_seed


def _add_portfolio_technology(db, name: str, capability_names: list[str]) -> None:
    technology = PortfolioTechnology(name=name, type="Test", active=True)
    db.add(technology)
    db.flush()
    for cap_name in capability_names:
        capability_id = db.query(Capability.id).filter_by(name=cap_name).scalar()
        db.add(
            PortfolioTechnologyCapability(portfolio_technology_id=technology.id, capability_id=capability_id)
        )
    db.commit()


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


def test_portfolio_fit_is_empty_without_portfolio_data(db_session):
    run_seed()
    result = resolve_technique(db_session, "T1078")
    assert result.portfolio_fit == []


def test_portfolio_fit_lists_covering_technologies(db_session):
    """docs/projektauftrag.md Abschnitt 10c.2: portfolio_fit wird aus aktiven
    Portfolio-Technologien befüllt, die eine der Technik-Capabilities abdecken."""
    run_seed()
    _add_portfolio_technology(db_session, "Okta", ["MFA", "Conditional Access"])
    _add_portfolio_technology(db_session, "Cortex XDR", ["EDR"])

    result = resolve_technique(db_session, "T1078")  # capabilities: MFA, Conditional Access, PAM, Identity Monitoring
    assert result.portfolio_fit == ["Okta"]

    unrelated = resolve_technique(db_session, "T1055")  # capabilities: EDR, Application Control
    assert unrelated.portfolio_fit == ["Cortex XDR"]


def test_portfolio_fit_never_influences_priority_rank(db_session):
    """Nicht-verhandelbares Prinzip aus Abschnitt 2: Portfolio-Fit ist reine
    Zusatzinformation und darf priority_rank nie beeinflussen."""
    run_seed()
    without_portfolio = analyze(db_session, ["T1078", "T1078.004", "T1003"])
    ranking_without = [(m.label, m.priority_rank) for m in without_portfolio.prioritized_measures]

    _add_portfolio_technology(db_session, "Okta", ["MFA"])

    with_portfolio = analyze(db_session, ["T1078", "T1078.004", "T1003"])
    ranking_with = [(m.label, m.priority_rank) for m in with_portfolio.prioritized_measures]

    assert ranking_without == ranking_with
