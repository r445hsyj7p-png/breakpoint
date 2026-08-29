# Projektauftrag für Claude Code: Breakpoint — ATT&CK-to-Action Plattform

> **v2 — überarbeitet nach Review-Session vom 29.08.2026.** Änderungen gegenüber der ursprünglichen Fassung sind in den betroffenen Abschnitten markiert (▶ **Update v2**). Grundlage der Überarbeitung: kritische Prüfung des Auftrags + Code-Review des interaktiven HTML-Prototyps (`breakpoint-dashboard.html`) + eine vom Auftraggeber formulierte Zielbild-Zusammenfassung (siehe neuer Abschnitt 2a).

Dieses Dokument ist der vollständige Übergabe-Auftrag, um das bisher als HTML-Mockup validierte Konzept **Breakpoint** ("From Attack Technique to Action") als produktive, im eigenen Datacenter betriebene Anwendung mit Claude Code umzusetzen. Es enthält Kontext, Architekturentscheidungen, Datenmodell, Modulübersicht und einen konkret ausführbaren **Schritt 1**.

---

## 1. Produktkontext (kurz)

Breakpoint übersetzt Red-Team-/Pentest-Findings (MITRE-ATT&CK-T-Nummern) automatisiert in:

1. **Capabilities** (herstellerneutral, z. B. "MFA", "Network Segmentation")
2. **Prevent/Detect/Respond-Controls** je Technik
3. **Portfolio-Fit** (Zuordnung zu den eigenen Technologien/Leistungen)
4. **Priorisierte, geschäftlich verständliche Maßnahmen** (Impact/Aufwand)

Der interaktive HTML-Prototyp liegt jetzt vollständig vor (`breakpoint-dashboard.html`) und dient als **funktionale Referenz** (Interaktionslogik, Datenstrukturen, Mapping-Regeln, Visualisierungen). Claude Code soll dieses Konzept nicht neu erfinden, sondern aus dem Prototyp in eine produktionsreife Architektur überführen — **mit den in Abschnitt 5 dokumentierten, bewussten Korrekturen** gegenüber dem 1:1-Prototyp-Verhalten.

---

## 2. Rahmenbedingungen (nicht verhandelbar)

| Anforderung | Konsequenz für die Architektur |
|---|---|
| **Nur On-Prem / eigenes Datacenter** | Keine Cloud-Dienste (kein AWS/Azure/GCP-SaaS, keine externen APIs zur Laufzeit). Alles muss in eigenen Containern/VMs laufen. |
| **Interne LLM-Plattform bereits vorhanden** | Kein eigenes Modell-Hosting aufbauen — die Anwendung integriert sich als Client gegen die bestehende Plattform (vermutlich OpenAI-kompatible oder proprietäre API; siehe offene Fragen in Abschnitt 12). |
| **PydanticAI bereits im Haus verfügbar** | Wird als Abstraktionsschicht für alle LLM-Aufrufe genutzt — nicht als rohe Prompt-Strings, sondern mit typisierten Input-/Output-Schemas. |
| **Hochsensible Daten** | Red-Team-Findings zeigen konkrete Kundenschwachstellen. Kein Datenabfluss nach außen, auch nicht indirekt (z. B. Telemetrie, Fehler-Tracking-SaaS, Font-CDNs im Frontend). |
| **Zwei sehr unterschiedliche Nutzergruppen** | Technische Analysten (Detailtiefe, T-Nummern, Capabilities) und Sales (Geschäftssprache, keine ATT&CK-Kenntnis vorausgesetzt) — UI und ggf. Rollenrechte müssen das abbilden, **aus derselben berechneten Wahrheit heraus** (siehe 2a). |
| **Portfolio ändert sich regelmäßig selbst** | Technologien/Leistungen und deren Capability-Zuordnungen dürfen nicht hart codiert sein — es braucht einen **Admin-Bereich**, über den das Team das Portfolio ohne Code-Änderung/Deployment pflegt (siehe Abschnitt 6a). |
| **MITRE ATT&CK entwickelt sich weiter** | Da kein Live-Internetzugriff zur Laufzeit erlaubt ist, braucht es einen **admin-gesteuerten Import-Workflow**, um neue/geänderte Techniken periodisch manuell nachzuladen (siehe Abschnitt 6a). |
| ▶ **Portfolio-Fit darf Priorisierung nie beeinflussen** *(neu, v2)* | `priority_rank` wird ausschließlich aus Impact/Effort/Kettenwirkung der Sicherheitslücke berechnet. Ob eine Maßnahme durch eigenes Portfolio abgedeckt ist, ist reine Zusatzinformation und fließt **nie** in die Sortierung ein — sonst wird aus einer neutralen Sicherheitsempfehlung verdeckter Produktverkauf. |
| ▶ **Lücken sind nie ausblendbar** *(neu, v2)* | Ungedeckte Capabilities/Portfolio-Gaps müssen in Analyst- und Sales-Ansicht immer sichtbar sein. Kein Toggle, keine selektive Auslassung im Sales-Briefing. |

