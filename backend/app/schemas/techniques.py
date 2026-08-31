from pydantic import BaseModel

from app.schemas.analyzer import MappingSourceLiteral


class TechniqueSummary(BaseModel):
    technique_id: str
    technique_name: str
    tactic_name: str
    mapping_source: MappingSourceLiteral
    deprecated: bool


class TechniqueCatalogResult(BaseModel):
    techniques: list[TechniqueSummary]
    total: int
