# Projektauftrag für Claude Code: Breakpoint — ATT&CK-to-Action Plattform

> **v9 — ergänzt am 31.08.2026.** Neuer Abschnitt 10e konkretisiert Schritt 6 (MITRE-Import + Mitigations-Bootstrap) — **Planungsstand, noch nicht umgesetzt**. Basis sind echte, in dieser Session geprüfte STIX-Bundle-Daten statt Annahmen (Bundle-Größe ~54 MB, nur 44 von 268 `course-of-action`-Objekten mit gültiger M-Nummer, `kill_chain_phases`-Slugs entsprechen exakt der bestehenden `Tactic.id`-Konvention, TAXII in dieser Sandbox blockiert/GitHub-Raw erreichbar). Frühere Änderungen: ▶ **Update v8** — Schritt 5 (Sales-Briefing) umgesetzt, kritisch geprüft und Bugs behoben — Details in Abschnitt 10d.5 (DoD vollständig abgehakt inkl. Review-Ergebnis). ▶ **Update v7** — Abschnitt 10d konkretisierte Schritt 5 (Sales-Briefing/PydanticAI) im Vorfeld der Umsetzung: async ohne neue Infrastruktur (FastAPI `BackgroundTasks` statt Task-Queue, Grenzen dokumentiert), LLM-Anbindung als ungeklärte Annahme markiert (offene Frage 1 aus Abschnitt 12 bleibt offen), Post-Processing-Guard testbar ohne echte LLM-Anbindung dank PydanticAI `TestModel`/`FunctionModel`. ▶ **Update v6** — Abschnitt 6a.3 plant die Nutzung offizieller MITRE-Mitigations (M-Nummern) als Bootstrap für spezifische Mappings, inkl. eines konkreten Code-Funds (`resolve_technique()` schreibt `mapping_source` hartkodiert statt aus der DB zu lesen — muss vor Schritt 6 behoben werden). ▶ **Update v5** — Abschnitt 10c konkretisiert Schritt 4 (Portfolio-Modul). ▶ **Update v4** — Abschnitt 10b konkretisiert Schritt 3 (Frontend-Anbindung). ▶ **Update v3** — gezielte, enge Ausnahme von der Offline-Regel für den MITRE-Import (Abschnitt 2, 6a.2, 9). ▶ **Update v2** — aus der Review-Session vom 29.08.2026: kritische Prüfung des Auftrags + Code-Review des interaktiven HTML-Prototyps (`breakpoint-dashboard.html`) + eine vom Auftraggeber formulierte Zielbild-Zusammenfassung (siehe Abschnitt 2a).

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
| **Nur On-Prem / eigenes Datacenter** | Keine Cloud-Dienste (kein AWS/Azure/GCP-SaaS, keine externen APIs zur Laufzeit). Alles muss in eigenen Containern/VMs laufen. ▶ **Eine einzige, eng begrenzte Ausnahme** *(neu, v3)*: admin-getriggerte, ausgehende Abfragen der offiziellen MITRE-ATT&CK-Quellen (GitHub-Releases `mitre-attack/attack-stix-data` bzw. der öffentliche TAXII-2.1-Server `attack-taxii.mitre.org`) für den Techniken-Import, siehe Abschnitt 6a.2. Alle anderen Grundsätze (kein Datenabfluss, keine sonstigen externen APIs, kein automatischer/unbeaufsichtigter Sync) bleiben unverändert bestehen. |
| **Interne LLM-Plattform bereits vorhanden** | Kein eigenes Modell-Hosting aufbauen — die Anwendung integriert sich als Client gegen die bestehende Plattform (vermutlich OpenAI-kompatible oder proprietäre API; siehe offene Fragen in Abschnitt 12). |
| **PydanticAI bereits im Haus verfügbar** | Wird als Abstraktionsschicht für alle LLM-Aufrufe genutzt — nicht als rohe Prompt-Strings, sondern mit typisierten Input-/Output-Schemas. |
| **Hochsensible Daten** | Red-Team-Findings zeigen konkrete Kundenschwachstellen. Kein Datenabfluss nach außen, auch nicht indirekt (z. B. Telemetrie, Fehler-Tracking-SaaS, Font-CDNs im Frontend). |
| **Zwei sehr unterschiedliche Nutzergruppen** | Technische Analysten (Detailtiefe, T-Nummern, Capabilities) und Sales (Geschäftssprache, keine ATT&CK-Kenntnis vorausgesetzt) — UI und ggf. Rollenrechte müssen das abbilden, **aus derselben berechneten Wahrheit heraus** (siehe 2a). |
| **Portfolio ändert sich regelmäßig selbst** | Technologien/Leistungen und deren Capability-Zuordnungen dürfen nicht hart codiert sein — es braucht einen **Admin-Bereich**, über den das Team das Portfolio ohne Code-Änderung/Deployment pflegt (siehe Abschnitt 6a). |
| **MITRE ATT&CK entwickelt sich weiter** | ▶ *(v3)* MITRE veröffentlicht ca. zweimal jährlich (Frühjahr `X.0`, Herbst `X.1`) neue STIX-Daten. Der **admin-gesteuerte Import-Workflow** (Abschnitt 6a) holt das Bundle jetzt direkt per Admin-Klick von der offiziellen Quelle (s. o.), statt dass ein Admin es manuell auf einem separaten internetfähigen Rechner herunterladen und hochladen muss. Review/Diff/Freigabe bleiben unverändert manuell — kein automatischer, unbeaufsichtigter Sync. |
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
  mapping_source ENUM('specific','mitre_derived','tactic_default'),  -- ▶ (v6)
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

### 6a.2 MITRE-Techniken-Import (admin-gesteuert, kein automatischer Sync)

▶ *(v3)* Der Import läuft weiterhin **nicht automatisch/unbeaufsichtigt**, sondern als bewusst angestoßener Admin-Workflow — aber mit einer eng begrenzten Ausnahme von der sonstigen Offline-Regel (Abschnitt 2): das Bundle darf direkt von der offiziellen MITRE-Quelle geholt werden, statt den Umweg über einen separaten internetfähigen Rechner zu gehen.

1. **Bereitstellung der Quelldaten**: Ein Admin klickt im Admin-Bereich auf "Neue ATT&CK-Version prüfen/laden". Das Backend fragt **ausschließlich** die offizielle MITRE-Quelle ab — entweder die GitHub-Releases von `mitre-attack/attack-stix-data` oder den öffentlichen TAXII-2.1-Server (`attack-taxii.mitre.org/api/v21/`) — und lädt das aktuelle STIX-Bundle herunter. Alternativ kann ein Admin weiterhin eine Datei manuell hochladen (z. B. wenn der Server keinen Internetzugriff hat oder als Fallback). Kein Zugriff auf irgendeine andere externe Quelle oder zu einem anderen Zweck als diesem Import.
2. **Parsen & Diff-Ansicht**: Das Backend parst das Bundle und zeigt **vor** jeder Übernahme eine Diff-Ansicht: neue Techniken, geänderte Namen/Taktik-Zuordnungen, als "deprecated" markierte Techniken. Sub-Technique-Beziehungen werden aus der STIX-Relationship übernommen (nicht aus der ID geparst, s. Abschnitt 5). Kein automatisches Überschreiben bestehender Daten ohne Review.
3. **Selektive Übernahme**: Admin bestätigt die Übernahme (ganz oder teilweise) — insbesondere wichtig, weil spezifische, händisch ausgearbeitete Mappings (`mapping_source = 'specific'`) durch einen Import **nicht versehentlich überschrieben** werden dürfen. Konflikte müssen explizit angezeigt werden.
4. **Versionierung & Rollback**: Jeder Import wird als `technique_import_batch` protokolliert (Quelldatei-Version/Hash, Zeitpunkt, durchführender Admin, Anzahl geänderter/neuer Techniken). Ein Rollback auf den Stand vor dem letzten Import muss möglich sein.
5. **Kein Zwang zur Vollständigkeit**: Der bestehende Taktik-Standardmapping-Mechanismus (Abschnitt 5) fängt neu importierte, noch nicht spezifisch gemappte Techniken automatisch ab — ein Import macht das Tool also nie "kaputt", auch wenn niemand sofort neue Capability-Zuordnungen für frisch importierte Techniken pflegt.

Zugriff ebenfalls nur für `admin`. Diese Funktion sollte **nicht** mit der Portfolio-Verwaltung (6a.1) verwechselt oder in derselben Ansicht vermischt werden — beide sind eigene Unterseiten im Admin-Bereich.

### 6a.3 MITRE-Mitigations als Bootstrap für spezifische Mappings *(neu, v6)*

**Idee:** MITRE-Mitigations (M-Nummern, STIX-Objekt `course-of-action`) sind bereits im selben STIX-Bundle enthalten, das der Import in 6a.2 ohnehin zieht, und über `mitigates`-Relationships zahlreichen Techniken zugeordnet — kein zusätzlicher Datenimport nötig. Das kann die Anzahl der Techniken mit technique-spezifischem statt nur taktik-grobem Mapping potenziell von 10 (Schritt 1) auf einen Großteil des Katalogs heben, ohne jede Technik einzeln von Hand zu kuratieren.

**Warum sich der Zusatzaufwand lohnt, trotz der Einschränkungen unten:** Kettenabdeckung (Abschnitt 2a/10a.4) ist umso aussagekräftiger, je spezifischer die Controls sind — 14 taktik-grobe Control-Sets, die sich Dutzende Techniken teilen, verwässern das Signal "wie viele beobachtete Techniken bricht diese Maßnahme wirklich". Technique-spezifische Prevent-Controls verbessern das Herzstück der Übersetzungskette direkt, nicht nur die Katalog-Optik.

**Kritische Einschränkungen (bewusst vor der Umsetzung geklärt, nicht erst beim Bauen entdeckt):**