---

## 2a. Zielbild & Produktprinzipien *(neu, v2)*

Diese Prinzipien wurden vom Auftraggeber als Erfolgsmaßstab formuliert und sind ab jetzt Teil der nicht verhandelbaren Anforderungen (Abschnitt 2), nicht nur Absichtserklärung.

**Das Problem:** Ein Red-Team-Report allein ist nicht handlungsleitend — eine Liste von T-Nummern sagt weder, was fachlich zu tun ist, noch was das priorisiert bedeutet, noch was das für das eigene Angebot heißt.

**Das Zielbild — Übersetzungskette:**
```
Technik  →  Fähigkeit (Capability)  →  Maßnahme (Control)  →  Priorität  →  eigene Lösung (Portfolio-Fit)
```
Jede Stufe ist eine eigenständige, abfragbare Entität (siehe Datenmodell, Abschnitt 5) — insbesondere **Maßnahme** ist keine Freitext-Eigenschaft einer Technik, sondern ein eigenes Objekt, das über mehrere Techniken hinweg wiederverwendet und dedupliziert werden muss (Details unten, "Maßnahmen-Deduplizierung").

**Für wen — Doppelnutzung aus derselben Wahrheit:** Analysten (technische Tiefe, T-Nummern, Capabilities) und Sales (Geschäftssprache, kein ATT&CK-Vorwissen nötig) arbeiten mit **demselben deterministisch berechneten Analyzer-Ergebnis** — nur die Präsentation unterscheidet sich. Das LLM (Sales-Briefing) erschafft keine neuen Fakten, sondern formuliert vorhandene, geprüfte Daten um (siehe Abschnitt 7).

▶ **Architekturkonsequenz:** Es gibt genau **ein kanonisches Analyzer-Output-Schema**, das sowohl die Analysten-UI direkt rendert als auch unverändert als Input für den PydanticAI-Sales-Agent dient. Zwei parallele Berechnungspfade (z. B. eine vereinfachte Zusammenfassung nur für Sales) sind ausdrücklich nicht erlaubt — sonst ist "dieselbe Wahrheit" nur behauptet, nicht technisch garantiert.

**Was Erfolg bedeutet (überprüfbar):**
- **Keine Sackgassen:** Jede eingegebene, im Katalog bekannte Technik führt zu einer Empfehlung — spezifisches Mapping oder Taktik-Standard-Fallback, nie "kein Ergebnis". Nur echte Katalog-Unbekannte (Tippfehler o. Ä.) sind eine sichtbare, benannte Ausnahme.
- **Echte Priorisierung:** Eine Impact/Effort-Einstufung pro Einzeltechnik reicht laut Zielbild nicht aus. ▶ Der Analyzer-Algorithmus (Schritt 2) muss zusätzlich berücksichtigen, **wie viele Techniken/Angriffsketten eine Maßnahme adressiert** — eine Maßnahme, die drei von sieben beobachteten Ketten unterbricht, muss höher priorisiert werden können als eine, die nur eine unwichtige Einzeltechnik betrifft. Das ist eine bewusste Erweiterung gegenüber dem Prototyp-Verhalten (dort: reine Sortierung nach Impact/Effort der Einzeltechnik), keine 1:1-Portierung.
- **Sichtbare statt verschwiegene Lücken:** siehe Rahmenbedingungen oben.

**Was die App bewusst nicht ist (dauerhafte Abgrenzung, kein Scope-Punkt für "später"):**
- **Kein ATT&CK-Navigator-Klon.** Die "Alle Techniken"-Ansicht bleibt eine filterbare Referenztabelle, keine vollständige Matrix-Heatmap über alle 14 Taktiken. Sollte künftig eine Navigator-artige Matrixansicht gewünscht werden, ist das ein bewusster Kurswechsel, der gegen dieses Prinzip explizit abgewogen werden muss.
- **Kein reiner Produktverkauf.** Empfehlungen sind primär herstellerneutral (Capability-Ebene); Portfolio-Fit ist optionale, ehrliche Zusatzinformation, nie Ranking-Faktor (siehe Rahmenbedingungen).
- **Kein statisches Nachschlagewerk.** Startpunkt der Nutzung ist immer ein aktives Engagement (Dashboard), nicht die Knowledge-Base. Die Knowledge-Base ist Referenz, nicht Einstiegspunkt.

---

## 3. Architekturüberblick

