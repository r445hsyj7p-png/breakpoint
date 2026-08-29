from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Engagement, Finding, Technique
from app.schemas.analyzer import (
    AnalyzerResult,
    EngagementCreate,
    EngagementRead,
    FindingsCreate,
    FindingsCreateResult,
)
from app.services.analyzer import analyze
from app.services.parsing import parse_codes

router = APIRouter(prefix="/api/engagements", tags=["engagements"])


def _get_engagement_or_404(db: Session, engagement_id: int) -> Engagement:
    engagement = db.get(Engagement, engagement_id)
    if engagement is None:
        raise HTTPException(status_code=404, detail="Engagement nicht gefunden")
    return engagement


@router.post("", response_model=EngagementRead, status_code=201)
def create_engagement(payload: EngagementCreate, db: Session = Depends(get_db)) -> Engagement:
    engagement = Engagement(name=payload.name, external_ref=payload.external_ref)
    db.add(engagement)
    db.commit()
    db.refresh(engagement)
    return engagement


@router.post("/{engagement_id}/findings", response_model=FindingsCreateResult)
def add_findings(
    engagement_id: int, payload: FindingsCreate, db: Session = Depends(get_db)
) -> FindingsCreateResult:
    """Fügt T-Nummern als Findings zu einem Engagement hinzu. Codes, die nicht
    im Techniken-Katalog existieren, werden nicht persistiert (die finding-
    Tabelle referenziert technique_id per Fremdschlüssel) und stattdessen
    sichtbar als unknown_codes zurückgegeben (Abschnitt 10a.5)."""
    _get_engagement_or_404(db, engagement_id)
    codes = parse_codes(payload.codes)

    known_ids = {
        technique_id
        for (technique_id,) in db.query(Technique.id).filter(Technique.id.in_(codes)).all()
    }
    added: list[str] = []
    unknown: list[str] = []
    for code in codes:
        if code not in known_ids:
            unknown.append(code)
            continue
        exists = (
            db.query(Finding)
            .filter_by(engagement_id=engagement_id, technique_id=code)
            .one_or_none()
        )
        if exists is None:
            db.add(Finding(engagement_id=engagement_id, technique_id=code))
        added.append(code)

    db.commit()
    return FindingsCreateResult(added_technique_ids=added, unknown_codes=unknown)


@router.get("/{engagement_id}/analysis", response_model=AnalyzerResult)
def get_engagement_analysis(engagement_id: int, db: Session = Depends(get_db)) -> AnalyzerResult:
    """Berechnet das AnalyzerResult zur Laufzeit aus den finding-Zeilen des
    Engagements — keine materialisierte recommendation-Tabelle (bewusste
    Entscheidung, Abschnitt 10a.1)."""
    _get_engagement_or_404(db, engagement_id)
    codes = [
        technique_id
        for (technique_id,) in db.query(Finding.technique_id)
        .filter_by(engagement_id=engagement_id)
        .distinct()
        .order_by(Finding.technique_id)
        .all()
    ]
    return analyze(db, codes)
