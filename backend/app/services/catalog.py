"""Techniken-Katalog-Listing (docs/projektauftrag.md Abschnitt 10b.1).

Bewusst getrennt von app/services/analyzer.py: hier geht es nur um den
Mapping-*Status* aller Techniken für die Katalog-Übersicht (leichtgewichtig,
eine Abfrage für alle Techniken), nicht um die vollständige Fallback-Kette mit
Capabilities/Controls für konkret analysierte Codes.
"""

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, contains_eager

from app.models import Tactic, Technique, TechniqueCapabilityMapping
from app.schemas.techniques import TechniqueCatalogResult, TechniqueSummary


def list_techniques(
    db: Session,
    tactic_name: str | None = None,
    status: str | None = None,
    q: str | None = None,
    include_deprecated: bool = False,
) -> TechniqueCatalogResult:
    # Jede Zeile braucht ohnehin den Taktik-Namen (s.u.) — ein einziger Join,
    # dessen Ergebnis über contains_eager() sowohl fürs Filtern als auch fürs
    # Befüllen von technique.tactic wiederverwendet wird (kein Doppel-Join,
    # wie es joinedload() zusätzlich zu einem expliziten .join() erzeugen würde).
    query = db.query(Technique).join(Tactic).options(contains_eager(Technique.tactic))
    if not include_deprecated:
        # Soft-Delete-Prinzip (Abschnitt 5/10e.1) — analog dem active-Flag
        # bei portfolio_technology: standardmäßig ausgeblendet, nie hart
        # gelöscht, historische Findings/Reports bleiben referenzierbar.
        query = query.filter(Technique.deprecated.is_(False))
    if tactic_name:
        query = query.filter(Tactic.name == tactic_name)
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(
            or_(func.lower(Technique.id).like(like), func.lower(Technique.name).like(like))
        )
    techniques = query.order_by(Technique.id).all()

    # Eine einzige Abfrage statt einer Fallback-Kette pro Technik: das
    # tatsächliche mapping_source je Technik-ID lesen (nicht nur "existiert
    # eine Zeile" — seit Schritt 6 kann diese Zeile auch 'mitre_derived'
    # sein, nicht nur 'specific'; Regressionsfund analog resolve_technique(),
    # Abschnitt 6a.3 Punkt 5), dann in Python gegen die
    # (Sub-Technique -> parent_technique_id)-Beziehung abgleichen.
    mapping_source_by_technique_id = {
        technique_id: mapping_source.value
        for (technique_id, mapping_source) in db.query(
            TechniqueCapabilityMapping.technique_id, TechniqueCapabilityMapping.mapping_source
        ).all()
    }

    summaries = []
    for technique in techniques:
        own_source = mapping_source_by_technique_id.get(technique.id)
        if own_source is not None:
            mapping_source = own_source
        elif technique.parent_technique_id is not None and technique.parent_technique_id in mapping_source_by_technique_id:
            mapping_source = mapping_source_by_technique_id[technique.parent_technique_id]
        else:
            mapping_source = "tactic_default"
        summaries.append(
            TechniqueSummary(
                technique_id=technique.id,
                technique_name=technique.name,
                tactic_name=technique.tactic.name,
                mapping_source=mapping_source,
                deprecated=technique.deprecated,
            )
        )

    if status:
        summaries = [s for s in summaries if s.mapping_source == status]

    return TechniqueCatalogResult(techniques=summaries, total=len(summaries))