```
                     ┌─────────────────────────┐
                     │   Frontend (React/TS)   │
                     │  Analyst-View / Sales-View│
                     └───────────┬─────────────┘
                                 │ REST/JSON (intern, HTTPS)
                     ┌───────────▼─────────────┐
                     │   Backend API (FastAPI)  │
                     │  Auth · Routing · Validation│
                     └───────────┬─────────────┘
                                 │
              ┌──────────────────┼───────────────────┐
              │                  │                    │
   ┌──────────▼─────────┐ ┌──────▼───────┐  ┌─────────▼──────────┐
   │  Analysis Engine     │ │  PydanticAI   │  │  Reporting/Export   │
   │  (Mapping-Logik:     │ │  Agent-Layer  │  │  (PDF/DOCX/Markdown)│
   │  Technik→Capability→ │ │  → interne    │  └─────────────────────┘
   │  Control→Portfolio)  │ │  LLM-Plattform│
   │  → EIN kanonisches   │ └───────────────┘
   │  Output-Schema für   │
   │  Analyst UND Sales   │
   └──────────┬───────────┘
              │
   ┌──────────▼───────────┐
   │   PostgreSQL           │
   │  Techniques, Mappings, │
   │  Portfolio, Engagements│
   └────────────────────────┘
```

Kein Graph-DB-Overhead in Version 1 (wie im ursprünglichen Konzept festgehalten: PostgreSQL reicht, solange die Beziehungen nicht explosionsartig komplex werden). Alles läuft in Docker-Containern, orchestriert über Docker Compose (Startpunkt) bzw. später ggf. das interne Kubernetes/Nomad-Setup des Datacenters.

---

## 4. Tech-Stack-Entscheidungen

| Layer | Technologie | Begründung |
|---|---|---|
| Frontend | React + TypeScript + Vite | Deckungsgleich mit dem interaktiven Prototyp-Verhalten, gute Tooling-Reife, kein Cloud-Zwang |
| Styling | Tailwind CSS | Schnelle, konsistente Umsetzung des im Prototyp definierten Dark-Theme (Graphit/Amber/Ember/Detect/Prevent/Respond-Farbsystem) |
| Backend | Python 3.12 + FastAPI | Deckt sich mit ursprünglicher Konzeptvorgabe, hervorragende Pydantic-Integration (Synergie mit PydanticAI) |
| Datenbank | PostgreSQL 16 | Ausreichend für Version 1, keine Graph-DB nötig |
| Migrations | Alembic | Standard für FastAPI/SQLAlchemy-Stacks |
| ORM | SQLAlchemy 2.x | — |
| LLM-Anbindung | PydanticAI (Agent-Definitionen) gegen interne LLM-Plattform | Typisierte, validierte Ein-/Ausgaben statt Freitext-Parsing |
| Auth | Anbindung an internes IdP (OIDC/SAML) — Platzhalter bis Klärung | Keine eigene Nutzerverwaltung von Grund auf |
| Containerisierung | Docker + Docker Compose (lokal) | Portierbar in bestehende Datacenter-Orchestrierung |
| Tests | pytest (Backend), Vitest (Frontend) | — |

---

## 5. Datenmodell (Kernentitäten) ▶ **überarbeitet in v2**

Abgeleitet aus dem Prototyp-Code (`KB`, `PORTFOLIO`, `TACTIC_DEFAULTS`, `TECHNIQUE_CATALOG`, `getMapping()`) — **mit Korrekturen gegenüber dem literalen Prototyp-Verhalten**, siehe Anmerkungen unten.

```
tactic
  id (PK), name, mitre_order (1–14)

technique
  id (PK, z.B. "T1078.004"), name, tactic_id (FK),
  parent_technique_id (nullable, self-FK, für Sub-Techniques)

capability
  id (PK), name (unique)

control
  id (PK), category ENUM('prevent','detect','respond'), label

technique_capability_mapping
  id (PK), technique_id (FK),
  mapping_source ENUM('specific','tactic_default'),
  impact ENUM('niedrig','mittel','hoch','sehr_hoch'),
  effort ENUM('niedrig','mittel','hoch')

technique_capability_mapping_capability   -- Join: Mapping ↔ Capability
  mapping_id (FK), capability_id (FK)

technique_capability_mapping_control      -- Join: Mapping ↔ Control
  mapping_id (FK), control_id (FK)

tactic_default_mapping                    -- eigenständig statt nullable technique_id
  tactic_id (PK, FK), impact, effort
tactic_default_mapping_capability / _control  -- gleiche Join-Struktur wie oben

portfolio_technology
  id (PK), name, type, active (bool, kein Hard-Delete)

portfolio_technology_capability           -- Join statt capabilities[]
  portfolio_technology_id (FK), capability_id (FK)

engagement
  id (PK), name, external_ref, created_at, status

finding
  id (PK), engagement_id (FK), technique_id (FK), raw_source_ref (Report-Fundstelle, optional)

recommendation  (materialisiertes Ergebnis pro Engagement, oder zur Laufzeit berechnet — Entscheidung vor Schritt 2)
  engagement_id (FK), control_id (FK), priority_rank,
  chain_coverage_count (Anzahl betroffener Techniken/Ketten — für "echte Priorisierung", s. 2a),
  portfolio_fit[] (rein informativ, kein Ranking-Faktor)

sales_briefing  (LLM-generiert, versioniert)
  id (PK), engagement_id (FK), generated_at, model_version, content (strukturiert, siehe PydanticAI-Schema Abschnitt 7), reviewed_by (nullable — technische Freigabe vor Kundenkontakt)

technique_import_batch  (Protokoll jedes admin-gesteuerten MITRE-Imports, siehe Abschnitt 6a.2)
  id (PK), imported_by, imported_at, source_file_hash, techniques_added, techniques_changed, techniques_deprecated, status ENUM('applied','rolled_back')

portfolio_technology_history  (Änderungsprotokoll der Self-Service-Portfolio-Pflege, siehe Abschnitt 6a.1)
  id (PK), portfolio_technology_id (FK), changed_by, changed_at, field_changed, old_value, new_value

audit_log  ▶ neu, v2 — bisher nur in Abschnitt 8 gefordert, jetzt auch im Datenmodell
  id (PK), actor, action, entity_type, entity_id, occurred_at
```

