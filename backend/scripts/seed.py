"""Seed-Skript für Schritt 1: befüllt tactic, technique, capability, control sowie
die spezifischen (KB) und Taktik-Standard-Mappings mit dem statischen Datensatz aus
dem HTML-Prototyp (siehe scripts/seed_data.py).

Nutzung:
    python -m scripts.seed
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session

from app.core.db import SessionLocal, engine
from app.models import (
    Capability,
    Control,
    Tactic,
    TacticDefaultMapping,
    TacticDefaultMappingCapability,
    TacticDefaultMappingControl,
    Technique,
    TechniqueCapabilityMapping,
    TechniqueCapabilityMappingCapability,
    TechniqueCapabilityMappingControl,
)
from app.models.control import ControlCategory
from app.models.mapping import EffortLevel, ImpactLevel, MappingSource
from scripts.seed_data import ALL_CAPABILITIES, KB, TACTIC_DEFAULTS, TACTIC_GROUPS


def slugify(name: str) -> str:
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def seed_tactics(db: Session) -> dict[str, Tactic]:
    tactics: dict[str, Tactic] = {}
    for order, name in enumerate(TACTIC_GROUPS.keys(), start=1):
        tactic = db.get(Tactic, slugify(name))
        if tactic is None:
            tactic = Tactic(id=slugify(name), name=name, mitre_order=order)
            db.add(tactic)
        tactics[name] = tactic
    db.flush()
    return tactics


def seed_techniques(db: Session, tactics: dict[str, Tactic]) -> dict[str, Technique]:
    """Ein Technik-Code kann im Prototyp-Katalog unter mehreren Taktiken auftauchen
    (z.B. T1078 unter Initial Access, Persistence, Privilege Escalation, Defense
    Evasion — MITRE modelliert Technik<->Taktik als n:m). Für Schritt 1 wird bewusst
    vereinfacht auf EINE Primär-Taktik pro Technik reduziert: die früheste in der
    Kill-Chain-Reihenfolge, in der die Technik auftritt — das entspricht exakt dem
    Laufzeitverhalten des Prototyps (Array.find() über die in Kill-Chain-Reihenfolge
    deklarierten TACTIC_GROUPS-Keys). Eine echte n:m-Modellierung ist für den
    STIX-Import in Schritt 6 vorzusehen, wo kill_chain_phases pro Technik verfügbar
    sind."""
    techniques: dict[str, Technique] = {}
    for tactic_name, entries in TACTIC_GROUPS.items():
        for code, name in entries:
            if code in techniques:
                continue  # frühere (in Kill-Chain-Reihenfolge frühere) Taktik gewinnt
            technique = db.get(Technique, code)
            if technique is None:
                technique = Technique(id=code, name=name, tactic_id=tactics[tactic_name].id)
                db.add(technique)
            techniques[code] = technique
    db.flush()

    # parent_technique_id aus der MITRE-ID-Konvention ableiten (Tbase.NNN -> Tbase),
    # nur sofern die Basistechnik selbst im Katalog existiert.
    for code, technique in techniques.items():
        base = code.split(".")[0]
        if base != code and base in techniques:
            technique.parent_technique_id = base
    db.flush()
    return techniques


def seed_capabilities(db: Session) -> dict[str, Capability]:
    capabilities: dict[str, Capability] = {}
    for name in ALL_CAPABILITIES:
        capability = db.query(Capability).filter_by(name=name).one_or_none()
        if capability is None:
            capability = Capability(name=name)
            db.add(capability)
        capabilities[name] = capability
    db.flush()
    return capabilities


def get_or_create_control(
    db: Session, cache: dict[tuple[ControlCategory, str], Control], category: ControlCategory, label: str
) -> Control:
    key = (category, label)
    control = cache.get(key)
    if control is None:
        control = db.query(Control).filter_by(category=category, label=label).one_or_none()
        if control is None:
            control = Control(category=category, label=label)
            db.add(control)
            db.flush()
        cache[key] = control
    return control


def seed_specific_mappings(
    db: Session, capabilities: dict[str, Capability], control_cache: dict
) -> None:
    for code, data in KB.items():
        existing = db.query(TechniqueCapabilityMapping).filter_by(technique_id=code).one_or_none()
        if existing is not None:
            continue
        mapping = TechniqueCapabilityMapping(
            technique_id=code,
            mapping_source=MappingSource.SPECIFIC,
            impact=ImpactLevel(data["impact"]),
            effort=EffortLevel(data["effort"]),
        )
        db.add(mapping)
        db.flush()

        for cap_name in data["capabilities"]:
            db.add(
                TechniqueCapabilityMappingCapability(
                    mapping_id=mapping.id, capability_id=capabilities[cap_name].id
                )
            )
        for category, labels in (
            (ControlCategory.PREVENT, data["prevent"]),
            (ControlCategory.DETECT, data["detect"]),
            (ControlCategory.RESPOND, data["respond"]),
        ):
            for label in labels:
                control = get_or_create_control(db, control_cache, category, label)
                db.add(
                    TechniqueCapabilityMappingControl(mapping_id=mapping.id, control_id=control.id)
                )
    db.flush()


def seed_tactic_defaults(
    db: Session, tactics: dict[str, Tactic], capabilities: dict[str, Capability], control_cache: dict
) -> None:
    for tactic_name, data in TACTIC_DEFAULTS.items():
        tactic_id = tactics[tactic_name].id
        existing = db.get(TacticDefaultMapping, tactic_id)
        if existing is not None:
            continue
        default_mapping = TacticDefaultMapping(
            tactic_id=tactic_id,
            impact=ImpactLevel(data["impact"]),
            effort=EffortLevel(data["effort"]),
        )
        db.add(default_mapping)
        db.flush()

        for cap_name in data["capabilities"]:
            db.add(
                TacticDefaultMappingCapability(
                    tactic_id=tactic_id, capability_id=capabilities[cap_name].id
                )
            )
        for category, labels in (
            (ControlCategory.PREVENT, data["prevent"]),
            (ControlCategory.DETECT, data["detect"]),
            (ControlCategory.RESPOND, data["respond"]),
        ):
            for label in labels:
                control = get_or_create_control(db, control_cache, category, label)
                db.add(TacticDefaultMappingControl(tactic_id=tactic_id, control_id=control.id))
    db.flush()


def run() -> None:
    db = SessionLocal()
    control_cache: dict[tuple[ControlCategory, str], Control] = {}
    try:
        tactics = seed_tactics(db)
        techniques = seed_techniques(db, tactics)
        capabilities = seed_capabilities(db)
        seed_specific_mappings(db, capabilities, control_cache)
        seed_tactic_defaults(db, tactics, capabilities, control_cache)
        db.commit()
        print(
            f"Seed abgeschlossen: {len(tactics)} Taktiken, {len(techniques)} Techniken, "
            f"{len(capabilities)} Capabilities, {len(KB)} spezifische Mappings, "
            f"{len(TACTIC_DEFAULTS)} Taktik-Standardmappings."
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
    engine.dispose()
