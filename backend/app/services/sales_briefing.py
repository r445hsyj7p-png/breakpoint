"""PydanticAI-Anbindung für die Sales-Briefing-Generierung
(docs/projektauftrag.md Abschnitt 7/10d.2).

Wichtig: Es gibt bewusst zwei Klassen namens "SalesBriefing" — das
SQLAlchemy-Modell (app.models.sales_briefing.SalesBriefing, die Zeile in der
Datenbank) und das Pydantic-Ausgabeschema für den LLM-Agenten
(app.schemas.sales_briefing.SalesBriefing, der generierte Inhalt). Um Import-
Kollisionen zu vermeiden, wird hier konsequent aliasiert."""

import logging
import re
from datetime import UTC, datetime

from pydantic_ai import Agent
from pydantic_ai.models import Model
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import SalesBriefing as SalesBriefingRow
from app.models import SalesBriefingStatus
from app.schemas.sales_briefing import SalesBriefing as SalesBriefingContent
from app.services.analyzer import analyze_engagement

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Du übersetzt technische Security-Findings in Geschäftsargumentation. "
    "Nutze ausschließlich die im Input gelieferten Fakten. Erfinde keine "
    "zusätzlichen Risiken, Zahlen oder Produktnamen. Nenne niemals ATT&CK-"
    "Technik-IDs oder rohe T-Nummern."
)

# Post-Processing-Guard (Abschnitt 7): T-Nummern-Muster wie z.B. "T1059" oder
# "T1059.001" — reines Vertrauen in den System-Prompt reicht bei einer
# Sales-Rolle ohne T-Nummern-Berechtigung nicht aus.
TECHNIQUE_ID_PATTERN = re.compile(r"T\d{4}(\.\d{3})?")


class LlmPlatformNotConfiguredError(RuntimeError):
    """Wird ausgelöst, wenn LLM_PLATFORM_BASE_URL nicht gesetzt ist — bewusst
    kein stiller Fallback auf einen externen Anbieter (Abschnitt 2/10d)."""


def build_agent(model: Model | str | None = None) -> Agent[None, SalesBriefingContent]:
    """Baut den PydanticAI-Agenten. Im Produktivbetrieb wird `model` nicht
    übergeben und stattdessen aus den Settings gegen die interne, OpenAI-
    kompatible LLM-Plattform konstruiert; Tests übergeben `TestModel()`/
    `FunctionModel()`, um ohne Netzwerkzugriff zu laufen (Abschnitt 10d.2)."""
    if model is None:
        if not settings.llm_platform_base_url:
            raise LlmPlatformNotConfiguredError(
                "LLM_PLATFORM_BASE_URL ist nicht konfiguriert — Sales-Briefing-"
                "Generierung kann nicht ausgeführt werden. Kein Fallback auf "
                "einen externen Anbieter (Abschnitt 2)."
            )
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        model = OpenAIChatModel(
            settings.llm_platform_model_name,
            provider=OpenAIProvider(
                base_url=settings.llm_platform_base_url,
                api_key=settings.llm_platform_api_key,
            ),
        )

    return Agent(model, output_type=SalesBriefingContent, system_prompt=SYSTEM_PROMPT)


def contains_technique_id(briefing: SalesBriefingContent) -> bool:
    """Rekursiver Scan über alle Textfelder des generierten Briefings auf
    ATT&CK-T-Nummern-Muster (Abschnitt 7 Post-Processing-Guard)."""
    return bool(TECHNIQUE_ID_PATTERN.search(briefing.model_dump_json()))


def generate_sales_briefing(
    db: Session,
    engagement_id: int,
    briefing_id: int,
    model: Model | str | None = None,
) -> None:
    """Läuft als BackgroundTasks-Job (Abschnitt 10d.2): lädt das
    AnalyzerResult, ruft den Agenten auf und schreibt das Ergebnis in die
    vorab mit status='pending' angelegte sales_briefing-Zeile. Fehler landen
    als status='failed' mit error_message statt als unbehandelter 500er im
    Hintergrund-Task."""
    row = db.get(SalesBriefingRow, briefing_id)
    if row is None:
        logger.error("sales_briefing-Zeile %s nicht gefunden, Job abgebrochen", briefing_id)
        return

    try:
        agent = build_agent(model)
        analyzer_result = analyze_engagement(db, engagement_id)
        prompt = f"Analyzer-Ergebnis (strukturiert, geprüft): {analyzer_result.model_dump_json()}"
        result = agent.run_sync(prompt)
        content = result.output

        row.content = content.model_dump(mode="json")
        row.model_version = settings.llm_platform_model_name
        row.generated_at = datetime.now(UTC)
        row.status = (
            SalesBriefingStatus.FLAGGED_FOR_REVIEW
            if contains_technique_id(content)
            else SalesBriefingStatus.READY
        )
    except Exception as exc:
        logger.exception("Sales-Briefing-Generierung fehlgeschlagen (engagement_id=%s)", engagement_id)
        row.status = SalesBriefingStatus.FAILED
        row.error_message = str(exc)

    db.commit()
