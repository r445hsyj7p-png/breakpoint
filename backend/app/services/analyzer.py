"""Analyzer-Kernlogik: Mapping-Resolution (docs/projektauftrag.md Abschnitt 10a.3)
und Prioritätsalgorithmus (Abschnitt 10a.4)."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import TacticDefaultMapping, Technique, TechniqueCapabilityMapping
from app.schemas.analyzer import (
    AnalyzerResult,
    ControlRef,
    PrioritizedMeasure,
    TechniqueResult,
)
from app.services.portfolio import portfolio_fit_for_capabilities

IMPACT_RANK = {"niedrig": 1, "mittel": 2, "hoch": 3, "sehr_hoch": 4}
EFFORT_RANK = {"niedrig": 1, "mittel": 2, "hoch": 3}


@dataclass
class _MeasureAccumulator:
    control: ControlRef
    affected_technique_ids: list[str]
    max_impact_rank: int
    min_effort_rank: int


def _find_specific_mapping(db: Session, technique_id: str) -> TechniqueCapabilityMapping | None:
    return (
        db.query(TechniqueCapabilityMapping)
        .filter_by(technique_id=technique_id)
        .one_or_none()
    )


def resolve_technique(db: Session, technique_id: str) -> TechniqueResult | None:
    """Löst eine einzelne Technik-ID gemäß der korrigierten Fallback-Kette auf:
    exakter Treffer -> parent_technique_id-Traversal -> Taktik-Standard.
    Gibt None zurück, wenn die ID auch im Katalog nicht existiert (unknown)."""
    technique = db.get(Technique, technique_id)
    if technique is None:
        return None

    mapping = _find_specific_mapping(db, technique_id)
    resolved_via_technique_id = technique_id

    if mapping is None and technique.parent_technique_id is not None:
        mapping = _find_specific_mapping(db, technique.parent_technique_id)
        resolved_via_technique_id = technique.parent_technique_id

    if mapping is not None:
        capabilities = [link.capability.name for link in mapping.capability_links]
        controls = [
            ControlRef(id=link.control.id, category=link.control.category.value, label=link.control.label)
            for link in mapping.control_links
        ]
        return TechniqueResult(
            technique_id=technique_id,
            technique_name=technique.name,
            tactic_name=technique.tactic.name,
            mapping_source="specific",
            resolved_via_technique_id=resolved_via_technique_id,
            impact=mapping.impact.value,
            effort=mapping.effort.value,
            capabilities=capabilities,
            controls=controls,
            portfolio_fit=portfolio_fit_for_capabilities(db, capabilities),
        )

    default = db.get(TacticDefaultMapping, technique.tactic_id)
    if default is None:
        # Sollte nie eintreten: jede der 14 Taktiken wird beim Seeden mit einem
        # Standardmapping versehen (scripts/seed.py). Ein fehlender Eintrag ist
        # ein Datenintegritätsfehler, keine unbekannte Nutzereingabe — daher
        # bewusst ein harter Fehler statt stiller Einordnung als unknown_code.
        raise RuntimeError(
            f"Kein tactic_default_mapping für Taktik '{technique.tactic_id}' "
            f"(Technik '{technique_id}') — Seed-Daten unvollständig."
        )

    capabilities = [link.capability.name for link in default.capability_links]
    controls = [
        ControlRef(id=link.control.id, category=link.control.category.value, label=link.control.label)
        for link in default.control_links
    ]
    return TechniqueResult(
        technique_id=technique_id,
        technique_name=technique.name,
        tactic_name=technique.tactic.name,
        mapping_source="tactic_default",
        resolved_via_technique_id=None,
        impact=default.impact.value,
        effort=default.effort.value,
        capabilities=capabilities,
        controls=controls,
        portfolio_fit=portfolio_fit_for_capabilities(db, capabilities),
    )


def _prioritize(techniques: list[TechniqueResult]) -> list[PrioritizedMeasure]:
    """Aggregiert pro eindeutigem Control über alle analysierten Techniken
    hinweg und sortiert nach Kettenabdeckung, dann Impact, dann Effort
    (docs/projektauftrag.md Abschnitt 10a.4 — v1, bewusst einfach)."""
    accumulators: dict[int, _MeasureAccumulator] = {}

    for technique in techniques:
        impact_rank = IMPACT_RANK[technique.impact]
        effort_rank = EFFORT_RANK[technique.effort]
        for control_ref in technique.controls:
            acc = accumulators.get(control_ref.id)
            if acc is None:
                accumulators[control_ref.id] = _MeasureAccumulator(
                    control=control_ref,
                    affected_technique_ids=[technique.technique_id],
                    max_impact_rank=impact_rank,
                    min_effort_rank=effort_rank,
                )
            else:
                if technique.technique_id not in acc.affected_technique_ids:
                    acc.affected_technique_ids.append(technique.technique_id)
                acc.max_impact_rank = max(acc.max_impact_rank, impact_rank)
                acc.min_effort_rank = min(acc.min_effort_rank, effort_rank)

    # control.id als letztes, stabiles Tie-Break-Kriterium: ohne das würde bei
    # exakt gleicher Kettenabdeckung/Impact/Effort die zufällige Einfüge-
    # reihenfolge (abhängig davon, in welcher Reihenfolge der Aufrufer die
    # Techniken übergeben hat) über die Reihenfolge entscheiden — dieselbe
    # Menge Techniken müsste unabhängig von ihrer Eingabereihenfolge dieselbe
    # Priorisierung ergeben.
    ordered = sorted(
        accumulators.values(),
        key=lambda a: (-len(a.affected_technique_ids), -a.max_impact_rank, a.min_effort_rank, a.control.id),
    )

    return [
        PrioritizedMeasure(
            control_id=acc.control.id,
            category=acc.control.category,
            label=acc.control.label,
            priority_rank=rank,
            chain_coverage_count=len(acc.affected_technique_ids),
            affected_technique_ids=acc.affected_technique_ids,
        )
        for rank, acc in enumerate(ordered, start=1)
    ]


def analyze(db: Session, codes: list[str]) -> AnalyzerResult:
    techniques: list[TechniqueResult] = []
    unknown_codes: list[str] = []

    for code in codes:
        result = resolve_technique(db, code)
        if result is None:
            unknown_codes.append(code)
        else:
            techniques.append(result)

    return AnalyzerResult(
        input_codes=codes,
        techniques=techniques,
        unknown_codes=unknown_codes,
        prioritized_measures=_prioritize(techniques),
    )
