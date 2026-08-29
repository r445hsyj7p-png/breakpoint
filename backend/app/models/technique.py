from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Technique(Base):
    """Eine MITRE-ATT&CK-Technik oder Sub-Technique, z. B. 'T1078' oder 'T1078.004'."""

    __tablename__ = "technique"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    tactic_id: Mapped[str] = mapped_column(ForeignKey("tactic.id"), nullable=False)
    parent_technique_id: Mapped[str | None] = mapped_column(
        ForeignKey("technique.id"), nullable=True
    )

    tactic = relationship("Tactic")
    parent_technique = relationship("Technique", remote_side=[id])