1. **Nur Prevent, nicht Detect/Respond.** MITRE liefert für Mitigations keine strukturierte Detect-/Respond-Taxonomie — nur ein Freitext-"Detection"-Feld je Technik, keine eigene ID-Struktur wie bei Mitigations. Detect/Respond bleiben Handarbeit; dieser Bootstrap verbessert ausschließlich die Prevent-Spalte. MITRE D3FEND bietet zwar eine offizielle Mapping-Tabelle ATT&CK-Mitigations→D3FEND-Techniken, das ist aber ein eigenes Framework mit eigener Komplexität — bewusst **nicht** jetzt einbeziehen (Scope-Disziplin, vgl. "kein Navigator-Klon"-Prinzip aus Abschnitt 2a), höchstens ein separat zu bewertender späterer Ausbau.
2. **Kein Impact/Effort von MITRE.** `technique_capability_mapping.impact`/`.effort` sind NOT NULL; MITRE liefert dafür keine Werte — das ist Breakpoints eigene Geschäftseinschätzung. Automatisch importierte Mitigation-Mappings übernehmen deshalb **impact/effort vom `tactic_default_mapping` derselben Taktik** als Startwert (transparente Näherung, kein Blocker für die Automatisierung) — ein Admin kann das später technikweise verfeinern.
3. **Nicht jede Mitigation bildet sauber auf eine Capability ab.** Manche M-Nummern sind konkret und technologienah (M1032 Multi-Factor Authentication → Capability "MFA"), andere sind Prozess-/Policy-Empfehlungen ohne Technologie-Bezug (z. B. "Application Developer Guidance", "User Training" grenzwertig zu "Security Awareness"). Realistisch mit Fällen rechnen, die auf gar keine bestehende Capability abgebildet werden — dann bleibt diese eine Mitigation für den Bootstrap ungenutzt, das ist kein Fehler, nur unvollständige Abdeckung.
4. **`mapping_source` bekommt einen dritten Wert — echte Migration, kein Zero-Cost-Change.** Ein automatisch aus MITRE übernommenes Mapping ist weder handkuratiert (`specific`) noch nur taktik-grob (`tactic_default`). Neuer Wert `mitre_derived`, neue Präzedenz in der Fallback-Kette (Abschnitt 10a.3): `specific` (Mensch) > `mitre_derived` (MITRE, automatisch, nur Prevent) > `tactic_default`. Das ist genau der Fall, vor dem die frühere Warnung zu nativen Postgres-ENUMs (schwerer per Alembic erweiterbar) real wird — technisch machbar (`ALTER TYPE … ADD VALUE` außerhalb einer Transaktion, von Alembic unterstützt), aber einzuplanen, nicht "nebenbei".
5. ▶ **Konkreter Code-Fund beim Review dieses Plans:** `resolve_technique()` (`backend/app/services/analyzer.py`, aktuell Zeilen 62 und 91) schreibt `mapping_source` als **hartkodierten String** (`"specific"` bzw. `"tactic_default"`) in `TechniqueResult`, statt den tatsächlichen Wert aus der `TechniqueCapabilityMapping`-Zeile zu lesen. Solange nur diese zwei Werte existieren, ist das unsichtbar richtig — sobald `mitre_derived`-Zeilen in derselben Tabelle landen, würde dieser Code sie stillschweigend als `"specific"` ausgeben. **Muss vor Schritt 6 auf `mapping.mapping_source.value` umgestellt werden**, sonst bricht die Transparenz-Garantie aus Abschnitt 2a ("woher kommt diese Empfehlung") genau an der Stelle, die sie eigentlich schützen soll.
6. **Geht durch denselben Review-Gate wie jeder Import, kein Sonderfall.** Mitigation-Mappings erscheinen in der Diff-Ansicht (6a.2, Punkt 2) wie neue/geänderte Techniken; ein Admin bestätigt vor Übernahme. Überschreibt **nie** eine bestehende `specific`-Zeile (gleiche Regel wie 6a.2, Punkt 3). Die Sub-Technique-Fallback-Logik (`parent_technique_id`-Traversal) gilt für `mitre_derived` genauso wie für `specific` — keine neue Logik, nur ein weiterer möglicher `mapping_source`-Wert an derselben Stelle.
7. **Der Mitigation→Capability-Crosswalk ist kuratierte Seed-Daten, keine neue Admin-UI-Fläche.** Konsistent damit, dass auch `capability` selbst nicht über eine Admin-Oberfläche gepflegt wird (nur Portfolio-Technologie↔Capability ist Self-Service, Abschnitt 6a.1) — der Crosswalk lebt als Liste im Code (analog `ALL_CAPABILITIES` in `seed_data.py`), von einem Entwickler erweitert, wenn ein Import neue M-Nummern zeigt.

**Aufwand-Realitätscheck:** Kein Nebenbei-Task innerhalb des ohnehin geplanten Schritt 6 — der STIX-Parser muss zusätzlich `course-of-action`-Objekte und `mitigates`-Relationships auswerten, die Diff-Ansicht um eine dritte Kategorie erweitern, und Enum/Fallback-Kette ändern sich. Als eigener, benannter Teilschritt innerhalb Schritt 6 einplanen (Konkretisierung folgt, sobald Schritt 6 selbst dran ist), nicht implizit "auf dem Weg mitnehmen".

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

- **Keine Laufzeit-Internetverbindung für Kundendaten.** Red-Team-Findings, Engagements, Sales-Briefings etc. verlassen das Datacenter nie. ▶ *(v3)* Einzige Ausnahme: admin-getriggerte, ausgehende Abfragen der offiziellen MITRE-Quellen (GitHub-Releases/TAXII, s. Abschnitt 6a.2) für den Techniken-Import — nur lesend, nur diese zwei Hosts, nur wenn ein Admin den Import aktiv anstößt (kein Hintergrund-Job, kein automatischer Poll). Diese Ausnahme muss auf Netzwerkebene (Egress-Firewall/Proxy-Allowlist) auch technisch so eng begrenzt durchgesetzt werden, nicht nur durch Anwendungslogik.
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
- **Automatischer, unbeaufsichtigter** STIX/TAXII-Sync (Hintergrund-Job, der ohne Admin-Aktion neue Versionen zieht und/oder übernimmt) — ▶ *(v3)* ausgeschlossen, weil er den Review-vor-Übernahme-Schritt aushebeln würde, nicht mehr wegen fehlender Internetverbindung. Der **admin-getriggerte** Import gegen die offizielle MITRE-Quelle (Abschnitt 6a.2) ist dagegen fester Bestandteil von Version 1, kein späterer Ausbau.

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

## 10a. Schritt 2 — konkreter Arbeitsauftrag *(neu, v3)*

**Ziel von Schritt 2:** Aus dem Schritt-1-Grundgerüst wird eine echte, deterministische Analyzer-Engine — Technik-Codes rein, priorisierte Maßnahmen raus. Noch **ohne** Frontend-Anbindung (Schritt 3), Portfolio-Fit (Schritt 4) oder LLM (Schritt 5). Portfolio-Fit ist im Ergebnis-Schema bereits als Feld vorgesehen, aber bis Schritt 4 immer leer — damit sich die Schnittstelle später nicht ändert.

**Lückenschluss gegenüber der bisherigen Grob-Planung:** In Abschnitt 11 (alt) war nirgends festgelegt, wer `engagement`/`finding` anlegt — Schritt 3 kümmert sich laut Abschnitt 11 nur um Analyzer- und Techniken-Katalog-Tab, nicht um den Engagements-Tab. Ohne eine persistierte Engagement/Finding-Ebene ist die Analyzer-Engine aber nur ein zustandsloser Rechner ohne Anbindung an "wer hat wann welches Engagement analysiert" (Audit-Log-Pflicht, Abschnitt 8). Deshalb wird die Engagement/Finding-Persistenz jetzt explizit **Teil von Schritt 2**, nicht länger implizit vorausgesetzt.

### 10a.1 Datenmodell-Ergänzung

Neue Alembic-Migration auf Basis der Schritt-1-Migration:

```
engagement
  id (PK), name, external_ref (nullable), created_at, status

finding
  id (PK), engagement_id (FK), technique_id (FK), raw_source_ref (nullable)
```

▶ **Bewusst nicht gebaut:** die `recommendation`-Tabelle aus Abschnitt 5. Die in Abschnitt 5 offen gelassene Entscheidung ("materialisiert oder zur Laufzeit berechnet") wird hiermit getroffen: **zur Laufzeit berechnet**, nicht materialisiert. Begründung: YAGNI — Materialisierung ist eine Performance-Optimierung, für die es noch keinen Bedarfsnachweis gibt, und sie würde eine Cache-Invalidierungslogik erfordern (was passiert bei einem nachträglichen MITRE-Import oder einer Mapping-Änderung mit bereits gespeicherten Empfehlungen?), die Schritt 2 unnötig verkompliziert. Diese Entscheidung kann revidiert werden, sobald echte Performance-Daten das nahelegen.

### 10a.2 Kanonisches Analyzer-Output-Schema (`app/schemas/analyzer.py`)

Das in Abschnitt 2a geforderte **eine** Schema, das später unverändert sowohl die Analyst-UI rendert als auch an den PydanticAI-Sales-Agent (Schritt 5) geht:

```python
class TechniqueResult(BaseModel):
    technique_id: str
    technique_name: str
    tactic_name: str
    mapping_source: Literal["specific", "tactic_default"]
    resolved_via_technique_id: str | None  # None bei tactic_default; sonst die
        # Technik, deren Mapping tatsächlich griff — bei direktem Treffer sie
        # selbst, bei Sub-Technique-Fallback ihre Basistechnik. Macht die
        # Herkunft einer Empfehlung vollständig nachvollziehbar (Transparenz-
        # Prinzip, s. Abschnitt 5), ohne die mapping_source-ENUM aufzublähen.
    impact: Literal["niedrig", "mittel", "hoch", "sehr_hoch"]
    effort: Literal["niedrig", "mittel", "hoch"]
    capabilities: list[str]
    controls: list[ControlRef]  # {category, label}
    portfolio_fit: list[str] = []  # Platzhalter bis Schritt 4

class PrioritizedMeasure(BaseModel):
    control_id: int
    category: Literal["prevent", "detect", "respond"]
    label: str
    priority_rank: int
    chain_coverage_count: int  # Anzahl unterschiedlicher analysierter Techniken,
        # die diese Maßnahme referenzieren
    affected_technique_ids: list[str]

class AnalyzerResult(BaseModel):
    input_codes: list[str]
    techniques: list[TechniqueResult]
    unknown_codes: list[str]  # Codes, die auch im Katalog nicht existieren —
        # sichtbar, nie stillschweigend verworfen (Prinzip "keine Sackgassen")
    prioritized_measures: list[PrioritizedMeasure]
```

