from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, get_db
from app.models import Engagement, SalesBriefingStatus
from app.models import SalesBriefing as SalesBriefingRow
from app.schemas.sales_briefing import MarkReviewedRequest, SalesBriefingRead
from app.services.sales_briefing import generate_sales_briefing

router = APIRouter(tags=["sales-briefing"])


def _get_engagement_or_404(db: Session, engagement_id: int) -> Engagement:
    engagement = db.get(Engagement, engagement_id)
    if engagement is None:
        raise HTTPException(status_code=404, detail="Engagement nicht gefunden")
    return engagement


def _get_briefing_or_404(db: Session, briefing_id: int) -> SalesBriefingRow:
    briefing = db.get(SalesBriefingRow, briefing_id)
    if briefing is None:
        raise HTTPException(status_code=404, detail="Sales-Briefing nicht gefunden")
    return briefing


def _run_generation_job(engagement_id: int, briefing_id: int) -> None:
    """Läuft in BackgroundTasks außerhalb des Request-Lebenszyklus — braucht
    daher eine eigene DB-Session statt der (nach Response-Versand
    geschlossenen) Request-Session aus Depends(get_db)."""
    db = SessionLocal()
    try:
        generate_sales_briefing(db, engagement_id, briefing_id)
    finally:
        db.close()


@router.post(
    "/api/engagements/{engagement_id}/sales-briefing",
    response_model=SalesBriefingRead,
    status_code=202,
)
def post_sales_briefing(
    engagement_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> SalesBriefingRow:
    """Legt sofort eine pending-Zeile an und gibt 202 zurück; die eigentliche
    Generierung läuft asynchron im Hintergrund (Abschnitt 10d.2, Frage 2 —
    bewusst ohne Task-Queue-Infrastruktur, mit dokumentierter Grenze)."""
    _get_engagement_or_404(db, engagement_id)

    briefing = SalesBriefingRow(engagement_id=engagement_id, status=SalesBriefingStatus.PENDING)
    db.add(briefing)
    db.commit()
    db.refresh(briefing)

    background_tasks.add_task(_run_generation_job, engagement_id, briefing.id)
    return briefing


@router.get(
    "/api/engagements/{engagement_id}/sales-briefing",
    response_model=SalesBriefingRead,
)
def get_latest_sales_briefing(engagement_id: int, db: Session = Depends(get_db)) -> SalesBriefingRow:
    _get_engagement_or_404(db, engagement_id)
    briefing = (
        db.query(SalesBriefingRow)
        .filter_by(engagement_id=engagement_id)
        .order_by(SalesBriefingRow.id.desc())
        .first()
    )
    if briefing is None:
        raise HTTPException(status_code=404, detail="Noch kein Sales-Briefing für dieses Engagement")
    return briefing


@router.get(
    "/api/engagements/{engagement_id}/sales-briefings",
    response_model=list[SalesBriefingRead],
)
def list_sales_briefings(engagement_id: int, db: Session = Depends(get_db)) -> list[SalesBriefingRow]:
    _get_engagement_or_404(db, engagement_id)
    return (
        db.query(SalesBriefingRow)
        .filter_by(engagement_id=engagement_id)
        .order_by(SalesBriefingRow.id.desc())
        .all()
    )


@router.post(
    "/api/sales-briefings/{briefing_id}/mark-reviewed",
    response_model=SalesBriefingRead,
)
def post_mark_reviewed(
    briefing_id: int, payload: MarkReviewedRequest, db: Session = Depends(get_db)
) -> SalesBriefingRow:
    briefing = _get_briefing_or_404(db, briefing_id)
    briefing.reviewed_by = payload.reviewed_by
    briefing.reviewed_at = datetime.now(UTC)
    db.commit()
    db.refresh(briefing)
    return briefing
