from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Tactic(Base):
    """Eine MITRE-ATT&CK-Enterprise-Taktik (Reconnaissance … Impact, plus per
    Abschnitt 10f ergänzte/umbenannte Taktiken wie Defense Impairment) —
    Anzahl bewusst nicht hartkodiert, da Breakpoint sich immer an der
    aktuellen MITRE-Taxonomie orientiert."""

    __tablename__ = "tactic"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    mitre_order: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