### 10a.3 Mapping-Resolution (`app/services/analyzer.py`)

Implementiert die in Abschnitt 5 **korrigierte** Fallback-Kette (nicht die Prototyp-Heuristik):

1. Exakter Treffer in `technique_capability_mapping` → `mapping_source="specific"`, `resolved_via_technique_id` = die Technik selbst.
2. Sonst: `parent_technique_id`-Traversal — hat die Basistechnik ein spezifisches Mapping? → `mapping_source="specific"`, `resolved_via_technique_id` = Basistechnik-ID.
3. Sonst: `tactic_default_mapping` der Taktik der Technik → `mapping_source="tactic_default"`, `resolved_via_technique_id=None`.
4. Sonst (Technik-Code auch nicht im Katalog): landet in `unknown_codes`.

▶ *(v6, Vormerkung für Schritt 6)* Wird um eine vierte Stufe zwischen 1./2. und 3. erweitert (`mitre_derived`, s. Abschnitt 6a.3) — dabei muss `mapping_source` dynamisch aus der DB gelesen werden, aktuell steht an dieser Stelle noch der hartkodierte String `"specific"` (Abschnitt 6a.3, Punkt 5).

### 10a.4 Prioritätsalgorithmus (v1, bewusst einfach)

Löst die in Abschnitt 12 (Frage 9) offene Gewichtungsfrage für Schritt 2 pragmatisch: Aggregation pro **eindeutigem Control** über alle analysierten Techniken hinweg (via die Join-Tabellen), dann Sortierung nach:

1. `chain_coverage_count` absteigend (Maßnahme, die mehr der eingegebenen Techniken adressiert, gewinnt)
2. bei Gleichstand: höchster `impact` unter den abgedeckten Techniken, absteigend
3. bei Gleichstand: niedrigster `effort`, aufsteigend

Bewusst **kein** Gewichten nach Kettenposition (z. B. "früher Breakpoint zählt mehr") — das bleibt ein möglicher v2-Ausbau des Algorithmus, sobald echte Nutzung zeigt, ob das gebraucht wird. `priority_rank` bleibt, wie in Abschnitt 2 festgeschrieben, unabhängig von Portfolio-Fit.

### 10a.5 Endpunkte (`app/api/`)

- `POST /api/analyze` — zustandslos: Liste roher Technik-Code-Strings im Body (Freitext/CSV-Parsing serverseitig: Split auf Whitespace/Komma/Semikolon, Uppercase, Dedup — analog `parseCodes()` im Prototyp) → `AnalyzerResult`. Deckt den Analyzer-Tab ab, der im Prototyp ohne Engagement-Bindung funktioniert.
- `POST /api/engagements` — Engagement anlegen (`name`, optional `external_ref`)
- `POST /api/engagements/{id}/findings` — Technik-Codes zu einem Engagement hinzufügen (gleiches Parsing wie oben)
- `GET /api/engagements/{id}/analysis` — berechnet `AnalyzerResult` zur Laufzeit aus den `finding`-Zeilen des Engagements (kein Caching, s. 10a.1)

Unbekannte Codes sind **kein Fehlerfall** (kein 4xx) — sie erscheinen in `unknown_codes`. Leere Eingabe liefert ein leeres `AnalyzerResult` (200), keinen Fehler.

### 10a.6 Tests

- Mapping-Resolution: alle drei Fallback-Stufen + unbekannter Code, inkl. Regressionstest für den in Abschnitt 5 dokumentierten Prototyp-Bug (ein Sub-Technique-Code ohne eigenes Mapping darf **nicht** das Mapping eines unverwandten Geschwister-Codes erben)
- Prioritätsalgorithmus: Dedup/Aggregation, wenn zwei Techniken denselben Control referenzieren
- Integrationstest: `POST /api/analyze` mit der Beispielkette aus dem Prototyp (`T1566.001, T1078, T1021.001, T1059.001`)

### 10a.7 Definition of Done für Schritt 2

- [x] Migration für `engagement`/`finding` läuft durch
- [x] `POST /api/analyze` liefert für die Prototyp-Beispielkette ein `AnalyzerResult` mit plausibler Priorisierung
- [x] Sub-Technique-Fallback nachweislich korrekt (nicht die Prototyp-Präfix-Heuristik)
- [x] Unbekannte Codes landen sichtbar in `unknown_codes`, nie stillschweigend verworfen
- [x] Alle Tests aus 10a.6 grün (25 Tests gesamt inkl. Schritt 1)

**Ergebnis der kritischen Review-Runde nach Implementierung** *(neu, v3)*: Zwei echte Bugs gefunden und behoben, bevor sie in Betrieb gegangen wären:
- **Priorisierung war nicht deterministisch**: Bei exakt gleicher Kettenabdeckung/Impact/Effort entschied die zufällige Eingabereihenfolge der Techniken über die Rangfolge. Fix: `control_id` als viertes, stabiles Tie-Break-Kriterium ergänzt (Abschnitt 10a.4) — dieselbe Technik-Menge liefert jetzt unabhängig von der Eingabereihenfolge dieselbe Priorisierung.
- **`GET /api/engagements/{id}/analysis` hatte kein `ORDER BY`**: `SELECT DISTINCT` ohne Sortierung liefert in Postgres keine garantierte, stabile Reihenfolge. Fix: `ORDER BY technique_id` ergänzt.

Geprüft und bewusst **nicht** geändert: kein Unique-Constraint auf `finding(engagement_id, technique_id)` — hätte das für Version 1 explizit vorgesehene `raw_source_ref`-Feld (mehrere Fundstellen derselben Technik im selben Report, Abschnitt 5/9) unnötig für die spätere automatische Report-Extraktion eingeschränkt. Die Analyse dedupliziert bereits zuverlässig auf Lesepfad-Ebene.

---

## 10b. Schritt 3 — konkreter Arbeitsauftrag *(neu, v4)*

**Ziel von Schritt 3:** Die drei in Abschnitt 11 genannten Tabs (Analyzer, Engagements, Techniken-Katalog) zeigen echte Daten vom Schritt-2-Backend statt statischer Platzhalter. Portfolio, Knowledge Base und Reports bleiben `PagePlaceholder` bis Schritt 4/6/7.

**Zwei Lücken beim Planen gefunden, bevor sie mitten in der Umsetzung aufgefallen wären:**
1. **Kein Backend-Endpunkt für den Techniken-Katalog.** Schritt 2 hat nur `POST /api/analyze` (nimmt konkrete Codes entgegen) gebaut — keinen Endpunkt, der "alle ~188 Techniken mit ihrem Mapping-Status" auflistet. Der Prototyp-Tab "Alle Techniken" (Filter nach Taktik/Status, Badges "Spezifisch"/"Taktik-Standard"/"Kein Mapping") braucht aber genau das. Wird jetzt Teil von Schritt 3 (10b.1).
2. **Vitest/React Testing Library nie eingerichtet.** Abschnitt 4 legt Vitest als Frontend-Test-Framework fest, Schritt 1 hat aber nur das Vite/React/Tailwind-Grundgerüst aufgesetzt, keinen Testrunner. Wird jetzt Teil von Schritt 3 (10b.5), damit Komponententests nicht ungeschrieben bleiben, nur weil nie ein guter Einstiegspunkt kam.

Außerdem technisch zwingend, aber in der bisherigen Grobplanung nicht explizit erwähnt: **CORS**. Frontend (`127.0.0.1:5173`) und Backend (`127.0.0.1:8000`) sind unterschiedliche Origins — ohne CORS-Konfiguration blockt der Browser jeden Fetch-Aufruf. Ebenfalls Teil von 10b.1.

### 10b.1 Backend-Ergänzungen

- **CORS-Middleware** in `app/main.py`: `allow_origins` explizit auf die Frontend-Dev-URL beschränkt (kein Wildcard `*`) — konsistent mit dem "so eng wie möglich"-Prinzip aus Abschnitt 8.
- **`GET /api/techniques`** — neuer, leichtgewichtiger Endpunkt für den Katalog-Tab. Bewusst **nicht** durch 188× `resolve_technique()` (das wäre pro Aufruf hunderte Einzelqueries), sondern eine eigene, schlanke Abfrage:
  ```python
  class TechniqueSummary(BaseModel):
      technique_id: str
      technique_name: str
      tactic_name: str
      mapping_source: Literal["specific", "tactic_default"]

  class TechniqueCatalogResult(BaseModel):
      techniques: list[TechniqueSummary]
      total: int
  ```
  Serverseitige Filter als Query-Parameter (`?tactic=...&status=...&q=...`), analog zu den Filtern im Prototyp-Tab. `mapping_source` wird effizient über eine `LEFT JOIN`/`EXISTS`-Abfrage gegen `technique_capability_mapping` bestimmt (direkt oder über `parent_technique_id`), nicht über die pro-Technik-Fallback-Kette aus 10a.3 — die bleibt dem `/api/analyze`-Pfad vorbehalten, wo tatsächlich vollständige Capability-/Control-Daten gebraucht werden.

### 10b.2 Frontend: API-Client & Typen

