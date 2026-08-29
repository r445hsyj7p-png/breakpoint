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
) -> TechniqueCatalogResult:
    # Jede Zeile braucht ohnehin den Taktik-Namen (s.u.) — ein einziger Join,
    # dessen Ergebnis über contains_eager() sowohl fürs Filtern als auch fürs
    # Befüllen von technique.tactic wiederverwendet wird (kein Doppel-Join,
    # wie es joinedload() zusätzlich zu einem expliziten .join() erzeugen würde).
    query = db.query(Technique).join(Tactic).options(contains_eager(Technique.tactic))
    if tactic_name:
        query = query.filter(Tactic.name == tactic_name)
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(
            or_(func.lower(Technique.id).like(like), func.lower(Technique.name).like(like))
        )
    techniques = query.order_by(Technique.id).all()

    # Eine einzige Abfrage statt einer Fallback-Kette pro Technik: alle
    # technique_ids mit spezifischem Mapping, dann in Python gegen die
    # (Sub-Technique -> parent_technique_id)-Beziehung abgleichen.
    specific_ids = {
        technique_id for (technique_id,) in db.query(TechniqueCapabilityMapping.technique_id).all()
    }

    summaries = []
    for technique in techniques:
        has_specific = technique.id in specific_ids or (
            technique.parent_technique_id is not None
            and technique.parent_technique_id in specific_ids
        )
        summaries.append(
            TechniqueSummary(
                technique_id=technique.id,
                technique_name=technique.name,
                tactic_name=technique.tactic.name,
                mapping_source="specific" if has_specific else "tactic_default",
            )
        )

    if status:
        summaries = [s for s in summaries if s.mapping_source == status]

    return TechniqueCatalogResult(techniques=summaries, total=len(summaries))
