from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.finding import Finding


class Engagement(Base):
    """Ein Red-Team-/Pentest-Engagement, gegen das T-Nummern (Findings)
    gesammelt und analysiert werden — siehe docs/projektauftrag.md Abschnitt 5."""

    __tablename__ = "engagement"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    external_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Kein festes Status-Vokabular in Schritt 2 vorgegeben (Abschnitt 5) — bewusst
    # als einfaches String-Feld statt vorschneller ENUM, bis ein echter
    # Status-Workflow gebraucht wird (YAGNI).
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="offen")

    findings: Mapped[list["Finding"]] = relationship(back_populates="engagement", cascade="all, delete-orphan")