- **Typen aus dem OpenAPI-Schema generieren**, nicht von Hand nachpflegen — sonst driften Frontend-Typen und das kanonische Backend-Schema (Abschnitt 2a) unbemerkt auseinander. Ablauf: `python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > openapi.json` (Backend muss dafür nicht laufen) + `openapi-typescript` als Dev-Dependency, Output nach `frontend/src/lib/api-types.ts`, per `npm run generate-types` — kein manuell gepflegtes Interface, das aus dem Tritt geraten kann.
- Dünner `fetch`-Wrapper (`frontend/src/lib/api.ts`) mit Basis-URL aus `import.meta.env.VITE_API_BASE_URL` (Default `http://127.0.0.1:8000`), typisiert mit den generierten Typen.
- **Datenfetching-Bibliothek: TanStack Query.** Begründung: mehrere Seiten (Analyzer, Engagements, Techniken-Katalog, später Portfolio/Reports) brauchen wiederkehrend Loading/Error/Cache-Verhalten für GET/POST-Aufrufe gegen dasselbe Backend — das von Hand mit `useEffect`/`useState` nachzubauen skaliert schlecht und ist fehleranfälliger als eine etablierte, kleine, weit verbreitete Bibliothek. Kein Server-seitiger Zustand, keine Cloud-Abhängigkeit (rein client-seitig) — verträgt sich mit den Rahmenbedingungen aus Abschnitt 2.

### 10b.3 Globaler Engagement-Kontext

Die Topbar hat seit Schritt 1 bereits die UI für eine Engagement-Auswahl ("Kein Engagement ausgewählt"). Schritt 3 macht sie funktional: ein `EngagementContext` (React Context + `localStorage`-Persistenz für das zuletzt gewählte Engagement) hält die `engagement_id` global, damit Analyzer- und Dashboard-Seite sie konsistent lesen können, ohne Props durch den ganzen Baum zu reichen.

### 10b.4 Seiten anbinden

- **Analyzer-Tab**: Textarea + "Analysieren"-Button (1:1 aus dem Prototyp), `POST /api/analyze` über TanStack Query, Rendering von Technik-Karten und priorisierten Maßnahmen aus dem `AnalyzerResult` — dieselben Anzeige-Komponenten werden in 10b.4 auch für die Engagement-Analyse wiederverwendet (Auszahlung des kanonischen Schemas: eine Ergebnis-Komponente, zwei Datenquellen).
- **Engagements-Tab**: Liste bestehender Engagements, Anlegen-Formular (`POST /api/engagements`), Auswahl setzt den `EngagementContext`; Detailansicht zeigt Findings-Eingabe (`POST /api/engagements/{id}/findings`) und die berechnete Analyse (`GET /api/engagements/{id}/analysis`) — letztere über dieselben Komponenten wie der Analyzer-Tab.
- **Techniken-Katalog-Tab**: Tabelle gegen `GET /api/techniques`, Filter (Taktik-Dropdown, Status-Dropdown, Suche) als Query-Parameter, Status-Badges wie im Prototyp.
- **Dashboard**: Stat-Kacheln (aktuell `—`-Platzhalter) zeigen bei gewähltem Engagement echte Zahlen aus dessen Analyse; ohne gewähltes Engagement bleibt der bisherige Hinweistext.

### 10b.5 Tests

- Vitest + React Testing Library + `@testing-library/jest-dom` einrichten (`npm run test`), `msw` (Mock Service Worker) für die API-Mocks in Komponententests — kein echter Backend-Aufruf in Frontend-Tests.
- Komponententests: Analyzer-Formular (Eingabe → Aufruf → Ergebnis-Rendering), Techniken-Katalog-Filter, Engagement-Anlegen-Formular (Validierungsfehler bei leerem Namen, konsistent mit dem Backend-422 aus Abschnitt 10a.7).
- Backend: Test für den neuen `GET /api/techniques`-Endpunkt (Filter, Status-Zuordnung, Zählung).

### 10b.6 Definition of Done für Schritt 3

- [x] CORS erlaubt Frontend-Origin, blockt alles andere (enge Allowlist, kein Wildcard)
- [x] `GET /api/techniques` liefert für alle 188 Techniken den korrekten Status (10 spezifisch = exakt die KB-Einträge aus Schritt 1, Rest Taktik-Standard)
- [x] Analyzer-Tab liefert für die Prototyp-Beispielkette ein sichtbares Ergebnis ohne Konsolenfehler (im Browser mit Playwright end-to-end verifiziert)
- [x] Engagement anlegen → Findings hinzufügen → Analyse ansehen funktioniert Ende-zu-Ende im Browser (inkl. Kettenabdeckung über mehrere Techniken hinweg sichtbar geprüft)
- [x] Techniken-Katalog-Tab filtert nach Taktik und Status (sowie Suche — im Browser geprüft: 188→10 bei Taktik-Filter, 188→10 bei Status-Filter, 188→4 bei Suche)
- [x] `npm run generate-types` läuft ohne laufenden Server durch und wird nicht manuell umgangen
- [x] `npm run test` (Vitest, 6 Tests) grün, `pytest` (32 Tests) weiterhin grün, `ruff` und `oxlint` sauber

**Ergebnis der kritischen Review-Runde nach Implementierung** *(neu, v4)*: Eine dritte Lücke zusätzlich zu den beiden bereits beim Planen gefundenen (10a-Intro): Es gab keinen `GET /api/engagements`-Listen-Endpunkt, den der Engagements-Tab aber braucht — ergänzt, sortiert nach `id` statt `created_at` (kollisionsfrei, statt auf Sekunden-Auflösung von `now()` zu vertrauen). Weitere Funde: `GET /api/techniques` erzeugte durch `joinedload()` zusätzlich zu einem expliziten Taktik-Filter-Join einen doppelten JOIN auf `tactic` — behoben durch `contains_eager()`, das den ohnehin nötigen Join wiederverwendet. Fehlende Fehleranzeige bei fehlgeschlagenem Engagement-Anlegen bzw. Findings-Hinzufügen im Frontend ergänzt (Konsistenz mit dem Analyzer-Tab). Veralteten "Schritt 1"-Hinweistext in der Sidebar aktualisiert.

---

## 10c. Schritt 4 — konkreter Arbeitsauftrag *(neu, v5)*

**Ziel von Schritt 4:** Das eigene Portfolio wird pflegbar und wirkt sich sichtbar auf Analyzer-Ergebnisse aus. Zwei Teile: (a) Self-Service-CRUD für `portfolio_technology` (Abschnitt 6a.1), (b) Aktivierung des bisher immer leeren `portfolio_fit`-Felds im kanonischen Analyzer-Schema (Abschnitt 10a.2) — der Auszahlungsmoment für das seit Schritt 2 vorbereitete Schema.

**Bewusst weiterhin offen:** Zugriff nur für Rolle `admin` (Abschnitt 6a.1) kann noch nicht durchgesetzt werden — es gibt noch kein Auth (Schritt 7). Das Portfolio-CRUD ist in Schritt 4 wie Engagements/Analyzer für alle offen; die Rollen-Beschränkung wird in Schritt 7 nachgezogen. `portfolio_technology_history.changed_by` bleibt aus demselben Grund vorerst `NULL` (kein Nutzerkonzept vorhanden) — Feld existiert schon, damit sich das Schema in Schritt 7 nicht mehr ändern muss.

### 10c.1 Datenmodell

```
portfolio_technology
  id (PK), name, type, active (bool, default true)

portfolio_technology_capability   -- Join statt Freitext (Abschnitt 6a.1: "keine
  portfolio_technology_id (FK), capability_id (FK)   Textfelder — sonst driftet die Coverage-Matrix auseinander")

portfolio_technology_history
  id (PK), portfolio_technology_id (FK), changed_by (nullable, s.o.),
  changed_at, field_changed, old_value, new_value
```

Kein Hard-Delete: Deaktivieren setzt `active=false` (Abschnitt 6a.1 — historische Recommendations/Reports dürfen nicht verwaisen). Jede Änderung (Anlegen, Bearbeiten, Deaktivieren) schreibt einen `portfolio_technology_history`-Eintrag pro geändertem Feld.

### 10c.2 Portfolio-Fit-Integration im Analyzer

`resolve_technique()` (Abschnitt 10a.3) bekommt einen zusätzlichen Schritt: für jede Capability der Technik werden aktive Portfolio-Technologien nachgeschlagen, die diese Capability abdecken (analog `matchPortfolio()`/`techsForCapability()` aus dem Prototyp) → befüllt `TechniqueResult.portfolio_fit`. **Nicht angefasst:** `_prioritize()` (Abschnitt 10a.4) — Portfolio-Fit bleibt reine Zusatzinformation ohne jeden Einfluss auf `priority_rank`, wie in Abschnitt 2 als nicht verhandelbar festgeschrieben. Ein Regressionstest sichert das explizit ab (gleiche Rangfolge mit und ohne Portfolio-Daten).

### 10c.3 Coverage-Matrix & Gap-Analyse

Neuer Service (`app/services/portfolio.py`): für jede Capability in der `capability`-Tabelle, welche aktiven Portfolio-Technologien sie abdecken. Gap = Capability ohne jede abdeckende Technologie. Eine Berechnung bedient sowohl den Portfolio-Tab (Matrix + Gap-Panel) als auch — indirekt über dieselbe Nachschlage-Logik — 10c.2.

### 10c.4 Endpunkte (`app/api/portfolio.py`)

- `GET /api/portfolio/technologies` — Liste (aktive; `?include_inactive=true` für alle)
- `POST /api/portfolio/technologies` — anlegen (`name`, `type`, `capability_ids`)
- `PATCH /api/portfolio/technologies/{id}` — bearbeiten, schreibt History pro geändertem Feld
- `POST /api/portfolio/technologies/{id}/deactivate` — `active=false`, History-Eintrag
- `GET /api/portfolio/technologies/{id}/history` — Änderungshistorie
- `GET /api/portfolio/coverage` — Coverage-Matrix + Gap-Liste
- ▶ `GET /api/capabilities` *(ergänzt beim Bauen)* — ID-tragende Referenzliste aller Capabilities, nötig für die Mehrfachauswahl im Formular (die Coverage-Antwort liefert nur Namen, keine IDs)

Kein eigener "Vorschau"-Endpunkt: die im Prototyp geforderte "sofortige Vorschau" (Abschnitt 6a.1) entsteht einfacher dadurch, dass das Frontend nach jeder Mutation die Coverage-Query invalidiert (gleiches Muster wie Findings→Analyse in Schritt 3) — eine Berechnung, kein Sonderfall.

