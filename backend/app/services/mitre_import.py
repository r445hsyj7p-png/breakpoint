"""MITRE-STIX-Import: Fetch, Parsing, Diff-Berechnung, Übernahme und Rollback
(docs/projektauftrag.md Abschnitt 6a.2/6a.3/10e).

parse_bundle() ist bewusst eine reine Funktion ohne DB-Zugriff — leicht mit
einem eingefrorenen STIX-Fixture testbar, ohne echten Netzwerkzugriff
(Abschnitt 10e.5), analog dazu, wie Schritt 5 PydanticAIs TestModel nutzt,
um ohne echte LLM-Anbindung zu testen.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from app.models import (
    Capability,
    Control,
    ImportBatchStatus,
    MappingSource,
    Tactic,
    Technique,
    TechniqueCapabilityMapping,
    TechniqueCapabilityMappingCapability,
    TechniqueCapabilityMappingControl,
    TechniqueImportBatch,
)
from app.models.control import ControlCategory
from app.models.mapping import EffortLevel, ImpactLevel
from app.models.tactic_default import TacticDefaultMapping
from scripts.seed_data import MITIGATION_CROSSWALK, TACTIC_PHASE_ALIASES

logger = logging.getLogger(__name__)

GITHUB_RAW_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/{ref}/"
    "enterprise-attack/enterprise-attack.json"
)
DEFAULT_REF = "master"

M_ID_PATTERN = re.compile(r"^M\d+$")
T_ID_PATTERN = re.compile(r"^T\d+(\.\d+)?$")


@dataclass
class ParsedTechnique:
    stix_id: str
    technique_id: str
    name: str
    phase_names: list[str]
    is_subtechnique: bool
    revoked: bool
    deprecated: bool
    parent_stix_id: str | None = None


@dataclass
class ParsedMitigation:
    stix_id: str
    m_id: str
    name: str


@dataclass
class ParsedBundle:
    bundle_version: str | None
    techniques: dict[str, ParsedTechnique] = field(default_factory=dict)  # keyed by stix_id
    mitigations: dict[str, ParsedMitigation] = field(default_factory=dict)  # keyed by stix_id
    # attack-pattern stix_id -> Liste von course-of-action stix_ids
    mitigates: dict[str, list[str]] = field(default_factory=dict)


def fetch_bundle_bytes(ref: str = DEFAULT_REF, timeout: float = 90.0) -> bytes:
    """Lädt das offizielle Enterprise-ATT&CK-STIX-Bundle direkt von GitHub
    (Abschnitt 10e Punkt 1 — primärer Weg, ~54 MB, in einer Testsession
    verifiziert erreichbar; TAXII bleibt vorerst unimplementiert, s. Punkt 1).
    Kein Streaming: ein admin-getriggerter, seltener Hintergrund-Job, kein
    Hot-Path (Abschnitt 10e Punkt 2)."""
    url = GITHUB_RAW_URL_TEMPLATE.format(ref=ref)
    with httpx.Client(timeout=timeout) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.content


def _external_id(obj: dict, prefix: str) -> str | None:
    for ref in obj.get("external_references", []):
        if ref.get("source_name") == "mitre-attack":
            ext_id = ref.get("external_id", "")
            if ext_id.startswith(prefix):
                return ext_id
    return None


def parse_bundle(raw: bytes) -> ParsedBundle:
    """Reine STIX-Parsing-Funktion ohne DB-Zugriff (siehe Modul-Docstring)."""
    data = json.loads(raw)
    objects = data.get("objects", [])

    bundle_version: str | None = None
    for obj in objects:
        if obj.get("type") == "x-mitre-collection":
            bundle_version = obj.get("x_mitre_version")
            break

    techniques: dict[str, ParsedTechnique] = {}
    for obj in objects:
        if obj.get("type") != "attack-pattern":
            continue
        technique_id = _external_id(obj, prefix="T")
        if technique_id is None or not T_ID_PATTERN.match(technique_id):
            continue
        phase_names = [
            phase["phase_name"]
            for phase in obj.get("kill_chain_phases", [])
            if phase.get("kill_chain_name") == "mitre-attack"
        ]
        techniques[obj["id"]] = ParsedTechnique(
            stix_id=obj["id"],
            technique_id=technique_id,
            name=obj["name"],
            phase_names=phase_names,
            is_subtechnique=bool(obj.get("x_mitre_is_subtechnique", False)),
            revoked=bool(obj.get("revoked", False)),
            deprecated=bool(obj.get("x_mitre_deprecated", False)),
        )

    mitigations: dict[str, ParsedMitigation] = {}
    for obj in objects:
        if obj.get("type") != "course-of-action":
            continue
        # Nur aktuelle, gültige Mitigations (Abschnitt 10e Punkt 3) — viele
        # course-of-action-Objekte im Bundle sind revoked/deprecated
        # Altobjekte ohne echte M-Nummer.
        if obj.get("revoked") or obj.get("x_mitre_deprecated"):
            continue
        m_id = _external_id(obj, prefix="M")
        if m_id is None or not M_ID_PATTERN.match(m_id):
            continue
        mitigations[obj["id"]] = ParsedMitigation(stix_id=obj["id"], m_id=m_id, name=obj["name"])

    mitigates: dict[str, list[str]] = {}
    for obj in objects:
        if obj.get("type") != "relationship":
            continue
        if obj.get("relationship_type") == "subtechnique-of":
            child = techniques.get(obj.get("source_ref"))
            if child is not None and obj.get("target_ref") in techniques:
                child.parent_stix_id = obj["target_ref"]
        elif obj.get("relationship_type") == "mitigates":
            source_ref, target_ref = obj.get("source_ref"), obj.get("target_ref")
            if source_ref in mitigations and target_ref in techniques:
                mitigates.setdefault(target_ref, []).append(source_ref)

    return ParsedBundle(
        bundle_version=bundle_version, techniques=techniques, mitigations=mitigations, mitigates=mitigates
    )


def _resolve_tactic_id(phase_names: list[str], tactic_order: dict[str, int]) -> str | None:
    """Mehrere ATT&CK-Techniken gehören offiziell zu mehreren Taktiken
    gleichzeitig (n:m) — das bestehende Schema (seit Schritt 1) reduziert
    bewusst auf eine Primär-Taktik pro Technik: die früheste in der
    Kill-Chain-Reihenfolge (identische Vereinfachung wie scripts/seed.py's
    seed_techniques(), hier fortgeführt statt eines größeren n:m-Umbaus, der
    nicht Teil des in Abschnitt 10e konkretisierten Plans ist).

    Ein STIX-`phase_name` entspricht meist direkt unserer `tactic.id`
    (Fallback `TACTIC_PHASE_ALIASES.get(p, p)`), außer MITRE hat die Taktik
    umbenannt/aufgespalten — dafür löst TACTIC_PHASE_ALIASES (Abschnitt 10f)
    zuerst auf unsere stabile interne tactic.id auf."""
    candidate_tactic_ids = [
        tactic_id
        for p in phase_names
        if (tactic_id := TACTIC_PHASE_ALIASES.get(p, p)) in tactic_order
    ]
    if not candidate_tactic_ids:
        return None
    return min(candidate_tactic_ids, key=lambda t: tactic_order[t])


def compute_diff(db: Session, bundle: ParsedBundle) -> dict:
    """Berechnet den Diff gegen den aktuellen DB-Stand — committet nichts
    (Abschnitt 6a.2 Punkt 2: kein automatisches Übernehmen ohne Review)."""
    tactic_order = {tid: order for (tid, order) in db.query(Tactic.id, Tactic.mitre_order).all()}

    existing_by_stix_id: dict[str, Technique] = {
        t.stix_id: t for t in db.query(Technique).filter(Technique.stix_id.isnot(None)).all()
    }
    existing_by_technique_id: dict[str, Technique] = {t.id: t for t in db.query(Technique).all()}
    stix_to_technique_id = {stix_id: pt.technique_id for stix_id, pt in bundle.techniques.items()}

    def _find_existing(stix_id: str, technique_id: str) -> Technique | None:
        return existing_by_stix_id.get(stix_id) or existing_by_technique_id.get(technique_id)

    new_techniques: list[dict] = []
    updated_techniques: list[dict] = []
    newly_deprecated: list[dict] = []
    unmapped_tactic_phase: list[dict] = []
    resolved_tactic_id_by_technique_id: dict[str, str] = {
        t.id: t.tactic_id for t in existing_by_technique_id.values()
    }

    for stix_id, pt in bundle.techniques.items():
        existing = _find_existing(stix_id, pt.technique_id)

        if pt.revoked or pt.deprecated:
            if existing is not None and not existing.deprecated:
                newly_deprecated.append({"technique_id": existing.id, "name": existing.name})
            continue

        tactic_id = _resolve_tactic_id(pt.phase_names, tactic_order)
        if tactic_id is None:
            unmapped_tactic_phase.append(
                {"technique_id": pt.technique_id, "name": pt.name, "phase_names": pt.phase_names}
            )
            continue

        parent_technique_id = (
            stix_to_technique_id.get(pt.parent_stix_id) if pt.parent_stix_id is not None else None
        )

        if existing is None:
            new_techniques.append(
                {
                    "technique_id": pt.technique_id,
                    "name": pt.name,
                    "tactic_id": tactic_id,
                    "parent_technique_id": parent_technique_id,
                    "stix_id": stix_id,
                }
            )
            resolved_tactic_id_by_technique_id[pt.technique_id] = tactic_id
            continue

        resolved_tactic_id_by_technique_id[existing.id] = tactic_id
        changes: dict[str, dict[str, str | None]] = {}
        if existing.name != pt.name:
            changes["name"] = {"old": existing.name, "new": pt.name}
        if existing.tactic_id != tactic_id:
            changes["tactic_id"] = {"old": existing.tactic_id, "new": tactic_id}
        if existing.parent_technique_id != parent_technique_id:
            changes["parent_technique_id"] = {"old": existing.parent_technique_id, "new": parent_technique_id}
        if existing.stix_id != stix_id:
            changes["stix_id"] = {"old": existing.stix_id, "new": stix_id}
        if changes:
            updated_techniques.append({"technique_id": existing.id, "changes": changes})

    mitigation_candidates: list[dict] = []
    conflicts: list[dict] = []
    skipped_mitigations: list[dict] = []
    skipped_seen: set[str] = set()

    existing_mapping_by_technique_id: dict[str, TechniqueCapabilityMapping] = {
        m.technique_id: m for m in db.query(TechniqueCapabilityMapping).all()
    }
    tactic_default_by_tactic_id: dict[str, TacticDefaultMapping] = {
        d.tactic_id: d for d in db.query(TacticDefaultMapping).all()
    }

    for attack_pattern_stix_id, mitigation_stix_ids in bundle.mitigates.items():
        pt = bundle.techniques.get(attack_pattern_stix_id)
        if pt is None or pt.revoked or pt.deprecated:
            continue
        technique_id = pt.technique_id
        if technique_id not in resolved_tactic_id_by_technique_id:
            continue  # unmappbare Taktik oder anderweitig übersprungen

        entries: list[dict] = []
        capabilities: dict[str, None] = {}
        control_labels: dict[str, None] = {}
        for mitigation_stix_id in mitigation_stix_ids:
            mitigation = bundle.mitigations.get(mitigation_stix_id)
            if mitigation is None:
                continue
            crosswalk_entry = MITIGATION_CROSSWALK.get(mitigation.m_id)
            if crosswalk_entry is None:
                if mitigation.m_id not in skipped_seen:
                    skipped_seen.add(mitigation.m_id)
                    skipped_mitigations.append({"m_id": mitigation.m_id, "mitigation_name": mitigation.name})
                continue
            entries.append(
                {
                    "m_id": mitigation.m_id,
                    "mitigation_name": mitigation.name,
                    "control_label": crosswalk_entry["control_label"],
                }
            )
            for cap in crosswalk_entry["capabilities"]:
                capabilities[cap] = None
            control_labels[crosswalk_entry["control_label"]] = None

        if not entries:
            continue

        existing_mapping = existing_mapping_by_technique_id.get(technique_id)
        if existing_mapping is not None and existing_mapping.mapping_source == MappingSource.SPECIFIC:
            conflicts.append(
                {
                    "technique_id": technique_id,
                    "mitigations": entries,
                    "reason": "bestehendes spezifisches Mapping wird nicht überschrieben",
                }
            )
            continue

        tactic_id = resolved_tactic_id_by_technique_id[technique_id]
        default = tactic_default_by_tactic_id.get(tactic_id)
        if default is None:
            # Datenintegritätsfehler wie in resolve_technique() (Abschnitt
            # 10a.3) — harter Fehler statt stiller Näherung.
            raise RuntimeError(
                f"Kein tactic_default_mapping für Taktik '{tactic_id}' "
                f"(Technik '{technique_id}') — Seed-Daten unvollständig."
            )

        mitigation_candidates.append(
            {
                "technique_id": technique_id,
                "mitigations": entries,
                "capabilities": list(capabilities),
                "control_labels": list(control_labels),
                "impact": default.impact.value,
                "effort": default.effort.value,
            }
        )

    return {
        "bundle_version": bundle.bundle_version,
        "new_techniques": new_techniques,
        "updated_techniques": updated_techniques,
        "newly_deprecated_techniques": newly_deprecated,
        "unmapped_tactic_phase_techniques": unmapped_tactic_phase,
        "mitigation_candidates": mitigation_candidates,
        "skipped_mitigations_without_crosswalk": skipped_mitigations,
        "conflicts": conflicts,
    }


def run_fetch_and_diff(
    db: Session,
    batch_id: int,
    raw_bytes: bytes | None = None,
    ref: str = DEFAULT_REF,
) -> None:
    """Läuft als BackgroundTasks-Job (analog Sales-Briefing, Schritt 5):
    Fetch (falls kein Upload übergeben wurde) + Parsing + Diff-Berechnung.
    Fehler landen als status='failed' mit error_message, kein unbehandelter
    500er im Hintergrund-Task."""
    batch = db.get(TechniqueImportBatch, batch_id)
    if batch is None:
        logger.error("technique_import_batch %s nicht gefunden, Job abgebrochen", batch_id)
        return

    try:
        if raw_bytes is None:
            raw_bytes = fetch_bundle_bytes(ref=ref)
        bundle = parse_bundle(raw_bytes)
        diff = compute_diff(db, bundle)
        batch.diff_snapshot = diff
        batch.bundle_version = diff["bundle_version"]
        batch.status = ImportBatchStatus.DIFF_READY
    except Exception as exc:
        logger.exception("MITRE-Import fehlgeschlagen (batch_id=%s)", batch_id)
        batch.status = ImportBatchStatus.FAILED
        batch.error_message = str(exc)

    db.commit()


def _snapshot_technique(db: Session, snapshot: dict, technique_id: str) -> None:
    if technique_id in snapshot["techniques"]:
        return
    t = db.get(Technique, technique_id)
    snapshot["techniques"][technique_id] = (
        None
        if t is None
        else {
            "name": t.name,
            "tactic_id": t.tactic_id,
            "parent_technique_id": t.parent_technique_id,
            "deprecated": t.deprecated,
            "stix_id": t.stix_id,
        }
    )


def _snapshot_mapping(db: Session, snapshot: dict, technique_id: str) -> None:
    if technique_id in snapshot["mappings"]:
        return
    m = db.query(TechniqueCapabilityMapping).filter_by(technique_id=technique_id).one_or_none()
    snapshot["mappings"][technique_id] = (
        None
        if m is None
        else {
            "mapping_source": m.mapping_source.name,
            "impact": m.impact.name,
            "effort": m.effort.name,
            "capabilities": [link.capability.name for link in m.capability_links],
            "controls": [
                {"category": link.control.category.value, "label": link.control.label}
                for link in m.control_links
            ],
        }
    )


def apply_batch(db: Session, batch: TechniqueImportBatch, technique_ids: list[str], mitigation_technique_ids: list[str]) -> None:
    """Übernimmt selektiv Teile des berechneten Diffs (Abschnitt 6a.2 Punkt 3
    / 10e.3) und schreibt vorher einen vollständigen Snapshot der
    betroffenen Zeilen für einen einstufigen Rollback (Abschnitt 10e.1)."""
    if batch.status != ImportBatchStatus.DIFF_READY:
        raise ValueError(f"Batch {batch.id} hat status={batch.status.value}, erwartet 'diff_ready'")

    diff = batch.diff_snapshot
    selected_technique_set = set(technique_ids)
    selected_mitigation_set = set(mitigation_technique_ids)
    snapshot: dict = {"techniques": {}, "mappings": {}}

    for item in diff["new_techniques"]:
        if item["technique_id"] not in selected_technique_set:
            continue
        _snapshot_technique(db, snapshot, item["technique_id"])
        db.add(
            Technique(
                id=item["technique_id"],
                name=item["name"],
                tactic_id=item["tactic_id"],
                parent_technique_id=item["parent_technique_id"],
                stix_id=item["stix_id"],
                deprecated=False,
            )
        )
    db.flush()  # neue Techniken müssen existieren, bevor Mappings/Parent-Refs darauf verweisen

    for item in diff["updated_techniques"]:
        if item["technique_id"] not in selected_technique_set:
            continue
        _snapshot_technique(db, snapshot, item["technique_id"])
        technique = db.get(Technique, item["technique_id"])
        for field_name, change in item["changes"].items():
            setattr(technique, field_name, change["new"])

    for item in diff["newly_deprecated_techniques"]:
        if item["technique_id"] not in selected_technique_set:
            continue
        _snapshot_technique(db, snapshot, item["technique_id"])
        db.get(Technique, item["technique_id"]).deprecated = True

    for candidate in diff["mitigation_candidates"]:
        tid = candidate["technique_id"]
        if tid not in selected_mitigation_set:
            continue
        _snapshot_mapping(db, snapshot, tid)

        existing_mapping = db.query(TechniqueCapabilityMapping).filter_by(technique_id=tid).one_or_none()
        if existing_mapping is not None and existing_mapping.mapping_source == MappingSource.SPECIFIC:
            # Defensive Zweitprüfung — der Diff markiert das bereits als
            # conflict (Abschnitt 6a.3 Punkt 6), nie überschreiben.
            continue

        if existing_mapping is None:
            existing_mapping = TechniqueCapabilityMapping(technique_id=tid, mapping_source=MappingSource.MITRE_DERIVED)
            db.add(existing_mapping)
        else:
            existing_mapping.mapping_source = MappingSource.MITRE_DERIVED
            for link in list(existing_mapping.capability_links):
                db.delete(link)
            for link in list(existing_mapping.control_links):
                db.delete(link)
        existing_mapping.impact = ImpactLevel(candidate["impact"])
        existing_mapping.effort = EffortLevel(candidate["effort"])
        db.flush()

        for capability_name in candidate["capabilities"]:
            capability = db.query(Capability).filter_by(name=capability_name).one()
            db.add(
                TechniqueCapabilityMappingCapability(mapping_id=existing_mapping.id, capability_id=capability.id)
            )
        for control_label in candidate["control_labels"]:
            control = (
                db.query(Control).filter_by(category=ControlCategory.PREVENT, label=control_label).one_or_none()
            )
            if control is None:
                control = Control(category=ControlCategory.PREVENT, label=control_label)
                db.add(control)
                db.flush()
            db.add(TechniqueCapabilityMappingControl(mapping_id=existing_mapping.id, control_id=control.id))

    batch.pre_apply_snapshot = snapshot
    batch.status = ImportBatchStatus.APPLIED
    batch.applied_at = datetime.now(UTC)
    db.commit()


def rollback_batch(db: Session, batch: TechniqueImportBatch) -> None:
    """Stellt den durch apply_batch() protokollierten Vorzustand wieder her
    (Abschnitt 6a.2 Punkt 4 / 10e.1). Der Aufrufer (API-Layer, 10e.3) muss
    sicherstellen, dass kein neuerer Batch bereits angewendet wurde."""
    if batch.status != ImportBatchStatus.APPLIED:
        raise ValueError(f"Batch {batch.id} hat status={batch.status.value}, erwartet 'applied'")

    snapshot = batch.pre_apply_snapshot or {"techniques": {}, "mappings": {}}

    # Mappings zuerst zurückrollen (referenzieren technique_id per FK) —
    # sonst würde eine gleich danach gelöschte Technik noch referenziert.
    for tid, mapping_snapshot in snapshot["mappings"].items():
        current = db.query(TechniqueCapabilityMapping).filter_by(technique_id=tid).one_or_none()
        if mapping_snapshot is None:
            if current is not None and current.mapping_source == MappingSource.MITRE_DERIVED:
                db.delete(current)
            continue
        if current is None:
            current = TechniqueCapabilityMapping(technique_id=tid)
            db.add(current)
            db.flush()
        else:
            for link in list(current.capability_links):
                db.delete(link)
            for link in list(current.control_links):
                db.delete(link)
        current.mapping_source = MappingSource[mapping_snapshot["mapping_source"]]
        current.impact = ImpactLevel[mapping_snapshot["impact"]]
        current.effort = EffortLevel[mapping_snapshot["effort"]]
        db.flush()
        for capability_name in mapping_snapshot["capabilities"]:
            capability = db.query(Capability).filter_by(name=capability_name).one()
            db.add(TechniqueCapabilityMappingCapability(mapping_id=current.id, capability_id=capability.id))
        for control_entry in mapping_snapshot["controls"]:
            control = (
                db.query(Control)
                .filter_by(category=ControlCategory(control_entry["category"]), label=control_entry["label"])
                .one()
            )
            db.add(TechniqueCapabilityMappingControl(mapping_id=current.id, control_id=control.id))

    for tid, technique_snapshot in snapshot["techniques"].items():
        technique = db.get(Technique, tid)
        if technique_snapshot is None:
            if technique is not None:
                db.delete(technique)
            continue
        if technique is None:
            technique = Technique(id=tid)
            db.add(technique)
        technique.name = technique_snapshot["name"]
        technique.tactic_id = technique_snapshot["tactic_id"]
        technique.parent_technique_id = technique_snapshot["parent_technique_id"]
        technique.deprecated = technique_snapshot["deprecated"]
        technique.stix_id = technique_snapshot["stix_id"]

    batch.status = ImportBatchStatus.ROLLED_BACK
    batch.rolled_back_at = datetime.now(UTC)
    db.commit()
