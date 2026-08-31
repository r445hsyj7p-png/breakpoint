"""PydanticAI-Ein-/Ausgabeschemas für das Sales-Briefing (docs/projektauftrag.md
Abschnitt 7/10d) — exakt wie in Abschnitt 7 skizziert, plus die API-seitigen
Lese-/Anfrageschemas für die sales_briefing-Tabelle."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SalesBriefingStatusLiteral = Literal["pending", "ready", "flagged_for_review", "failed"]


class MassnahmeArgumentation(BaseModel):
    massnahme: str
    kunden_nutzen: str = Field(description="1-2 Sätze, Geschäftssprache, keine Fachbegriffe")
    risiko_ohne_massnahme: str
    einwand_antizipation: str = Field(description="Ein wahrscheinlicher Kundeneinwand + Gegenargument")


class SalesBriefing(BaseModel):
    executive_summary: str = Field(description="3-4 Sätze, für Geschäftsführung")
    top_massnahmen: list[MassnahmeArgumentation] = Field(max_length=5)
    naechster_schritt: str


class SalesBriefingRead(BaseModel):
    id: int
    engagement_id: int
    status: SalesBriefingStatusLiteral
    model_version: str | None
    content: SalesBriefing | None
    error_message: str | None
    created_at: datetime
    generated_at: datetime | None
    reviewed_by: str | None
    reviewed_at: datetime | None

    model_config = {"from_attributes": True}


class MarkReviewedRequest(BaseModel):
    reviewed_by: str | None = None
