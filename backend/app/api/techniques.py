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
    include_deprecated: bool = False,
    db: Session = Depends(get_db),
) -> TechniqueCatalogResult:
    """Techniken-Katalog mit Mapping-Status je Technik, für den 'Alle
    Techniken'-Tab (docs/projektauftrag.md Abschnitt 10b.1). `tactic` filtert
    nach Taktik-Name, `status` nach 'specific'/'tactic_default'/'mitre_derived',
    `q` durchsucht Technik-ID und -Name (case-insensitive). Von MITRE als
    deprecated markierte Techniken (Abschnitt 10e) sind standardmäßig
    ausgeblendet, `include_deprecated=true` zeigt sie zusätzlich an."""
    return list_techniques(db, tactic_name=tactic, status=status, q=q, include_deprecated=include_deprecated)