**Wichtig aus dem Prototyp übernehmen, mit Korrekturen:**

- **Zweistufiges Mapping** (`specific` vs. `tactic_default`) bleibt als explizites Feld erhalten — Kern der Transparenz gegenüber dem Nutzer ("woher kommt diese Empfehlung?").
- ▶ **Sub-Technique-Fallback — korrigiert:** Der Prototyp-Code (`getMapping()`) sucht bei fehlendem exaktem Treffer den *ersten* KB-Eintrag mit gleichem ID-Präfix vor dem Punkt (`k.split('.')[0] === base`) — das kann fälschlich das Mapping einer **anderen** Sub-Technique statt der Basistechnik liefern, sobald der Katalog wächst (aktuell im Demo-Datensatz nicht sichtbar, weil zu jeder Sub-Technique zufällig auch die Basistechnik existiert). **Für die produktive Umsetzung gilt stattdessen die im Auftrag ursprünglich beschriebene, korrekte Logik:** exakter Technik-Treffer → sonst `parent_technique_id`-Traversal zur Basistechnik → sonst `tactic_default_mapping` der zugehörigen Taktik → sonst "kein Mapping" (nur bei Katalog-unbekannten Codes).
- ▶ **Maßnahmen-Deduplizierung (neu, verpflichtend seit Abschnitt 2a):** `control` ist eine eigenständige, wiederverwendbare Entität, kein Freitext-Array je Mapping-Zeile. Das ist Voraussetzung dafür, dass eine Maßnahme, die bei mehreren Techniken auftaucht (z. B. "MFA erzwingen" bei Initial Access **und** Credential-Access-Taktik-Default), im Analyzer-Ergebnis als **eine** Zeile mit Kettenabdeckung erscheint statt als mehrere Duplikate.
- ▶ **`parent_technique_id`-Befüllung:** Für den statischen Prototyp-Datensatz (Schritt 1/2) wird die Sub-Technique-Beziehung aus der MITRE-ID-Konvention abgeleitet (`Tbase.NNN` → Basis `Tbase`, sofern als eigene Technik vorhanden). Für den späteren STIX-Import (Schritt 6) ist stattdessen die **echte MITRE-Relationship** (`x_mitre_is_subtechnique`) zu verwenden, nicht weiteres String-Parsing — sonst importiert das Tool stillschweigend falsche Beziehungen, falls MITRE von der Namenskonvention abweicht.

---

## 6. Kernmodule (aus dem Prototyp abzuleiten)

1. **Engagement-Import** — T-Nummern (Freitext/CSV), später Report-Upload mit Extraktion (nicht Teil von Version 1, siehe Abschnitt 9)
2. **ATT&CK Analyzer** — Kernmapping-Engine (Technik → Capability → Control → Portfolio), inkl. Prioritätensortierung nach Impact/Aufwand **und Kettenabdeckung** (s. 2a), Ausgabe über das eine kanonische Analyzer-Output-Schema
3. **Techniken-Katalog** — vollständige Referenzliste; ▶ **in Version 1 bereits mit dem vollständigen, im Prototyp enthaltenen ~200-Techniken-Katalog seeden** (alle 14 Taktiken, `TACTIC_GROUPS`), nicht nur mit den ~10 detailliert ausgearbeiteten Techniken — sonst funktioniert die "Alle Techniken"-Ansicht in Schritt 1 nur unvollständig. Die ~10 KB-Einträge bleiben die einzigen mit `mapping_source='specific'`, der Rest fällt korrekt auf Taktik-Standard zurück. Danach über den admin-gesteuerten Import-Workflow (Abschnitt 6a.2) aktuell gehalten.
4. **Portfolio-Mapping** — Coverage-Matrix, Gap-Analyse, Verwaltung der eigenen Technologien/Leistungen (inkl. Self-Service-CRUD im Admin-Bereich, siehe Abschnitt 6a.1)
5. **Angriffsketten-Visualisierung** — MITRE-Stage-Strahl kombiniert mit Technik-Kacheln und farbcodierten Prevent/Detect/Respond-Unterbrechungen (Interaktionslogik 1:1 aus dem Prototyp übernehmbar, nur als React-Komponente statt Vanilla-JS)
6. **Sales-Briefing (LLM/PydanticAI)** — siehe Abschnitt 7, eigenes Modul, klar getrennt vom deterministischen Analyzer, konsumiert ausschließlich das kanonische Analyzer-Output-Schema
7. **Reporting/Export** — Executive Summary, technischer Report (PDF/DOCX)
8. **Admin-Bereich** — Portfolio-Verwaltung und Techniken-Import, siehe Abschnitt 6a

