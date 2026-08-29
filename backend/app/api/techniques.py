from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.techniques import TechniqueCatalogResult
from app.services.catalog import list_techniques

router = APIRouter(prefix="/api", tags=["techniques"])


@router.get("/techniques", response_model=TechniqueCatalogResult)
def get_techniques(
    tactic: str | None = None,
    status: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
) -> TechniqueCatalogResult:
    """Techniken-Katalog mit Mapping-Status je Technik, für den 'Alle
    Techniken'-Tab (docs/projektauftrag.md Abschnitt 10b.1). `tactic` filtert
    nach Taktik-Name, `status` nach 'specific'/'tactic_default', `q` durchsucht
    Technik-ID und -Name (case-insensitive)."""
    return list_techniques(db, tactic_name=tactic, status=status, q=q)
