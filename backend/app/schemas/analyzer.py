"""Das kanonische Analyzer-Output-Schema (docs/projektauftrag.md Abschnitt 2a/10a.2).

Wird unverändert sowohl von der Analyst-UI gerendert als auch später 1:1 als
Input für den PydanticAI-Sales-Agent (Schritt 5) verwendet — deshalb keine
UI-spezifischen Kurzformen und kein Feld, das nur einer der beiden
Nutzergruppen dient.
"""

from typing import Literal

from pydantic import BaseModel, Field

MappingSourceLiteral = Literal["specific", "tactic_default"]
ImpactLiteral = Literal["niedrig", "mittel", "hoch", "sehr_hoch"]
EffortLiteral = Literal["niedrig", "mittel", "hoch"]
ControlCategoryLiteral = Literal["prevent", "detect", "respond"]


class ControlRef(BaseModel):
    id: int
    category: ControlCategoryLiteral
    label: str


class TechniqueResult(BaseModel):
    technique_id: str
    technique_name: str
    tactic_name: str
    mapping_source: MappingSourceLiteral
    # None bei tactic_default; sonst die Technik, deren Mapping tatsächlich
    # griff — bei direktem Treffer sie selbst, bei Sub-Technique-Fallback ihre
    # Basistechnik. Macht die Herkunft einer Empfehlung vollständig
    # nachvollziehbar, ohne die mapping_source-ENUM aufzublähen.
    resolved_via_technique_id: str | None
    impact: ImpactLiteral
    effort: EffortLiteral
    capabilities: list[str]
    controls: list[ControlRef]
    # Platzhalter bis Schritt 4 (Portfolio-Modul) — Feld existiert bereits,
    # damit sich die Schnittstelle später nicht ändert.
    portfolio_fit: list[str] = []


class PrioritizedMeasure(BaseModel):
    control_id: int
    category: ControlCategoryLiteral
    label: str
    priority_rank: int
    chain_coverage_count: int
    affected_technique_ids: list[str]


class AnalyzerResult(BaseModel):
    input_codes: list[str]
    techniques: list[TechniqueResult]
    # Codes, die auch im Katalog nicht existieren — sichtbar, nie
    # stillschweigend verworfen (Prinzip "keine Sackgassen", Abschnitt 2a).
    unknown_codes: list[str]
    prioritized_measures: list[PrioritizedMeasure]


class AnalyzeRequest(BaseModel):
    codes: str  # Freitext/CSV, wird serverseitig geparst (siehe app/services/parsing.py)


class EngagementCreate(BaseModel):
    name: str = Field(min_length=1)
    external_ref: str | None = None


class EngagementRead(BaseModel):
    id: int
    name: str
    external_ref: str | None
    status: str

    model_config = {"from_attributes": True}


class FindingsCreate(BaseModel):
    codes: str


class FindingsCreateResult(BaseModel):
    added_technique_ids: list[str]
    unknown_codes: list[str]