---

## 6a. Admin-Bereich (Portfolio-Pflege & Techniken-Import)

Beide Funktionen sind **kein "nice to have"**, sondern Grundvoraussetzung, damit das Tool nach dem initialen Aufbau ohne Entwicklerbeteiligung aktuell gehalten werden kann.

### 6a.1 Portfolio-Verwaltung (Self-Service)

- CRUD-Oberfläche für `portfolio_technology`: Technologie/Leistung anlegen, bearbeiten, deaktivieren (kein Hard-Delete, um historische Recommendations/Reports nicht zu verwaisen — stattdessen ein `active`-Flag)
- Zuordnung zu Capabilities über eine einfache Mehrfachauswahl gegen die `capability`-Tabelle (keine Textfelder/Freitext — sonst driften Capability-Namen auseinander und die Coverage-Matrix wird unbrauchbar)
- Direkte Vorschau der Auswirkung: beim Speichern zeigt die UI sofort, wie sich die Coverage-Matrix und die Gap-Liste durch die Änderung verschieben (serverseitig aus derselben Berechnungslogik wie der Portfolio-Tab, nicht separat gepflegt)
- Änderungshistorie pro Technologie (wer hat wann was geändert) — wichtig, da sich das direkt auf laufende Kundenempfehlungen auswirkt
- Zugriff ausschließlich für die Rolle `admin` (ggf. später eine feinere Rolle `portfolio_admin`, falls Sales-Leitung das pflegen soll, ohne volle System-Admin-Rechte zu haben)

### 6a.2 MITRE-Techniken-Import (admin-gesteuert, kein Live-Sync)

Da laut Abschnitt 8 keine Laufzeit-Internetverbindung erlaubt ist, läuft der Import **nicht automatisch**, sondern als bewusst angestoßener Admin-Workflow:

1. **Bereitstellung der Quelldaten**: Ein Admin lädt das aktuelle MITRE-ATT&CK-STIX-Bundle extern herunter (z. B. von einem Rechner mit Internetzugang) und lädt die Datei im Admin-Bereich hoch — kein direkter Zugriff der Anwendung auf `attack.mitre.org` zur Laufzeit.
2. **Parsen & Diff-Ansicht**: Das Backend parst das Bundle und zeigt **vor** jeder Übernahme eine Diff-Ansicht: neue Techniken, geänderte Namen/Taktik-Zuordnungen, als "deprecated" markierte Techniken. Sub-Technique-Beziehungen werden aus der STIX-Relationship übernommen (nicht aus der ID geparst, s. Abschnitt 5). Kein automatisches Überschreiben bestehender Daten ohne Review.
3. **Selektive Übernahme**: Admin bestätigt die Übernahme (ganz oder teilweise) — insbesondere wichtig, weil spezifische, händisch ausgearbeitete Mappings (`mapping_source = 'specific'`) durch einen Import **nicht versehentlich überschrieben** werden dürfen. Konflikte müssen explizit angezeigt werden.
4. **Versionierung & Rollback**: Jeder Import wird als `technique_import_batch` protokolliert (Quelldatei-Version/Hash, Zeitpunkt, durchführender Admin, Anzahl geänderter/neuer Techniken). Ein Rollback auf den Stand vor dem letzten Import muss möglich sein.
5. **Kein Zwang zur Vollständigkeit**: Der bestehende Taktik-Standardmapping-Mechanismus (Abschnitt 5) fängt neu importierte, noch nicht spezifisch gemappte Techniken automatisch ab — ein Import macht das Tool also nie "kaputt", auch wenn niemand sofort neue Capability-Zuordnungen für frisch importierte Techniken pflegt.

Zugriff ebenfalls nur für `admin`. Diese Funktion sollte **nicht** mit der Portfolio-Verwaltung (6a.1) verwechselt oder in derselben Ansicht vermischt werden — beide sind eigene Unterseiten im Admin-Bereich.

---

## 7. LLM-Integration mit PydanticAI (intern, kein externer Call)

Ziel: Aus den bereits **deterministisch berechneten** Analyzer-Ergebnissen (dem kanonischen Output-Schema, s. Abschnitt 2a/3) eine verständliche, geschäftsorientierte Argumentation für Sales generieren — das LLM erschafft keine neuen Fakten, sondern **formuliert vorhandene, geprüfte Daten** um. Das reduziert Halluzinationsrisiko drastisch.

