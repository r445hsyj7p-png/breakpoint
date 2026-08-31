import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ImportSource(str, enum.Enum):
    GITHUB_RAW = "github_raw"
    TAXII = "taxii"
    MANUAL_UPLOAD = "manual_upload"


class ImportBatchStatus(str, enum.Enum):
    DIFF_PENDING = "diff_pending"
    DIFF_READY = "diff_ready"
    APPLIED = "applied"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class TechniqueImportBatch(Base):
    """Protokolliert einen MITRE-STIX-Import (Abschnitt 6a.2 Punkt 4 / 10e.1):
    Fetch+Diff laufen als Hintergrund-Job (analog Sales-Briefing, Schritt 5),
    das Ergebnis liegt hier zwischengespeichert, bis ein Admin es explizit
    übernimmt. pre_apply_snapshot trägt den Vorzustand für einen einstufigen
    Rollback (kein voller Versionsbaum, Abschnitt 10e.1 — YAGNI)."""

    __tablename__ = "technique_import_batch"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[ImportSource] = mapped_column(Enum(ImportSource, name="import_source"), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)
    bundle_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[ImportBatchStatus] = mapped_column(
        Enum(ImportBatchStatus, name="import_batch_status"),
        nullable=False,
        default=ImportBatchStatus.DIFF_PENDING,
    )
    # Freitext bis Schritt 7 (kein Nutzerkonzept) — analog
    # portfolio_technology_history.changed_by / sales_briefing.reviewed_by.
    triggered_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    diff_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    pre_apply_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rolled_back_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