### 10c.5 Frontend

Portfolio-Tab (bisher `PagePlaceholder`): Technologie-Karten, Anlegen/Bearbeiten-Formular mit **Capability-Mehrfachauswahl** (Checkboxen gegen `GET /api/capabilities` — nicht Freitext), Deaktivieren-Button, Coverage-Matrix-Tabelle, Gap-Panel, Verlauf pro Technologie. `TechniqueCard` (Schritt 3) zeigt `portfolio_fit` jetzt als eigene Chip-Zeile statt eines leeren Arrays.

### 10c.6 Definition of Done für Schritt 4

- [x] Migration für die drei neuen Tabellen läuft durch
- [x] Portfolio-Technologie anlegen → Capability zuordnen → erscheint sofort in Coverage-Matrix und verschwindet aus der Gap-Liste (im Browser verifiziert: MFA verschwand nach Anlegen von "Okta" mit Capability MFA)
- [x] Deaktivieren ist Soft-Delete (Zeile bleibt in der DB, `active=false`, verschwindet aus Coverage/Gap-Berechnung)
- [x] Jede Änderung erzeugt einen History-Eintrag, No-Op-Updates erzeugen keinen
- [x] `POST /api/analyze` liefert für Techniken mit Portfolio-Abdeckung nicht-leere `portfolio_fit`-Listen
- [x] Regressionstest: `priority_rank`-Reihenfolge identisch mit und ohne Portfolio-Daten
- [x] `pytest` (47 Tests), `npm run test` (8 Tests), `ruff`, `oxlint`, `tsc -b`, `npm run build` grün

**Ergebnis der kritischen Review-Runde nach Implementierung** *(neu, v5)*: Zwei zusätzliche Backend-Endpunkte gegenüber dem ursprünglichen Plan als Lücke gefunden und ergänzt: `GET /api/engagements` gab es schon (Schritt 3), aber **`GET /api/capabilities`** fehlte — ohne ID-tragende Referenzliste konnte das Formular keine Capability-Mehrfachauswahl an `capability_ids` binden (Coverage-Antworten liefern nur Namen). Zwei echte Bugs gefunden und behoben:
- **`create_technology` deduplizierte `capability_ids` nicht** (im Unterschied zu `update_technology`) — doppelte IDs im Payload hätten beim Commit einen `IntegrityError` auf dem zusammengesetzten Primärschlüssel ausgelöst. Fix: `sorted(set(...))` konsistent an beiden Stellen.
- **Keine Validierung nicht existierender `capability_id`s** — hätte einen rohen 500er (FK-Verletzung) statt einer sauberen Antwort erzeugt. Fix: `_validate_capability_ids_exist()` in der API-Schicht, liefert `422` mit den unbekannten IDs.

Fehlende Fehleranzeige bei fehlgeschlagenem Bearbeiten/Deaktivieren im Frontend ergänzt (gleiches Muster wie Schritt 3). Ein scheinbarer Layout-Bug (Topbar erschien mitten im bearbeiteten Formular) stellte sich als reines Playwright-`fullPage`-Screenshot-Artefakt bei `position: sticky` heraus, kein echter Fehler — mit einem normalen Viewport-Screenshot verifiziert. Veralteten Sidebar-Hinweistext aktualisiert.

---

## 10d. Schritt 5 — konkreter Arbeitsauftrag *(neu, v7)*

**Ziel von Schritt 5:** Aus dem kanonischen Analyzer-Ergebnis (inkl. `portfolio_fit` seit Schritt 4) eine geschäftssprachliche Sales-Argumentation generieren — PydanticAI gegen die interne LLM-Plattform, mit den in Abschnitt 7 skizzierten Guardrails.

**Kritisch vorab geklärt, bevor gebaut wurde:**

1. ▶ **Offene Frage 1 (Abschnitt 12) ist weiterhin ungeklärt** — wie die interne LLM-Plattform genau angesprochen wird, ist nicht bekannt. Umgesetzt wird gegen die **wahrscheinlichste Form** (OpenAI-kompatible Chat-Completions-API, via `OpenAIChatModel` + `OpenAIProvider(base_url=…, api_key=…)` aus PydanticAI 2.x — beides über Env-Variablen konfigurierbar, `LLM_PLATFORM_BASE_URL` liegt seit Schritt 1 als Platzhalter bereit). **Das ist eine Annahme, keine bestätigte Integration** — kann erst gegen die echte Plattform verifiziert werden, sobald Frage 1 beantwortet ist. Ohne konfigurierte Basis-URL schlägt die Generierung mit einer klaren Fehlermeldung fehl (kein stiller Fallback auf irgendeinen öffentlichen Anbieter — das wäre ein Verstoß gegen Abschnitt 2).
2. **Async-Umsetzung bewusst ohne neue Infrastruktur.** Abschnitt 7 verlangt "asynchrone Verarbeitung, kein blockierender Request/Response-Zyklus" — das liest sich nach Task-Queue (Celery/arq + Redis + Worker-Container). Umgesetzt wird stattdessen mit FastAPIs eingebauten `BackgroundTasks`: der Endpoint legt sofort eine `sales_briefing`-Zeile mit `status='pending'` an und gibt `202` zurück, die Generierung läuft im selben Prozess weiter, das Frontend pollt den Status. **Bekannte Grenze, nicht verschwiegen:** stürzt der Uvicorn-Worker während der Generierung ab, geht der Task verloren (kein Redo, kein Redis-Persistenz). Für den aktuellen Maßstab (ein Sales-Briefing pro Engagement, kein Hochlastszenario) akzeptabel; eine echte Task-Queue ist der klare Ausbaupfad, sobald Volumen/Laufzeit das rechtfertigen — nicht vorab bauen (YAGNI).
3. **`flagged_for_review` versteckt den Inhalt nicht, markiert ihn nur.** Der Post-Processing-Guard (Abschnitt 7) soll verhindern, dass ein Briefing mit T-Nummer "ungeprüft ausgeliefert" wird — ohne RBAC (Schritt 7 fehlt noch) kann aber niemand technisch von "Sales sieht das nicht" unterschieden werden. Der Inhalt bleibt sichtbar (sonst könnte niemand die "Nachbearbeitung" überhaupt vornehmen), aber unübersehbar als nicht freigegeben markiert. Konsistent mit der bereits mehrfach dokumentierten Lücke "kein Auth vor Schritt 7".
4. **Portfolio-Fit darf in den LLM-Input, das ist kein Widerstand gegen Abschnitt 2a.** "Kein reiner Produktverkauf" verbietet, dass Portfolio-Fit die *Priorisierung* beeinflusst (bleibt unverändert, Schritt 4) — nicht, dass Sales erfährt, welche bereits vorhandene Technologie eine Lücke schließt. Der bestehende System-Prompt-Guardrail ("nutze ausschließlich die im Input gelieferten Fakten") deckt das bereits ab, keine neue Regel nötig.

### 10d.1 Datenmodell-Ergänzung

```
sales_briefing
  id (PK), engagement_id (FK),
  status ENUM('pending','ready','flagged_for_review','failed'),
  model_version, content (JSONB — serialisiertes SalesBriefing-Schema, nullable bis fertig),
  error_message (nullable), generated_at (nullable),
  reviewed_by (nullable, Freitext bis Schritt 7 — analog portfolio_technology_history.changed_by),
  reviewed_at (nullable)
```

Jede Generierung legt eine **neue** Zeile an (append-only, kein Update bestehender Inhalte) — das ist die in Abschnitt 5/7 geforderte Versionierung. `GET .../sales-briefings` liefert die volle Historie, `GET .../sales-briefing` nur die neueste Zeile.

### 10d.2 PydanticAI-Anbindung (`app/services/sales_briefing.py`)

- `SalesBriefing`/`MassnahmeArgumentation` als Pydantic-Schemas exakt wie in Abschnitt 7 skizziert.
- Agent-Konstruktion **parametrisiert über das Model-Objekt**, nicht fest verdrahtet — Produktivbetrieb nutzt `OpenAIChatModel(settings.llm_platform_model_name, provider=OpenAIProvider(base_url=settings.llm_platform_base_url, api_key=settings.llm_platform_api_key))`, Tests nutzen `pydantic_ai.models.test.TestModel()`/`FunctionModel()` — kein Netzwerkzugriff nötig, um die Guardrail-Logik zu verifizieren (bewusster Vorteil von PydanticAIs Design, hier direkt genutzt statt selbst nachzubauen).
- **Input**: `AnalyzerResult.model_dump_json()` — dasselbe kanonische Schema wie Analyst-UI, keine separate Aufbereitung (Abschnitt 2a-Auszahlung, wie schon bei `portfolio_fit`).
- **Post-Processing-Guard**: Regex `T\d{4}(\.\d{3})?` über alle Textfelder des generierten `SalesBriefing` (rekursiv über `executive_summary`, jede `MassnahmeArgumentation`, `naechster_schritt`) — Treffer → `status='flagged_for_review'` statt `'ready'`.

### 10d.3 Endpunkte (`app/api/sales_briefing.py`)

- `POST /api/engagements/{id}/sales-briefing` — legt `pending`-Zeile an, startet `BackgroundTasks`-Job, `202`
- `GET /api/engagements/{id}/sales-briefing` — neueste Zeile (`404` falls noch keine existiert)
- `GET /api/engagements/{id}/sales-briefings` — volle Historie
- `POST /api/sales-briefings/{id}/mark-reviewed` — setzt `reviewed_by` (Freitext) + `reviewed_at`

### 10d.4 Frontend

Neuer Abschnitt in der Engagement-Detailansicht (nicht der `Reports`-Tab — der ist Schritt 7s Export, das hier ist eine live generierte, engagement-gebundene Ansicht): "Sales-Briefing generieren"-Button → Statusanzeige (`pending` gepollt via TanStack Query `refetchInterval`) → Executive Summary, priorisierte Maßnahmen mit Kundennutzen/Risiko/Einwand-Antizipation, "Nächster Schritt". Deutliche Warnung bei `flagged_for_review`. "Als geprüft freigeben"-Button.

