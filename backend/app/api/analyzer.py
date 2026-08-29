from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.analyzer import AnalyzeRequest, AnalyzerResult
from app.services.analyzer import analyze
from app.services.parsing import parse_codes

router = APIRouter(prefix="/api", tags=["analyzer"])


@router.post("/analyze", response_model=AnalyzerResult)
def analyze_codes(payload: AnalyzeRequest, db: Session = Depends(get_db)) -> AnalyzerResult:
    """Zustandslose Analyse: T-Nummern rein, priorisierte Maßnahmen raus.
    Deckt den Analyzer-Tab ab, der im Prototyp ohne Engagement-Bindung
    funktioniert (docs/projektauftrag.md Abschnitt 10a.5)."""
    codes = parse_codes(payload.codes)
    return analyze(db, codes)
