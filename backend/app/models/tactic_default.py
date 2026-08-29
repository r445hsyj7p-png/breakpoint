from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mapping import EffortLevel, ImpactLevel


class TacticDefaultMapping(Base):
    """Taktik-Standardmapping: jede der 14 Taktiken bekommt eine Basis-Empfehlung,
    damit jede Technik mindestens ein Mapping hat (mapping_source='tactic_default').
    Eigenständige Tabelle statt nullable technique_id — siehe docs/projektauftrag.md
    Abschnitt 5 ('tactic_default_mapping als eigene Tabelle')."""

    __tablename__ = "tactic_default_mapping"

    tactic_id: Mapped[str] = mapped_column(ForeignKey("tactic.id"), primary_key=True)
    impact: Mapped[ImpactLevel] = mapped_column(Enum(ImpactLevel, name="impact_level"), nullable=False)
    effort: Mapped[EffortLevel] = mapped_column(Enum(EffortLevel, name="effort_level"), nullable=False)

    tactic = relationship("Tactic")
    capability_links: Mapped[list["TacticDefaultMappingCapability"]] = relationship(
        back_populates="tactic_default", cascade="all, delete-orphan"
    )
    control_links: Mapped[list["TacticDefaultMappingControl"]] = relationship(
        back_populates="tactic_default", cascade="all, delete-orphan"
    )


class TacticDefaultMappingCapability(Base):
    __tablename__ = "tactic_default_mapping_capability"

    tactic_id: Mapped[str] = mapped_column(
        ForeignKey("tactic_default_mapping.tactic_id"), primary_key=True
    )
    capability_id: Mapped[int] = mapped_column(ForeignKey("capability.id"), primary_key=True)

    tactic_default = relationship("TacticDefaultMapping", back_populates="capability_links")
    capability = relationship("Capability")


class TacticDefaultMappingControl(Base):
    __tablename__ = "tactic_default_mapping_control"

    tactic_id: Mapped[str] = mapped_column(
        ForeignKey("tactic_default_mapping.tactic_id"), primary_key=True
    )
    control_id: Mapped[int] = mapped_column(ForeignKey("control.id"), primary_key=True)

    tactic_default = relationship("TacticDefaultMapping", back_populates="control_links")
    control = relationship("Control")