### 10d.5 Definition of Done für Schritt 5

- [x] Migration für `sales_briefing` läuft durch
- [x] Generierung mit `TestModel` liefert `status='ready'` und befüllten Content für ein Beispiel-Engagement
- [x] Post-Processing-Guard: ein `FunctionModel`, das absichtlich eine T-Nummer ins Ergebnis schreibt, erzeugt `status='flagged_for_review'`, kein `'ready'`
- [x] Fehlerfall (Agent wirft Exception) landet als `status='failed'` mit `error_message`, kein unbehandelter 500er im Hintergrund-Task
- [x] Ohne konfigurierte `LLM_PLATFORM_BASE_URL` liefert der Endpoint einen klaren Fehler, keinen stillen Fallback
- [x] `mark-reviewed` setzt `reviewed_by`/`reviewed_at`
- [x] Frontend zeigt Pending → Ready/Flagged-Übergang ohne manuelles Neuladen (Polling)
- [x] `pytest`, `npm run test`, `ruff`, `oxlint`, `tsc -b`, `npm run build` weiterhin grün

**Ergebnis der kritischen Review-Runde:**

Implementiert wurde: SQLAlchemy-Modell + Alembic-Migration für `sales_briefing`
(append-only, `SalesBriefingStatus`-Enum); `app/services/analyzer.py` um
`analyze_engagement()` erweitert (Finding→Analyse-Logik aus
`get_engagement_analysis()` extrahiert, damit Sales-Briefing-Service und
Analyse-Endpoint sie gemeinsam nutzen, statt sie zu duplizieren);
`app/services/sales_briefing.py` mit `build_agent()` (test-injizierbares
Model-Argument, produktiv `OpenAIChatModel`/`OpenAIProvider` gegen die
interne Plattform), Post-Processing-Guard (`contains_technique_id()`,
Regex `T\d{4}(\.\d{3})?`) und `generate_sales_briefing()`
(Fehlerbehandlung fängt jede Exception ab, setzt `status='failed'` +
`error_message`, committet immer); vier Endpunkte in
`app/api/sales_briefing.py` (`POST .../sales-briefing` mit
`BackgroundTasks` + eigener DB-Session — die Request-Session ist nach
Response-Versand geschlossen —, `GET .../sales-briefing`,
`GET .../sales-briefings`, `POST /api/sales-briefings/{id}/mark-reviewed`);
Frontend-Sektion `SalesBriefingSection.tsx` in der Engagement-Detailansicht
mit TanStack-Query-Polling (`refetchInterval`, nur solange `status='pending'`).

Bei der Review gefundene und behobene Bugs (echte Funde, keine
kosmetischen Änderungen):
1. **"Als geprüft freigeben"-Button erschien auch bei `status='failed'`.**
   Ursprünglich zeigte die Bedingung `briefing.status !== 'pending'` den
   Freigabe-Button für jeden nicht-pending-Status, also auch für
   fehlgeschlagene Generierungen ohne jeden Inhalt — ein Techniker hätte
   dort fälschlich etwas "freigeben" können, das nie generiert wurde.
   Eingegrenzt auf `status === 'ready' || status === 'flagged_for_review'`.
   Gefunden durch manuellen Playwright-Check im Browser (Screenshot zeigte
   den Button neben der Fehlermeldung), nicht durch die automatisierten
   Tests — kein Test deckte diese UI-Bedingung ab.
2. **Sidebar-Footer verwies noch auf Schritt 4.** Analog zu den vorherigen
   Schritten aktualisiert auf "Schritt 5 · Sales-Briefing" mit Ausblick auf
   Schritt 6 (MITRE-Import/Mitigations-Bootstrap, Auth).

Der Fail-Fast-Pfad ohne konfigurierte `LLM_PLATFORM_BASE_URL` wurde
zusätzlich end-to-end im Browser gegen echtes Backend + Frontend verifiziert
(nicht nur in Tests): Engagement anlegen, Finding hinzufügen,
"Sales-Briefing generieren" klicken → sichtbar `status='failed'` mit der
erwarteten deutschen Fehlermeldung, kein stiller Fallback, keine
unbehandelte Exception im Hintergrund-Task. Die `ready`/`flagged_for_review`-
Übergänge wurden nicht gegen eine echte LLM-Plattform verifiziert (offene
Frage 1 aus Abschnitt 12 bleibt ungeklärt), sondern wie geplant über
PydanticAIs `TestModel`/`FunctionModel` — sowohl in Backend-Unittests
(`test_sales_briefing_service.py`) als auch in Backend-API-Tests
(`test_api_sales_briefing.py`, `build_agent` dort per `monkeypatch`
überschrieben) und in zwei neuen Frontend-Vitest-Tests
(`Engagements.test.tsx`, MSW-Mocks für den vollen Pending→Ready-Zyklus).

64 Backend-Tests + 10 Frontend-Tests grün, `ruff check app/` (Scope wie in
den vorherigen Schritten) und `oxlint`/`tsc -b --noEmit`/`npm run build`
fehlerfrei.

---

## 10e. Schritt 6 — konkreter Arbeitsauftrag *(v8 geplant, v9 umgesetzt)*

**Ziel von Schritt 6:** Admin-gesteuerter MITRE-ATT&CK-Techniken-Import (Abschnitt 6a.2) mit Diff-Ansicht, Versionierung und Rollback, **plus** MITRE-Mitigations-Bootstrap für spezifische Prevent-Mappings (Abschnitt 6a.3) — beides aus demselben STIX-Bundle, ein Import-Vorgang. ✅ Umgesetzt, kritisch geprüft und dokumentiert — Ergebnis der Review-Runde in Abschnitt 10e.5.

**Kritisch vorab geklärt, mit echten Daten verifiziert statt angenommen** (das offizielle STIX-Bundle wurde probeweise geladen und ausgewertet, nicht nur die MITRE-Doku gelesen):

1. ▶ **Netzwerk-Erreichbarkeit unterschiedlich, produktiv zu verifizieren.** In dieser Sandbox ist `raw.githubusercontent.com` erreichbar (das GitHub-Release-Bundle liefert `enterprise-attack.json`, HTTP 200), der öffentliche TAXII-2.1-Server (`attack-taxii.mitre.org`) dagegen von der Sandbox-Netzwerkrichtlinie blockiert (403). Das ist eine Aussage über **diese Entwicklungsumgebung**, nicht zwingend über das Produktivnetz — die Egress-Allowlist (Abschnitt 8) muss dort ohnehin explizit für den Zielhost freigeschaltet werden. Umgesetzt wird der GitHub-Raw-Pfad als primärer Weg (`https://raw.githubusercontent.com/mitre-attack/attack-stix-data/<ref>/enterprise-attack/enterprise-attack.json`), TAXII bleibt als dokumentierte, aber ungetestete Alternative; der manuelle Datei-Upload (6a.2, Punkt 1) funktioniert in jedem Fall unabhängig von der Netzwerkfreigabe.
2. ▶ **Bundle-Größe verlangt bewusste Verarbeitung, kein naives `json.load()` im Request-Zyklus.** Das aktuelle Enterprise-ATT&CK-Bundle ist **~54 MB, 26.086 STIX-Objekte, davon 21.262 Relationships**. Fetch/Parse/Diff-Berechnung laufen deshalb wie die Sales-Briefing-Generierung (Schritt 5) als admin-getriggerter Hintergrund-Job (`BackgroundTasks`, dieselbe dokumentierte Grenze wie in Abschnitt 10d.2 — kein Verlust bei Worker-Absturz, für einen seltenen, admin-gesteuerten Vorgang akzeptabel). Das berechnete Diff-Ergebnis wird serverseitig zwischengespeichert (eigene Tabelle, s. 10e.1), damit der Admin es in Ruhe prüfen kann, ohne dass ein Reload den 54-MB-Parse-Vorgang wiederholt.
3. ▶ **Nur 44 von 268 `course-of-action`-Objekten sind aktuelle Mitigations mit echter M-Nummer.** Der Rest sind revoked/deprecated Altobjekte (z. B. ein Objekt mit `external_id: "T1174"` statt `M-Format` — ein Datenrelikt aus einer älteren ATT&CK-Version). Der Import filtert Mitigations auf `revoked == false`, `x_mitre_deprecated != true` **und** `external_references[].external_id` passend zu `^M\d+$` (source_name `mitre-attack`) — sonst würden veraltete/nicht mehr gültige Mitigations in den Bootstrap einfließen.
4. ▶ **`kill_chain_phases[].phase_name` entspricht exakt der `Tactic.id`-Slug-Konvention dieses Projekts, keine Mapping-Tabelle nötig — mit einer bei der Umsetzung entdeckten Einschränkung.** Verifiziert: STIX liefert z. B. `resource-development`, `privilege-escalation` — dieselben Slugs, die `scripts/seed.py::slugify()` bereits aus den Taktik-Namen erzeugt, für 13 der 14 Taktiken exakt deckungsgleich. Die Taktik-Zuordnung importierter Techniken ist damit größtenteils ein direkter Dictionary-Lookup, keine Heuristik. **Einschränkung (Fund während der Umsetzung, siehe 10e.5 und Abschnitt 12 Frage 10):** `defense-evasion` kommt im aktuellen Bundle als Phase gar nicht mehr vor — MITRE hat diese Taktik in "Stealth" umbenannt und eine neue 15. Taktik "Defense Impairment" ergänzt. Der Diff behandelt nicht zuordenbare Phasen transparent (`unmapped_tactic_phase_techniques`) statt falsch zu klassifizieren oder abzustürzen.
5. **Sub-Technique-Erkennung bestätigt wie in Abschnitt 5 geplant.** `x_mitre_is_subtechnique: true` + eine `subtechnique-of`-Relationship (477 im Bundle) liefern die Eltern-Kind-Beziehung strukturiert — keine Prefix-Parsing-Heuristik auf der ID nötig, wie schon in Abschnitt 5/10a.3 festgelegt.
6. **Vorbedingung aus Abschnitt 6a.3 Punkt 5 wird in Schritt 6 zuerst erledigt:** `resolve_technique()` (`backend/app/services/analyzer.py`) muss von hartkodierten `mapping_source`-Strings auf `mapping.mapping_source.value` umgestellt werden, **bevor** `mitre_derived`-Zeilen entstehen können — sonst würden sie stillschweigend als `"specific"` ausgegeben. Erster Teilschritt der Umsetzung, mit eigenem Regressionstest (bestehendes Verhalten für `specific`/`tactic_default` darf sich nicht ändern).
7. **`mapping_source`-Enum-Erweiterung ist eine echte Migration.** Nativer Postgres-Enum-Typ `mapping_source` bekommt per Alembic `op.execute("ALTER TYPE mapping_source ADD VALUE 'mitre_derived'")` außerhalb einer Transaktion (Alembic unterstützt das über `with op.get_context().autocommit_block()`) einen dritten Wert — kein additiver Tabellen-Change, aber ein PostgreSQL-Spezifikum, das die Migration explizit dokumentieren muss.

