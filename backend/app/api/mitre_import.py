from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, get_db
from app.models import ImportBatchStatus, ImportSource, TechniqueImportBatch
from app.schemas.mitre_import import ApplySelection, ImportBatchRead
from app.services.mitre_import import DEFAULT_REF, apply_batch, rollback_batch, run_fetch_and_diff

router = APIRouter(prefix="/api/admin/mitre-import", tags=["mitre-import"])


def _get_batch_or_404(db: Session, batch_id: int) -> TechniqueImportBatch:
    batch = db.get(TechniqueImportBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Import-Batch nicht gefunden")
    return batch


def _run_fetch_job(batch_id: int, raw_bytes: bytes | None, ref: str) -> None:
    """Läuft in BackgroundTasks außerhalb des Request-Lebenszyklus — braucht
    daher eine eigene DB-Session statt der (nach Response-Versand
    geschlossenen) Request-Session aus Depends(get_db), analog
    app/api/sales_briefing.py."""
    db = SessionLocal()
    try:
        run_fetch_and_diff(db, batch_id, raw_bytes=raw_bytes, ref=ref)
    finally:
        db.close()


@router.post("/fetch", response_model=ImportBatchRead, status_code=202)
def post_fetch(
    background_tasks: BackgroundTasks,
    triggered_by: str | None = None,
    ref: str = DEFAULT_REF,
    db: Session = Depends(get_db),
) -> TechniqueImportBatch:
    """Legt sofort eine diff_pending-Zeile an und gibt 202 zurück; Fetch (vom
    offiziellen GitHub-Raw-Bundle) + Parsing + Diff-Berechnung laufen
    asynchron im Hintergrund (Abschnitt 10e Punkt 2)."""
    batch = TechniqueImportBatch(
        source=ImportSource.GITHUB_RAW,
        source_ref=ref,
        status=ImportBatchStatus.DIFF_PENDING,
        triggered_by=triggered_by,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    background_tasks.add_task(_run_fetch_job, batch.id, None, ref)
    return batch


@router.post("/upload", response_model=ImportBatchRead, status_code=202)
async def post_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    triggered_by: str | None = None,
    db: Session = Depends(get_db),
) -> TechniqueImportBatch:
    """Wie /fetch, aber mit einer manuell hochgeladenen STIX-Bundle-Datei
    statt eines GitHub-Fetches (Abschnitt 6a.2 Punkt 1 — Fallback, falls der
    Server keinen Internetzugriff hat)."""
    raw_bytes = await file.read()
    batch = TechniqueImportBatch(
        source=ImportSource.MANUAL_UPLOAD,
        source_ref=file.filename,
        status=ImportBatchStatus.DIFF_PENDING,
        triggered_by=triggered_by,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    background_tasks.add_task(_run_fetch_job, batch.id, raw_bytes, DEFAULT_REF)
    return batch


@router.get("/batches", response_model=list[ImportBatchRead])
def list_batches(db: Session = Depends(get_db)) -> list[TechniqueImportBatch]:
    return db.query(TechniqueImportBatch).order_by(TechniqueImportBatch.id.desc()).all()


@router.get("/batches/{batch_id}", response_model=ImportBatchRead)
def get_batch(batch_id: int, db: Session = Depends(get_db)) -> TechniqueImportBatch:
    return _get_batch_or_404(db, batch_id)


@router.post("/batches/{batch_id}/apply", response_model=ImportBatchRead)
def post_apply_batch(
    batch_id: int, payload: ApplySelection, db: Session = Depends(get_db)
) -> TechniqueImportBatch:
    batch = _get_batch_or_404(db, batch_id)
    try:
        apply_batch(db, batch, payload.technique_ids, payload.mitigation_technique_ids)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.refresh(batch)
    return batch


@router.post("/batches/{batch_id}/rollback", response_model=ImportBatchRead)
def post_rollback_batch(batch_id: int, db: Session = Depends(get_db)) -> TechniqueImportBatch:
    batch = _get_batch_or_404(db, batch_id)

    # Nur der jeweils zuletzt angewendete Batch darf zurückgerollt werden
    # (Abschnitt 10e.1 — einstufiger Rollback, kein Versionsbaum). Ein
    # neuerer, bereits angewendeter Batch würde sonst einen inkonsistenten
    # Zwischenzustand erzeugen.
    latest_applied = (
        db.query(TechniqueImportBatch)
        .filter(TechniqueImportBatch.status == ImportBatchStatus.APPLIED)
        .order_by(TechniqueImportBatch.id.desc())
        .first()
    )
    if latest_applied is None or latest_applied.id != batch.id:
        raise HTTPException(
            status_code=409,
            detail="Nur der zuletzt angewendete Batch kann zurückgerollt werden",
        )

    try:
        rollback_batch(db, batch)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.refresh(batch)
    return batch
