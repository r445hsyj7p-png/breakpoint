"""API-Schemas für den MITRE-STIX-Import (docs/projektauftrag.md Abschnitt
10e.3). Bilden die von app/services/mitre_import.py::compute_diff()
erzeugte Diff-Struktur 1:1 typisiert ab, statt sie als loses dict an die
API-Antwort durchzureichen."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ImportSourceLiteral = Literal["github_raw", "taxii", "manual_upload"]
ImportBatchStatusLiteral = Literal["diff_pending", "diff_ready", "applied", "rolled_back", "failed"]


class MitigationEntry(BaseModel):
    m_id: str
    mitigation_name: str
    control_label: str


class NewTechniqueDiffItem(BaseModel):
    technique_id: str
    name: str
    tactic_id: str
    parent_technique_id: str | None
    stix_id: str


class FieldChange(BaseModel):
    old: str | None
    new: str | None


class UpdatedTechniqueDiffItem(BaseModel):
    technique_id: str
    changes: dict[str, FieldChange]


class DeprecatedTechniqueDiffItem(BaseModel):
    technique_id: str
    name: str


class UnmappedTacticPhaseItem(BaseModel):
    technique_id: str
    name: str
    phase_names: list[str]


class MitigationCandidateDiffItem(BaseModel):
    technique_id: str
    mitigations: list[MitigationEntry]
    capabilities: list[str]
    control_labels: list[str]
    impact: str
    effort: str


class ConflictDiffItem(BaseModel):
    technique_id: str
    mitigations: list[MitigationEntry]
    reason: str


class SkippedMitigationItem(BaseModel):
    m_id: str
    mitigation_name: str


class ImportDiff(BaseModel):
    bundle_version: str | None
    new_techniques: list[NewTechniqueDiffItem]
    updated_techniques: list[UpdatedTechniqueDiffItem]
    newly_deprecated_techniques: list[DeprecatedTechniqueDiffItem]
    unmapped_tactic_phase_techniques: list[UnmappedTacticPhaseItem]
    mitigation_candidates: list[MitigationCandidateDiffItem]
    skipped_mitigations_without_crosswalk: list[SkippedMitigationItem]
    conflicts: list[ConflictDiffItem]


class ImportBatchRead(BaseModel):
    id: int
    source: ImportSourceLiteral
    source_ref: str | None
    bundle_version: str | None
    status: ImportBatchStatusLiteral
    triggered_by: str | None
    diff_snapshot: ImportDiff | None
    error_message: str | None
    created_at: datetime
    applied_at: datetime | None
    rolled_back_at: datetime | None

    model_config = {"from_attributes": True}


class ApplySelection(BaseModel):
    technique_ids: list[str] = []
    mitigation_technique_ids: list[str] = []