### 10e.1 Datenmodell-Ergänzung

```
technique_import_batch
  id (PK), source ENUM('github_raw','taxii','manual_upload'),
  source_ref (z. B. Branch/Tag oder Dateiname), bundle_version (x_mitre_attack_spec_version aus dem Bundle),
  status ENUM('diff_pending','applied','rolled_back'),
  triggered_by (Freitext, analog reviewed_by/changed_by aus Schritt 4/5),
  diff_snapshot (JSONB — die berechnete Diff-Struktur, bis zur Bestätigung/Verwerfung),
  pre_apply_snapshot (JSONB — vollständiger Vorzustand der betroffenen technique/technique_capability_mapping-Zeilen, für Rollback),
  created_at, applied_at (nullable), rolled_back_at (nullable)
```

`technique` bekommt zwei neue Spalten: `deprecated: bool` (default `false` — Soft-Delete-Prinzip aus Abschnitt 5, keine Techniken werden hart gelöscht, damit historische Findings/Reports nicht verwaisen) und `stix_id: str | None` (die interne STIX-UUID, getrennt von der öffentlichen T-Nummer, nötig um Relationships beim nächsten Import wiederzufinden, ohne dass sich `technique.id` ändert).

`MappingSource`-Enum bekommt den dritten Wert `MITRE_DERIVED = "mitre_derived"` (Migration wie oben, Punkt 7).

Rollback ist **einstufig** (nur der zuletzt angewendete, noch nicht durch einen neueren Import überschriebene Batch lässt sich zurückrollen) — kein voller Versionsbaum, das wäre YAGNI für einen Vorgang, der laut Abschnitt 12 (offene Frage 6) vierteljährlich stattfindet.

### 10e.2 STIX-Parsing & Diff-Berechnung (`app/services/mitre_import.py`)

- Bundle-Fetch (GitHub-Raw, mit `manual_upload` als Alternative über einen Datei-Upload-Endpoint) → Parsing mit `ijson` oder blockweisem `json.load` (Entscheidung beim Bauen anhand eines Speicherverbrauchstests; 54 MB als vollständiger Python-Dict ist vermutlich noch vertretbar, muss aber gegen den Ziel-Container-Speicher geprüft werden, nicht angenommen).
- Techniken: `attack-pattern`-Objekte mit `revoked=false`, `x_mitre_deprecated` nicht `true` → neue/geänderte/als-deprecated-erkannte Einträge relativ zum aktuellen `technique`-Bestand (Abgleich über `stix_id`, Fallback über die T-Nummer für den allerersten Import, bei dem `stix_id` noch nicht gesetzt ist).
- Mitigations: gefilterte `course-of-action`-Objekte (10e Punkt 3) + `mitigates`-Relationships → Kandidaten für `mitre_derived`-Mappings, über den kuratierten Crosswalk `MITIGATION_CAPABILITY_CROSSWALK` (Python-Dict analog `ALL_CAPABILITIES` in `seed_data.py`, Abschnitt 6a.3 Punkt 7) auf Capabilities abgebildet. `impact`/`effort` werden vom `tactic_default_mapping` derselben Taktik übernommen (Abschnitt 6a.3 Punkt 2).
- **Nie überschrieben werden bestehende `mapping_source='specific'`-Zeilen** (Abschnitt 6a.2 Punkt 3, 6a.3 Punkt 6) — der Diff zeigt einen Konflikt an, übernimmt ihn aber nicht automatisch.
- Ergebnis ist eine strukturierte Diff-Antwort (neue Techniken, geänderte Namen/Taktiken, neu als deprecated erkannte Techniken, neue `mitre_derived`-Mapping-Kandidaten, übersprungene Mitigations ohne Crosswalk-Treffer, Konflikte mit bestehenden `specific`-Mappings) — nicht committet, sondern in `technique_import_batch.diff_snapshot` zwischengespeichert.

### 10e.3 Endpunkte (`app/api/mitre_import.py`, Präfix `/api/admin/mitre-import`)

- `POST /fetch` — stößt Fetch+Parse+Diff als Hintergrund-Job an, legt `technique_import_batch` mit `status='diff_pending'` an, `202`
- `POST /upload` — wie `/fetch`, aber mit hochgeladener Datei statt GitHub-Raw-Fetch (`multipart/form-data`)
- `GET /batches/{id}` — Batch-Status + Diff (sobald `diff_pending` fertig berechnet ist)
- `POST /batches/{id}/apply` — Admin übergibt, welche Diff-Teile übernommen werden (z. B. alle Techniken, aber nur ausgewählte Mitigation-Kandidaten); schreibt `pre_apply_snapshot`, wendet an, setzt `status='applied'`
- `POST /batches/{id}/rollback` — nur solange kein neuerer Batch `applied` ist; stellt `pre_apply_snapshot` wieder her, setzt `status='rolled_back'`
- `GET /batches` — Historie aller Imports

Kein Auth-Gate (weiterhin die aus Schritt 1 bekannte, wiederholt dokumentierte Lücke "kein Auth vor Schritt 7") — die Endpunkte sind technisch für jeden erreichbar, der das Backend erreicht, genau wie alle bisherigen.

### 10e.4 Frontend

Neuer Admin-Bereich (eigene Route, nicht mit dem bestehenden Portfolio-Tab vermischt, Abschnitt 6a.2 letzter Satz): Import starten → Fortschritt (Polling wie Sales-Briefing) → Diff-Ansicht mit Kategorien (neu/geändert/deprecated/Mitigation-Kandidaten/Konflikte), Checkboxen zur selektiven Übernahme → Bestätigen → Ergebnis. Eigene Unterseite "Import-Historie" mit Rollback-Button auf dem jeweils letzten Batch.

### 10e.5 Definition of Done für Schritt 6

- [x] `resolve_technique()` liest `mapping_source` aus der DB-Zeile statt hartkodierter Strings (Regressionstest für bestehendes `specific`/`tactic_default`-Verhalten)
- [x] Migration: `technique.deprecated`/`technique.stix_id`, `technique_import_batch`-Tabelle, `mapping_source`-Enum-Erweiterung um `mitre_derived`
- [x] Fetch gegen ein echtes (oder als Fixture eingefrorenes) STIX-Bundle liefert einen korrekten Diff für einen bekannten Ausschnitt (z. B. eine gezielt veränderte Kopie mit einer neuen/umbenannten/deprecated Technik)
- [x] Bestehende `specific`-Mappings werden von einem Import nie überschrieben, Konflikt wird im Diff sichtbar
- [x] Mitigation-Bootstrap: gefilterte Mitigations (M-Nummer, nicht revoked/deprecated) mit Crosswalk-Treffer erzeugen `mitre_derived`-Kandidaten mit von der Taktik geerbtem impact/effort
- [x] `apply` ist selektiv (Admin kann Teilmengen übernehmen), schreibt `pre_apply_snapshot`
- [x] `rollback` stellt den Vorzustand korrekt wieder her, nur für den jeweils letzten Batch möglich
- [x] Frontend zeigt Diff-Ansicht + selektive Übernahme + Import-Historie mit Rollback
- [x] `pytest`, `npm run test`, `ruff`, `oxlint`, `tsc -b`, `npm run build` weiterhin grün

**Ergebnis der kritischen Review-Runde:**

Implementiert: `resolve_technique()`-Bugfix samt gezieltem Regressionstest
(legt eine `technique_capability_mapping`-Zeile mit einem anderen Wert als
`specific` an — mit dem alten hartkodierten Code wäre das trotzdem als
`"specific"` ausgegeben worden); Migration für `technique.deprecated`
(Soft-Delete, nie Hard-Delete), `technique.stix_id` (unique), die neue
`technique_import_batch`-Tabelle und die native-Enum-Erweiterung um
`mitre_derived` (per `ALTER TYPE ... ADD VALUE` in einem
`autocommit_block()`, da Postgres das außerhalb einer Transaktion verlangt);
der kuratierte `MITIGATION_CROSSWALK` (30 von 44 aktuellen M-Nummern
gegen echte, in dieser Session aus dem offiziellen STIX-Bundle gezogene
Mitigation-Namen abgeglichen, inkl. deutscher Control-Label, die bewusst
bestehende KB-Controls wiederverwenden statt englische Duplikate
anzulegen); `app/services/mitre_import.py` mit reiner
`parse_bundle()`-Funktion, DB-abhängiger `compute_diff()`,
`apply_batch()`/`rollback_batch()` mit vollständigem Vorzustand-Snapshot;
vier Endpunkte inkl. Datei-Upload und GitHub-Fetch via `BackgroundTasks`;
Frontend-Admin-Bereich mit Diff-Ansicht, Checkbox-Auswahl,
Import-Historie und Rollback-Button (nur auf dem jeweils letzten
angewendeten Batch).

