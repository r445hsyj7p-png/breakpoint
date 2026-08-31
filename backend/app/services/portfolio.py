"""Portfolio-CRUD, Änderungshistorie und Coverage/Gap-Berechnung
(docs/projektauftrag.md Abschnitt 10c). `techs_for_capabilities()` ist die
gemeinsame Nachschlage-Logik für den Portfolio-Tab (Coverage-Matrix) UND für
die Portfolio-Fit-Integration im Analyzer (Abschnitt 10c.2) — eine
Berechnung, kein Sonderfall.
"""

from sqlalchemy.orm import Session

from app.models import (
    Capability,
    PortfolioTechnology,
    PortfolioTechnologyCapability,
    PortfolioTechnologyHistory,
)
from app.schemas.portfolio import (
    CoverageResult,
    CoverageRow,
    PortfolioTechnologyCreate,
    PortfolioTechnologyRead,
    PortfolioTechnologyUpdate,
)


def techs_for_capabilities(db: Session, capability_names: list[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {name: [] for name in capability_names}
    if not capability_names:
        return result

    rows = (
        db.query(Capability.name, PortfolioTechnology.name)
        .join(
            PortfolioTechnologyCapability,
            PortfolioTechnologyCapability.capability_id == Capability.id,
        )
        .join(
            PortfolioTechnology,
            PortfolioTechnology.id == PortfolioTechnologyCapability.portfolio_technology_id,
        )
        .filter(Capability.name.in_(capability_names), PortfolioTechnology.active.is_(True))
        .all()
    )
    for capability_name, technology_name in rows:
        result[capability_name].append(technology_name)
    return result


def portfolio_fit_for_capabilities(db: Session, capability_names: list[str]) -> list[str]:
    """Union aller Portfolio-Technologien, die mindestens eine der gegebenen
    Capabilities abdecken — analog matchPortfolio() aus dem Prototyp."""
    by_capability = techs_for_capabilities(db, capability_names)
    seen: dict[str, None] = {}
    for technology_names in by_capability.values():
        for name in technology_names:
            seen[name] = None
    return list(seen.keys())


def compute_coverage(db: Session) -> CoverageResult:
    all_capabilities = db.query(Capability).order_by(Capability.name).all()
    by_capability = techs_for_capabilities(db, [c.name for c in all_capabilities])
    rows = [
        CoverageRow(capability=c.name, covering_technologies=by_capability[c.name])
        for c in all_capabilities
    ]
    gaps = [c.name for c in all_capabilities if not by_capability[c.name]]
    return CoverageResult(rows=rows, gaps=gaps)


def to_read_model(technology: PortfolioTechnology) -> PortfolioTechnologyRead:
    return PortfolioTechnologyRead(
        id=technology.id,
        name=technology.name,
        type=technology.type,
        active=technology.active,
        capabilities=sorted(link.capability.name for link in technology.capability_links),
    )


def list_technologies(db: Session, include_inactive: bool = False) -> list[PortfolioTechnology]:
    query = db.query(PortfolioTechnology)
    if not include_inactive:
        query = query.filter(PortfolioTechnology.active.is_(True))
    return query.order_by(PortfolioTechnology.name).all()


def _record_history(db: Session, technology_id: int, field: str, old_value: str | None, new_value: str | None) -> None:
    if old_value == new_value:
        return
    db.add(
        PortfolioTechnologyHistory(
            portfolio_technology_id=technology_id,
            changed_by=None,  # kein Nutzerkonzept vor Schritt 7 (Abschnitt 10c)
            field_changed=field,
            old_value=old_value,
            new_value=new_value,
        )
    )


def _capability_names_display(db: Session, capability_ids: list[int]) -> str:
    if not capability_ids:
        return ""
    names = [
        name
        for (name,) in db.query(Capability.name).filter(Capability.id.in_(capability_ids)).all()
    ]
    return ", ".join(sorted(names))


def create_technology(db: Session, payload: PortfolioTechnologyCreate) -> PortfolioTechnology:
    technology = PortfolioTechnology(name=payload.name, type=payload.type, active=True)
    db.add(technology)
    db.flush()

    # dedupliziert: doppelte IDs im Payload würden sonst denselben
    # zusammengesetzten Primärschlüssel zweimal einfügen wollen und beim
    # Commit mit einem IntegrityError abbrechen.
    capability_ids = sorted(set(payload.capability_ids))
    for capability_id in capability_ids:
        db.add(
            PortfolioTechnologyCapability(
                portfolio_technology_id=technology.id, capability_id=capability_id
            )
        )

    _record_history(db, technology.id, "name", None, payload.name)
    _record_history(db, technology.id, "type", None, payload.type)
    if capability_ids:
        _record_history(db, technology.id, "capabilities", None, _capability_names_display(db, capability_ids))

    db.commit()
    db.refresh(technology)
    return technology


def update_technology(
    db: Session, technology: PortfolioTechnology, payload: PortfolioTechnologyUpdate
) -> PortfolioTechnology:
    if payload.name is not None and payload.name != technology.name:
        _record_history(db, technology.id, "name", technology.name, payload.name)
        technology.name = payload.name

    if payload.type is not None and payload.type != technology.type:
        _record_history(db, technology.id, "type", technology.type, payload.type)
        technology.type = payload.type

    if payload.capability_ids is not None:
        old_ids = sorted(link.capability_id for link in technology.capability_links)
        new_ids = sorted(set(payload.capability_ids))
        if old_ids != new_ids:
            old_display = _capability_names_display(db, old_ids)
            new_display = _capability_names_display(db, new_ids)
            _record_history(db, technology.id, "capabilities", old_display, new_display)
            for link in list(technology.capability_links):
                db.delete(link)
            db.flush()
            for capability_id in new_ids:
                db.add(
                    PortfolioTechnologyCapability(
                        portfolio_technology_id=technology.id, capability_id=capability_id
                    )
                )

    db.commit()
    db.refresh(technology)
    return technology


def deactivate_technology(db: Session, technology: PortfolioTechnology) -> PortfolioTechnology:
    if technology.active:
        _record_history(db, technology.id, "active", "true", "false")
        technology.active = False
        db.commit()
        db.refresh(technology)
    return technology


def get_history(db: Session, technology_id: int) -> list[PortfolioTechnologyHistory]:
    return (
        db.query(PortfolioTechnologyHistory)
        .filter_by(portfolio_technology_id=technology_id)
        .order_by(PortfolioTechnologyHistory.id.desc())
        .all()
    )
