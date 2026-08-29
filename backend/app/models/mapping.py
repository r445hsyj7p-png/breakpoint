import enum

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class MappingSource(str, enum.Enum):
    SPECIFIC = "specific"
    TACTIC_DEFAULT = "tactic_default"


class ImpactLevel(str, enum.Enum):
    NIEDRIG = "niedrig"
    MITTEL = "mittel"
    HOCH = "hoch"
    SEHR_HOCH = "sehr_hoch"


class EffortLevel(str, enum.Enum):
    NIEDRIG = "niedrig"
    MITTEL = "mittel"
    HOCH = "hoch"


class TechniqueCapabilityMapping(Base):
    """Spezifisches Mapping einer einzelnen Technik auf Capabilities/Controls
    (mapping_source='specific'). Taktik-weite Standardmappings liegen separat
    in tactic_default_mapping — siehe docs/projektauftrag.md Abschnitt 5."""

    __tablename__ = "technique_capability_mapping"
    __table_args__ = (UniqueConstraint("technique_id", name="uq_mapping_technique"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    technique_id: Mapped[str] = mapped_column(ForeignKey("technique.id"), nullable=False)
    mapping_source: Mapped[MappingSource] = mapped_column(
        Enum(MappingSource, name="mapping_source"), nullable=False, default=MappingSource.SPECIFIC
    )
    impact: Mapped[ImpactLevel] = mapped_column(Enum(ImpactLevel, name="impact_level"), nullable=False)
    effort: Mapped[EffortLevel] = mapped_column(Enum(EffortLevel, name="effort_level"), nullable=False)

    technique = relationship("Technique")
    capability_links: Mapped[list["TechniqueCapabilityMappingCapability"]] = relationship(
        back_populates="mapping", cascade="all, delete-orphan"
    )
    control_links: Mapped[list["TechniqueCapabilityMappingControl"]] = relationship(
        back_populates="mapping", cascade="all, delete-orphan"
    )


class TechniqueCapabilityMappingCapability(Base):
    """Join: welche Capabilities gehören zu einem technique_capability_mapping-Eintrag."""

    __tablename__ = "technique_capability_mapping_capability"

    mapping_id: Mapped[int] = mapped_column(
        ForeignKey("technique_capability_mapping.id"), primary_key=True
    )
    capability_id: Mapped[int] = mapped_column(ForeignKey("capability.id"), primary_key=True)

    mapping = relationship("TechniqueCapabilityMapping", back_populates="capability_links")
    capability = relationship("Capability")


class TechniqueCapabilityMappingControl(Base):
    """Join: welche Controls (Prevent/Detect/Respond) gehören zu einem Mapping-Eintrag."""

    __tablename__ = "technique_capability_mapping_control"

    mapping_id: Mapped[int] = mapped_column(
        ForeignKey("technique_capability_mapping.id"), primary_key=True
    )
    control_id: Mapped[int] = mapped_column(ForeignKey("control.id"), primary_key=True)

    mapping = relationship("TechniqueCapabilityMapping", back_populates="control_links")
    control = relationship("Control")