**Prinzip:** Das Modell bekommt niemals Rohdaten oder freien Kontext, sondern ausschließlich die bereits strukturierten Analyzer-Ergebnisse als Input, und muss in einem festen Pydantic-Schema antworten.

```python
from pydantic import BaseModel, Field
from pydantic_ai import Agent

class MassnahmeArgumentation(BaseModel):
    massnahme: str
    kunden_nutzen: str = Field(description="1-2 Sätze, Geschäftssprache, keine Fachbegriffe")
    risiko_ohne_massnahme: str
    einwand_antizipation: str = Field(description="Ein wahrscheinlicher Kundeneinwand + Gegenargument")

class SalesBriefing(BaseModel):
    executive_summary: str = Field(description="3-4 Sätze, für Geschäftsführung")
    top_massnahmen: list[MassnahmeArgumentation] = Field(max_length=5)
    naechster_schritt: str

sales_agent = Agent(
    model="<interne-plattform-model-id>",  # gegen internes Gateway, kein externer Provider
    output_type=SalesBriefing,
    system_prompt=(
        "Du übersetzt technische Security-Findings in Geschäftsargumentation. "
        "Nutze ausschließlich die im Input gelieferten Fakten. Erfinde keine "
        "zusätzlichen Risiken, Zahlen oder Produktnamen. Nenne niemals ATT&CK-"
        "Technik-IDs oder rohe T-Nummern."
    ),
)

result = await sales_agent.run(
    f"Analyzer-Ergebnis (strukturiert, geprüft): {analyzer_result.model_dump_json()}"
)
```

**Guardrails, die Claude Code umsetzen muss:**
- Kein Freitext-Prompt aus Nutzereingabe direkt an das Modell — Input ist immer das bereits validierte, kanonische Analyzer-Ergebnis (Pydantic-Modell → JSON).
- Output wird gegen das Schema validiert (PydanticAI übernimmt das); bei Validierungsfehler kein Fallback auf ungeprüften Freitext, sondern Fehleranzeige.
- ▶ **Post-Processing-Guard (neu, v2):** Zusätzlich zur System-Prompt-Anweisung wird der generierte Text serverseitig auf ATT&CK-T-Nummern-Muster (`T\d{4}(\.\d{3})?`) geprüft — falls das Modell dennoch eine T-Nummer erzeugt, wird das Briefing zur Nachbearbeitung markiert statt ungeprüft ausgeliefert. Reines Vertrauen in den System-Prompt reicht bei einer Sales-Rolle ohne T-Nummern-Berechtigung nicht aus.
- `sales_briefing`-Datensätze sind **versioniert und mit Modellversion protokolliert** (Nachvollziehbarkeit, falls sich die LLM-Plattform-Version ändert).
- Optionales Freigabe-Flag (`reviewed_by`), falls ihr wollt, dass ein Techniker das Briefing vor Kundenkontakt kurz gegenliest — empfehlenswert für die ersten Monate im Betrieb.
- Der LLM-Aufruf ist ein potenziell langsamer externer Systemaufruf (interne Plattform, aber Latenz unklar) — sollte als asynchroner Hintergrund-Job umgesetzt werden, nicht als blockierender Request/Response-Zyklus.

---

## 8. Sicherheits- und Betriebsanforderungen

- **Keine Laufzeit-Internetverbindung erforderlich.** Die MITRE-ATT&CK-Referenzdaten (STIX-Bundle) werden **offline heruntergeladen und periodisch manuell/über einen internen Job importiert**, nicht live von `attack.mitre.org` zur Laufzeit gezogen.
- Alle Frontend-Assets (Fonts, Icon-Bibliotheken) müssen **selbst gehostet** werden, keine externen CDN-Aufrufe (im Prototyp wurden Google Fonts per CDN geladen — für die produktive Version durch lokal ausgelieferte Font-Dateien ersetzen).
- Rollenmodell mindestens: `analyst` (voller Zugriff, Techniken-Detailtiefe), `sales` (nur Sales-Briefing-Ansicht, keine T-Nummern-Rohdaten — technisch durchgesetzt über RBAC **und** den Post-Processing-Guard aus Abschnitt 7), `admin` (Portfolio-Verwaltung, MITRE-Techniken-Import, Nutzerverwaltung — siehe Abschnitt 6a).
- Audit-Log: Wer hat wann welches Engagement analysiert / welches Sales-Briefing generiert (Tabelle `audit_log`, siehe Abschnitt 5).
- ▶ **Schritt-1-Guardrail (neu, v2):** Solange kein Auth-Layer existiert (Schritt 1–ca. 6), darf die lokale Docker-Compose-Umgebung nur an `localhost`/interne Loopback-Interfaces binden, nie an eine gemeinsam erreichbare Netzwerkadresse — angesichts hochsensibler Daten auch in der Entwicklungsphase nicht verhandelbar.

---

