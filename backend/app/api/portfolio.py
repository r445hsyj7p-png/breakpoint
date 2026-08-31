from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Capability, PortfolioTechnology
from app.schemas.portfolio import (
    CoverageResult,
    PortfolioTechnologyCreate,
    PortfolioTechnologyHistoryEntry,
    PortfolioTechnologyRead,
    PortfolioTechnologyUpdate,
)
from app.services.portfolio import (
    compute_coverage,
    create_technology,
    deactivate_technology,
    get_history,
    list_technologies,
    to_read_model,
    update_technology,
)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


def _get_technology_or_404(db: Session, technology_id: int) -> PortfolioTechnology:
    technology = db.get(PortfolioTechnology, technology_id)
    if technology is None:
        raise HTTPException(status_code=404, detail="Portfolio-Technologie nicht gefunden")
    return technology


def _validate_capability_ids_exist(db: Session, capability_ids: list[int] | None) -> None:
    """Verhindert einen rohen 500er (FK-Verletzung beim Commit), falls der
    Aufrufer eine nicht existierende Capability-ID schickt — anders als bei
    frei getippten T-Nummern (Abschnitt 10a.5) ist das hier kein normaler
    Tippfehler-Fall, sondern ein fehlerhafter API-Aufruf, also ein harter
    422-Fehler statt stillem Filtern."""
    if not capability_ids:
        return
    existing = {
        cid for (cid,) in db.query(Capability.id).filter(Capability.id.in_(capability_ids)).all()
    }
    unknown = sorted(set(capability_ids) - existing)
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unbekannte capability_ids: {unknown}")


@router.get("/technologies", response_model=list[PortfolioTechnologyRead])
def get_technologies(
    include_inactive: bool = False, db: Session = Depends(get_db)
) -> list[PortfolioTechnologyRead]:
    technologies = list_technologies(db, include_inactive=include_inactive)
    return [to_read_model(t) for t in technologies]


@router.post("/technologies", response_model=PortfolioTechnologyRead, status_code=201)
def post_technology(
    payload: PortfolioTechnologyCreate, db: Session = Depends(get_db)
) -> PortfolioTechnologyRead:
    _validate_capability_ids_exist(db, payload.capability_ids)
    technology = create_technology(db, payload)
    return to_read_model(technology)


@router.patch("/technologies/{technology_id}", response_model=PortfolioTechnologyRead)
def patch_technology(
    technology_id: int, payload: PortfolioTechnologyUpdate, db: Session = Depends(get_db)
) -> PortfolioTechnologyRead:
    technology = _get_technology_or_404(db, technology_id)
    _validate_capability_ids_exist(db, payload.capability_ids)
    technology = update_technology(db, technology, payload)
    return to_read_model(technology)


@router.post("/technologies/{technology_id}/deactivate", response_model=PortfolioTechnologyRead)
def post_deactivate_technology(
    technology_id: int, db: Session = Depends(get_db)
) -> PortfolioTechnologyRead:
    technology = _get_technology_or_404(db, technology_id)
    technology = deactivate_technology(db, technology)
    return to_read_model(technology)


@router.get("/technologies/{technology_id}/history", response_model=list[PortfolioTechnologyHistoryEntry])
def get_technology_history(
    technology_id: int, db: Session = Depends(get_db)
) -> list[PortfolioTechnologyHistoryEntry]:
    _get_technology_or_404(db, technology_id)
    return get_history(db, technology_id)


@router.get("/coverage", response_model=CoverageResult)
def get_coverage(db: Session = Depends(get_db)) -> CoverageResult:
    return compute_coverage(db)
