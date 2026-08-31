from sqlalchemy import Boolean, ForeignKey, String
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
    # Soft-Delete-Prinzip (Abschnitt 5): eine von MITRE als deprecated
    # markierte Technik wird nie hart gelöscht, damit historische
    # Findings/Reports nicht verwaisen (Abschnitt 10e.1).
    deprecated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Interne STIX-UUID (z. B. "attack-pattern--...), getrennt von der
    # öffentlichen T-Nummer — nötig, um Relationships beim nächsten Import
    # wiederzufinden, ohne dass sich technique.id ändern muss (Abschnitt 10e.1).
    # unique statt nur indiziert: zwei Technique-Zeilen dürfen nie auf
    # dieselbe STIX-Uuid zeigen, sonst wird die Diff-Zuordnung mehrdeutig.
    stix_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)

    tactic = relationship("Tactic")
    parent_technique = relationship("Technique", remote_side=[id])
