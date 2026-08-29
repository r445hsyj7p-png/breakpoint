from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Tactic(Base):
    """Eine der 14 MITRE-ATT&CK-Enterprise-Taktiken (Reconnaissance … Impact)."""

    __tablename__ = "tactic"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    mitre_order: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