## 9. Bewusst außerhalb von Version 1 (Scope-Abgrenzung, zeitlich — vgl. dauerhafte Abgrenzung in Abschnitt 2a)

Damit Schritt 1 nicht ausufert, explizit **nicht** Teil der ersten Ausbaustufe:

- Automatische Extraktion von T-Nummern aus hochgeladenen Red-Team-Reports (PDF/DOCX) — Version 1 arbeitet mit manueller T-Nummern-Eingabe/CSV
- Graph-Datenbank (PostgreSQL reicht vorerst)
- Multi-Tenant-Fähigkeit (zunächst interne Nutzung / ein Mandant)
- **Automatischer** STIX/TAXII-Live-Sync gegen `attack.mitre.org` zur Laufzeit (ausgeschlossen wegen fehlender Internetverbindung). Der **manuelle, admin-gesteuerte** Import (Abschnitt 6a.2) ist dagegen fester Bestandteil von Version 1, kein späterer Ausbau.

> Zur Klarstellung: Die Punkte in Abschnitt 2a ("Was die App bewusst nicht ist") sind **keine** späteren Ausbaustufen wie die Liste oben, sondern dauerhafte Produktidentität — sie sollen auch nach Version 5 nicht Realität werden, außer als bewusster, explizit abgewogener Kurswechsel.

---

## 10. Schritt 1 — konkreter Arbeitsauftrag für Claude Code

**Ziel von Schritt 1:** Lauffähiges Grundgerüst, lokal startbar, ohne jede Cloud-Abhängigkeit, mit der Datenbank-Basis für die 14 Taktiken und dem im Prototyp definierten Datensatz — **noch ohne LLM-Anbindung und ohne vollständige Analyzer-Logik**. Das Fundament muss stehen, bevor Logik und LLM folgen.

### 10.1 Repo-Struktur anlegen

```
breakpoint/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── models/          # SQLAlchemy-Modelle
│   │   ├── schemas/         # Pydantic-Schemas
│   │   └── core/            # Config, DB-Session
│   ├── alembic/
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/           # Dashboard, Engagements, Analyzer, Techniken, Portfolio, Reports
│   │   └── styles/
│   ├── package.json
│   └── Dockerfile
├── infra/
│   └── docker-compose.yml
├── docs/
│   └── (dieses Dokument + weitere ADRs)
└── README.md
```

### 10.2 Backend-Grundgerüst ▶ **aktualisiert in v2**

- FastAPI-App mit `/health`-Endpoint
- SQLAlchemy-Setup + Alembic-Migrationen für die Tabellen `tactic`, `technique`, `capability`, `control`, `technique_capability_mapping`, `technique_capability_mapping_capability`, `technique_capability_mapping_control`, `tactic_default_mapping` (+ deren Join-Tabellen) — zunächst ohne `portfolio_technology`, `engagement`, `sales_briefing` (kommt in Schritt 2–4)
- Seed-Skript (`scripts/seed_tactics.py`), das die 14 MITRE-Taktiken in der korrekten Reihenfolge einträgt (Namen 1:1 aus dem Prototyp: Reconnaissance … Impact)
- ▶ Seed-Skript für den **vollständigen Techniken-Katalog aus dem Prototyp** (~200 Techniken über alle 14 Taktiken, aus `TACTIC_GROUPS`), inkl. Ableitung von `parent_technique_id` aus der ID-Konvention
- Seed-Skript für die ~10 im Prototyp detailliert ausgearbeiteten Techniken (`KB`) als `technique_capability_mapping` mit `mapping_source='specific'`, plus alle 14 `tactic_default_mapping`-Einträge (`TACTIC_DEFAULTS`)

### 10.3 Frontend-Grundgerüst

- Vite + React + TypeScript + Tailwind aufsetzen
- Layout-Grundgerüst nach Prototyp: Sidebar (Dashboard, Engagements, ATT&CK Analyzer, Alle Techniken, Portfolio, Knowledge Base, Reports), Topbar, Routing (react-router)
- Farbsystem als Tailwind-Theme-Konfiguration übernehmen (Graphit-Töne, Amber/Ember als Aktionsfarbe, Prevent=Grün/Detect=Blau/Respond=Violett)
- Noch **keine** echte Anbindung an Backend-Endpunkte nötig — leere/statische Seiten reichen für Schritt 1, Hauptsache Navigation und Theme stehen

### 10.4 Docker Compose (lokal)

- Services: `db` (postgres:16), `backend` (FastAPI, mit Hot-Reload für Entwicklung), `frontend` (Vite Dev-Server)
- Keine externen Netzwerkabhängigkeiten zur Laufzeit; alle Services binden nur an localhost (s. Abschnitt 8)
- `.env.example` mit Platzhaltern (DB-Credentials, später `LLM_PLATFORM_BASE_URL` als Vorbereitung für Schritt 5 — aber in Schritt 1 noch nicht funktional genutzt)

### 10.5 Definition of Done für Schritt 1

