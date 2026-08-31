from datetime import datetime

from pydantic import BaseModel, Field


class PortfolioTechnologyCreate(BaseModel):
    name: str = Field(min_length=1)
    type: str = Field(min_length=1)
    capability_ids: list[int] = []


class PortfolioTechnologyUpdate(BaseModel):
    """Alle Felder optional (PATCH-Semantik) — nur mitgeschickte Felder werden
    geändert und lösen jeweils einen eigenen History-Eintrag aus."""

    name: str | None = Field(default=None, min_length=1)
    type: str | None = Field(default=None, min_length=1)
    capability_ids: list[int] | None = None


class PortfolioTechnologyRead(BaseModel):
    id: int
    name: str
    type: str
    active: bool
    capabilities: list[str]


class PortfolioTechnologyHistoryEntry(BaseModel):
    id: int
    changed_by: str | None
    changed_at: datetime
    field_changed: str
    old_value: str | None
    new_value: str | None


class CoverageRow(BaseModel):
    capability: str
    covering_technologies: list[str]


class CoverageResult(BaseModel):
    rows: list[CoverageRow]
    gaps: list[str]
