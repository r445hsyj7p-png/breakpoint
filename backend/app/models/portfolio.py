from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class PortfolioTechnology(Base):
    """Eine eigene Technologie/Leistung, herstellerneutralen Capabilities
    zugeordnet — siehe docs/projektauftrag.md Abschnitt 5/6a.1."""

    __tablename__ = "portfolio_technology"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    type: Mapped[str] = mapped_column(String(128), nullable=False)
    # Kein Hard-Delete (Abschnitt 6a.1) — Deaktivieren setzt active=false,
    # damit historische Recommendations/Reports nicht verwaisen.
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    capability_links: Mapped[list["PortfolioTechnologyCapability"]] = relationship(
        back_populates="portfolio_technology", cascade="all, delete-orphan"
    )


class PortfolioTechnologyCapability(Base):
    """Join: welche Capabilities deckt eine Portfolio-Technologie ab. Bewusst
    eine Tabelle statt Freitext (Abschnitt 6a.1) — sonst driften Capability-
    Namen auseinander und die Coverage-Matrix wird unbrauchbar."""

    __tablename__ = "portfolio_technology_capability"

    portfolio_technology_id: Mapped[int] = mapped_column(
        ForeignKey("portfolio_technology.id"), primary_key=True
    )
    capability_id: Mapped[int] = mapped_column(ForeignKey("capability.id"), primary_key=True)

    portfolio_technology = relationship("PortfolioTechnology", back_populates="capability_links")
    capability = relationship("Capability")


class PortfolioTechnologyHistory(Base):
    """Änderungsprotokoll pro Technologie (Abschnitt 6a.1) — wichtig, da sich
    das direkt auf laufende Kundenempfehlungen auswirkt. `changed_by` bleibt
    NULL, bis Schritt 7 ein echtes Nutzerkonzept einführt (Abschnitt 10c)."""

    __tablename__ = "portfolio_technology_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    portfolio_technology_id: Mapped[int] = mapped_column(
        ForeignKey("portfolio_technology.id"), nullable=False
    )
    changed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    field_changed: Mapped[str] = mapped_column(String(64), nullable=False)
    old_value: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    new_value: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    portfolio_technology = relationship("PortfolioTechnology")