- [ ] `docker compose up` startet DB, Backend und Frontend lokal ohne manuelle Zusatzschritte
- [ ] `GET /health` liefert `200 OK`
- [ ] Alembic-Migration läuft durch, `tactic`- und `technique`-Tabellen sind vollständig befüllt (14 Taktiken, ~200 Techniken, ~10 spezifische + 14 Taktik-Standard-Mappings)
- [ ] Frontend zeigt das Grundlayout mit funktionierender Tab-Navigation (noch ohne Live-Daten)
- [ ] README beschreibt lokalen Setup-Prozess vollständig, ohne Cloud-Voraussetzungen
- [ ] Kein Code-Pfad ruft eine externe URL zur Laufzeit auf (keine CDN-Fonts, keine externen APIs)
- [ ] Alle Compose-Services binden ausschließlich an localhost/interne Interfaces

---

## 11. Ausblick Schritt 2+ (grob, nicht Teil des aktuellen Auftrags)

- **Schritt 2:** Analyzer-Mapping-Engine im Backend (Portierung von `KB`, `TACTIC_DEFAULTS`, korrigierter Sub-Technique-Fallback-Logik aus Abschnitt 5), **ein** kanonisches Analyzer-Output-Schema, Prioritätsalgorithmus inkl. Kettenabdeckung (nicht nur Impact/Effort der Einzeltechnik, s. Abschnitt 2a), REST-Endpunkte für Analyse-Anfragen
- **Schritt 3:** Frontend-Tabs an echte Backend-Endpunkte anbinden (Analyzer, Techniken-Katalog)
- **Schritt 4:** Portfolio-Modul inkl. Coverage-Matrix, Gap-Analyse, **Admin-Bereich mit Self-Service-CRUD** (Abschnitt 6a.1)
- **Schritt 5:** PydanticAI-Sales-Briefing-Modul gegen interne LLM-Plattform (siehe Abschnitt 7), inkl. Post-Processing-Guard und asynchroner Verarbeitung
- **Schritt 6:** **Admin-Bereich MITRE-Techniken-Import** mit Upload, Diff-Ansicht, Versionierung/Rollback (Abschnitt 6a.2), STIX-Relationship-basierte Sub-Technique-Zuordnung
- **Schritt 7:** Reporting/Export, Rollenmodell/Auth-Anbindung, Audit-Log-UI

---

## 12. Offene Fragen, die vor oder während Schritt 1 geklärt werden sollten

1. Wie wird die interne LLM-Plattform angesprochen — OpenAI-kompatible API, proprietäres SDK, oder REST mit eigenem Auth-Schema? (Bestimmt die PydanticAI-Model-Provider-Konfiguration in Schritt 5.)
2. Gibt es unternehmensweite Standards für Python-Version, Linting (ruff/black), CI/CD-Pipeline und Container-Registry, an die sich Claude Code halten soll?
3. Welcher Auth-Provider ist im Datacenter Standard (Keycloak, Azure AD/Entra on-prem, LDAP, etwas anderes)?
4. Soll PostgreSQL als eigener Container mitgeliefert werden oder existiert bereits eine zentrale DB-Instanz, an die sich die Anwendung anbinden soll?
5. Gibt es bereits ein internes Basis-Image / einen Style-Guide für Docker-Images, den Claude Code verwenden soll, statt öffentliche Docker-Hub-Images direkt zu referenzieren?
6. In welchem Rhythmus soll das MITRE-Techniken-Update typischerweise erfolgen (z. B. quartalsweise bei größeren ATT&CK-Releases), und reicht ein einzelner Admin zur Freigabe, oder braucht es ein Vier-Augen-Prinzip, bevor ein Import produktiv übernommen wird?
7. ▶ *(neu, v2)* Welches selbst gehostete Logging-/Monitoring-Setup soll genutzt werden (z. B. Loki/Grafana), da externe SaaS-Fehler-Tracking-Dienste laut Abschnitt 2 ausgeschlossen sind?
8. ▶ *(neu, v2)* Gibt es eine Datenretention-/Löschpflicht für Engagement-Daten nach Projektabschluss (Kundenschwachstellen-Daten)?
9. ▶ *(neu, v2)* Genaue Gewichtungsformel für "Kettenabdeckung" in der Priorisierung (Abschnitt 2a/11): reine Zählung betroffener Techniken, oder gewichtet nach Position in der Kette (z. B. früher Breakpoint wertvoller)? Sollte vor Schritt 2 grob festgelegt werden, muss aber nicht in Schritt 1 final sein.

Diese Fragen blockieren Schritt 1 nicht zwingend (sinnvolle Defaults sind oben angegeben), sollten aber vor Schritt 5 (LLM-Anbindung) und vor einem produktiven Deployment final geklärt sein. Fragen 2 und 5 sollten idealerweise **vor** dem ersten Commit geklärt sein, da sie sich sonst flächendeckend (Formatierung, Dockerfiles) niederschlagen und später aufwändig nachgezogen werden müssten.
