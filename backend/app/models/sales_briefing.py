import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class SalesBriefingStatus(str, enum.Enum):
    PENDING = "pending"
    READY = "ready"
    FLAGGED_FOR_REVIEW = "flagged_for_review"
    FAILED = "failed"


class SalesBriefing(Base):
    """LLM-generiertes Sales-Briefing für ein Engagement — versioniert durch
    append-only (jede Generierung legt eine neue Zeile an, keine Zeile wird
    überschrieben), siehe docs/projektauftrag.md Abschnitt 10d.1."""

    __tablename__ = "sales_briefing"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagement.id"), nullable=False)
    status: Mapped[SalesBriefingStatus] = mapped_column(
        Enum(SalesBriefingStatus, name="sales_briefing_status"),
        nullable=False,
        default=SalesBriefingStatus.PENDING,
    )
    model_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Serialisiertes SalesBriefing-Pydantic-Schema (Abschnitt 7), nullable bis fertig.
    content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Freitext bis Schritt 7 (kein Nutzerkonzept) — analog
    # portfolio_technology_history.changed_by (Abschnitt 10c.1).
    reviewed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    engagement = relationship("Engagement")