**Verifiziert gegen echte MITRE-Daten, nicht nur Annahmen:** Das
offizielle STIX-Bundle wurde in dieser Session mehrfach real geladen
(~54 MB, aktuelle Version 19.2) und `parse_bundle()`/`compute_diff()`
testweise dagegen ausgeführt (1,6 s Parse-Zeit, <0,2 s Diff-Berechnung
gegen die Seed-DB) — nicht nur gegen das kleine Test-Fixture. Dabei
gefundene, konkrete Fakten statt Annahmen: 858 Techniken, 44 aktuelle
Mitigations, 477 aufgelöste Sub-Technique-Elternbeziehungen, 366
Mitigation-Kandidaten und 10 Konflikte mit bestehenden `specific`-Mappings
auf dem aktuellen Seed-Datensatz.

**Bei der Review gefundene und behobene Bugs (echte Funde, nicht nur
kosmetisch):**
1. **Zweites Vorkommen desselben hartkodierten-`mapping_source`-Bugs in
   `app/services/catalog.py`.** Der ursprüngliche Fund (Abschnitt 6a.3
   Punkt 5) betraf nur `resolve_technique()` — beim Bauen von Schritt 6
   fiel auf, dass `list_techniques()` (der Techniken-Katalog-Endpunkt,
   `GET /api/techniques`) denselben Fehler unabhängig enthielt: es wurde
   nur geprüft, *ob* eine Zeile in `technique_capability_mapping`
   existiert, nicht welchen `mapping_source`-Wert sie trägt — jede
   `mitre_derived`-Zeile wäre im Katalog fälschlich als `"specific"`
   angezeigt worden. Mit Regressionstest behoben (liest jetzt den
   tatsächlichen Wert), inklusive Fallback über `parent_technique_id` für
   Sub-Techniken wie zuvor.
2. **`technique.deprecated` wäre ein Flag ohne Wirkung geblieben.** Ein
   neues Feld, das nirgends gelesen wird, ist toter Code — der
   Techniken-Katalog blendet deprecated Techniken jetzt standardmäßig aus
   (`include_deprecated=true` zeigt sie zusätzlich), analog zum
   `active`-Flag bei `portfolio_technology` (Abschnitt 10c). Mit
   Regressionstest.
3. **`stix_id` ohne Unique-Constraint hätte mehrdeutige Diffs erlaubt.**
   Ursprünglich nur `nullable=True` ohne Eindeutigkeit — zwei
   `technique`-Zeilen hätten (bei einem Datenfehler) auf dieselbe
   STIX-UUID zeigen können, was die stix_id-basierte Zuordnung beim
   nächsten Import mehrdeutig gemacht hätte. Vor dem ersten produktiven
   Einsatz der Migration ergänzt (`UNIQUE`-Constraint), inklusive eines
   vollständigen Downgrade/Upgrade-Testlaufs, der dabei einen echten
   Alembic-Bug aufdeckte und behob (siehe Punkt 4).
4. **Alembic-Downgrade ließ verwaiste Postgres-ENUM-Typen zurück.** Der
   autogenerierte `downgrade()` droppte die `technique_import_batch`-
   Tabelle, aber nicht die für ihre Spalten angelegten nativen ENUM-Typen
   (`import_source`, `import_batch_status`) — ein erneutes `upgrade()`
   scheiterte dadurch mit "type already exists". In dieser Session so
   reproduziert (Downgrade→Upgrade-Testlauf) und behoben (`sa.Enum(...).drop()`
   ergänzt); ein zweiter Downgrade→Upgrade-Zyklus bestätigt die Reparatur.

**Offener Punkt, bewusst nicht in Schritt 6 gelöst, sondern dokumentiert:**
Das offizielle STIX-Bundle zeigt, dass MITRE die Taktik "Defense Evasion"
(TA0005) inzwischen in **"Stealth"** umbenannt und eine **neue 15. Taktik
"Defense Impairment" (TA0112)** eingeführt hat — dieses Projekt bildet
weiterhin die ursprünglichen 14 Taktiken ab. Ein Import gegen das aktuelle
Bundle würde deshalb ca. 204 von 858 Techniken (~24 %) als
`unmapped_tactic_phase_techniques` melden, statt sie einer Taktik
zuzuordnen — das ist kein Absturz und kein stiller Fehler (die Diff-Logik
fängt das transparent ab und zeigt es dem Admin an), aber ein spürbarer
Anteil. Eine Auflösung (Taktik umbenennen vs. 15. Taktik ergänzen) berührt
mehrere Stellen außerhalb von Schritt 6 (Frontend-Taktik-Dropdown,
Dokumentensprache "14 Taktiken" an mehreren Stellen) und wird deshalb
bewusst nicht hier mitentschieden, sondern als neue offene Frage in
Abschnitt 12 aufgenommen.

85 Backend-Tests + 13 Frontend-Tests grün (inkl. 20 neuer Backend- und 3
neuer Frontend-Tests für Schritt 6), `ruff check app/ tests/ scripts/`,
`oxlint`, `tsc -b --noEmit` und `npm run build` fehlerfrei. Der volle
Import→Diff→Übernahme→Rollback-Zyklus wurde zusätzlich end-to-end im
Browser gegen echtes Backend + Frontend verifiziert (Datei-Upload des
Test-Fixtures, Diff-Ansicht, selektive Übernahme, Bestätigung im
Techniken-Katalog inkl. korrektem Sub-Technique-Fallback, Rollback,
erneute Prüfung im Katalog).

---

## 11. Ausblick Schritt 7+ (grob, nicht Teil des aktuellen Auftrags)

- **Schritt 2:** ✅ siehe Abschnitt 10a (konkretisiert)
- **Schritt 3:** ✅ siehe Abschnitt 10b (konkretisiert)
- **Schritt 4:** ✅ siehe Abschnitt 10c (konkretisiert)
- **Schritt 5:** ✅ siehe Abschnitt 10d (konkretisiert)
- **Schritt 6:** ✅ siehe Abschnitt 10e (konkretisiert und umgesetzt)
- **Schritt 7:** Reporting/Export, Rollenmodell/Auth-Anbindung, Audit-Log-UI

---

## 12. Offene Fragen, die vor oder während Schritt 1 geklärt werden sollten

1. Wie wird die interne LLM-Plattform angesprochen — OpenAI-kompatible API, proprietäres SDK, oder REST mit eigenem Auth-Schema? (Bestimmt die PydanticAI-Model-Provider-Konfiguration in Schritt 5.)
2. Gibt es unternehmensweite Standards für Python-Version, Linting (ruff/black), CI/CD-Pipeline und Container-Registry, an die sich Claude Code halten soll?
3. Welcher Auth-Provider ist im Datacenter Standard (Keycloak, Azure AD/Entra on-prem, LDAP, etwas anderes)?
4. Soll PostgreSQL als eigener Container mitgeliefert werden oder existiert bereits eine zentrale DB-Instanz, an die sich die Anwendung anbinden soll?
5. Gibt es bereits ein internes Basis-Image / einen Style-Guide für Docker-Images, den Claude Code verwenden soll, statt öffentliche Docker-Hub-Images direkt zu referenzieren?
6. ▶ *(v3, teilweise beantwortet)* MITRE selbst veröffentlicht ca. zweimal jährlich (Frühjahr/Herbst) — ein quartalsweiser "Prüfen"-Klick durch einen Admin deckt das komfortabel ab. Weiterhin offen: reicht ein einzelner Admin zur Freigabe, oder braucht es ein Vier-Augen-Prinzip, bevor ein Import produktiv übernommen wird?
7. ▶ *(neu, v2)* Welches selbst gehostete Logging-/Monitoring-Setup soll genutzt werden (z. B. Loki/Grafana), da externe SaaS-Fehler-Tracking-Dienste laut Abschnitt 2 ausgeschlossen sind?
8. ▶ *(neu, v2)* Gibt es eine Datenretention-/Löschpflicht für Engagement-Daten nach Projektabschluss (Kundenschwachstellen-Daten)?
9. ▶ *(neu, v2)* Genaue Gewichtungsformel für "Kettenabdeckung" in der Priorisierung (Abschnitt 2a/11): reine Zählung betroffener Techniken, oder gewichtet nach Position in der Kette (z. B. früher Breakpoint wertvoller)? Sollte vor Schritt 2 grob festgelegt werden, muss aber nicht in Schritt 1 final sein.
10. ▶ *(neu, v9, Fund aus Schritt 6)* MITRE hat die Taktik "Defense Evasion" (TA0005) im aktuellen STIX-Bundle in **"Stealth"** umbenannt und eine **neue 15. Taktik "Defense Impairment" (TA0112)** eingeführt — dieses Projekt bildet weiterhin die ursprünglichen 14 Taktiken ab (Abschnitt 10e.5). Ein Import gegen das aktuelle Bundle würde deshalb ca. 24 % der Techniken als nicht zuordenbar melden statt sie zu klassifizieren. Zu entscheiden, bevor ein produktiver MITRE-Import gegen die aktuelle ATT&CK-Version durchgeführt wird: Taktik "defense-evasion" umbenennen (Auswirkung auf bestehende `technique.tactic_id`-Werte, `tactic_default_mapping`, Frontend-Taktik-Dropdown) oder "Defense Impairment" als 15. Taktik ergänzen (Auswirkung auf jede Stelle, die "14 Taktiken" annimmt) — oder beides.

Diese Fragen blockieren Schritt 1 nicht zwingend (sinnvolle Defaults sind oben angegeben), sollten aber vor Schritt 5 (LLM-Anbindung) und vor einem produktiven Deployment final geklärt sein. Fragen 2 und 5 sollten idealerweise **vor** dem ersten Commit geklärt sein, da sie sich sonst flächendeckend (Formatierung, Dockerfiles) niederschlagen und später aufwändig nachgezogen werden müssten. Frage 10 sollte vor dem ersten produktiven MITRE-Import (Schritt 6) geklärt sein, blockiert aber Schritt 6 selbst nicht (die Diff-Ansicht behandelt unmappbare Techniken bereits transparent, statt sie stillschweigend falsch zuzuordnen).
