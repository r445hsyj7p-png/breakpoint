from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Finding(Base):
    """Eine beobachtete Technik innerhalb eines Engagements (ein Eintrag pro
    T-Nummer-Fund) — siehe docs/projektauftrag.md Abschnitt 5."""

    __tablename__ = "finding"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagement.id"), nullable=False)
    technique_id: Mapped[str] = mapped_column(ForeignKey("technique.id"), nullable=False)
    raw_source_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)

    engagement = relationship("Engagement", back_populates="findings")
    technique = relationship("Technique")
