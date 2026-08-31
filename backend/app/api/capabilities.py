from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Capability
from app.schemas.capability import CapabilityRead

router = APIRouter(prefix="/api", tags=["capabilities"])


@router.get("/capabilities", response_model=list[CapabilityRead])
def get_capabilities(db: Session = Depends(get_db)) -> list[Capability]:
    """Referenzliste aller Capabilities mit ID — nötig für die Capability-
    Mehrfachauswahl im Portfolio-Formular (docs/projektauftrag.md Abschnitt
    10c.5), da die Coverage-Antwort nur Namen liefert, keine IDs."""
    return db.query(Capability).order_by(Capability.name).all()
