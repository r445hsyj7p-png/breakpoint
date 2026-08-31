from app.models import Engagement, Finding, SalesBriefingStatus
from app.models import SalesBriefing as SalesBriefingRow
from app.schemas.sales_briefing import MassnahmeArgumentation
from app.schemas.sales_briefing import SalesBriefing as SalesBriefingContent
from app.services.sales_briefing import (
    LlmPlatformNotConfiguredError,
    build_agent,
    contains_technique_id,
    generate_sales_briefing,
)
from scripts.seed import run as run_seed


def _make_engagement_with_finding(db_session) -> int:
    engagement = Engagement(name="Test Engagement")
    db_session.add(engagement)
    db_session.commit()
    db_session.refresh(engagement)
    db_session.add(Finding(engagement_id=engagement.id, technique_id="T1078"))
    db_session.commit()
    return engagement.id


def _make_pending_row(db_session, engagement_id: int) -> int:
    row = SalesBriefingRow(engagement_id=engagement_id, status=SalesBriefingStatus.PENDING)
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row.id


def test_contains_technique_id_detects_t_number_anywhere_in_content():
    briefing = SalesBriefingContent(
        executive_summary="Enthält versehentlich T1078 im Text.",
        top_massnahmen=[],
        naechster_schritt="Weiter.",
    )
    assert contains_technique_id(briefing) is True


def test_contains_technique_id_false_for_clean_content():
    briefing = SalesBriefingContent(
        executive_summary="Saubere, geschäftssprachliche Zusammenfassung ohne Technikdetails.",
        top_massnahmen=[
            MassnahmeArgumentation(
                massnahme="MFA einführen",
                kunden_nutzen="Reduziert das Risiko von Kontoübernahmen erheblich.",
                risiko_ohne_massnahme="Angreifer können gestohlene Zugangsdaten direkt verwenden.",
                einwand_antizipation="Einwand: Aufwand für Nutzer. Gegenargument: moderne MFA ist kaum spürbar.",
            )
        ],
        naechster_schritt="Workshop zur Einführung planen.",
    )
    assert contains_technique_id(briefing) is False


def test_build_agent_raises_without_configured_base_url(monkeypatch):
    monkeypatch.setattr("app.services.sales_briefing.settings.llm_platform_base_url", None)
    try:
        build_agent()
        raise AssertionError("sollte LlmPlatformNotConfiguredError auslösen")
    except LlmPlatformNotConfiguredError:
        pass


def test_generate_sales_briefing_ready_with_test_model(db_session):
    from pydantic_ai.models.test import TestModel

    run_seed()
    engagement_id = _make_engagement_with_finding(db_session)
    briefing_id = _make_pending_row(db_session, engagement_id)

    generate_sales_briefing(db_session, engagement_id, briefing_id, model=TestModel())

    row = db_session.get(SalesBriefingRow, briefing_id)
    assert row.status == SalesBriefingStatus.READY
    assert row.content is not None
    assert row.model_version is not None
    assert row.generated_at is not None
    assert row.error_message is None


def test_generate_sales_briefing_flagged_when_model_leaks_technique_id(db_session):
    from pydantic_ai.messages import ModelResponse, TextPart
    from pydantic_ai.models.function import FunctionModel

    def leaky_response(messages, info):
        content = SalesBriefingContent(
            executive_summary="Zusammenfassung, die versehentlich T1078 nennt.",
            top_massnahmen=[],
            naechster_schritt="Weiter.",
        )
        return ModelResponse(parts=[TextPart(content.model_dump_json())])

    run_seed()
    engagement_id = _make_engagement_with_finding(db_session)
    briefing_id = _make_pending_row(db_session, engagement_id)

    generate_sales_briefing(db_session, engagement_id, briefing_id, model=FunctionModel(leaky_response))

    row = db_session.get(SalesBriefingRow, briefing_id)
    assert row.status == SalesBriefingStatus.FLAGGED_FOR_REVIEW
    assert row.content is not None


def test_generate_sales_briefing_failed_when_platform_not_configured(db_session, monkeypatch):
    monkeypatch.setattr("app.services.sales_briefing.settings.llm_platform_base_url", None)
    run_seed()
    engagement_id = _make_engagement_with_finding(db_session)
    briefing_id = _make_pending_row(db_session, engagement_id)

    generate_sales_briefing(db_session, engagement_id, briefing_id)

    row = db_session.get(SalesBriefingRow, briefing_id)
    assert row.status == SalesBriefingStatus.FAILED
    assert row.error_message is not None
    assert "LLM_PLATFORM_BASE_URL" in row.error_message


def test_generate_sales_briefing_failed_on_agent_exception(db_session):
    from pydantic_ai.models.function import FunctionModel

    def raising_response(messages, info):
        raise ValueError("Simulierter Plattformfehler")

    run_seed()
    engagement_id = _make_engagement_with_finding(db_session)
    briefing_id = _make_pending_row(db_session, engagement_id)

    generate_sales_briefing(db_session, engagement_id, briefing_id, model=FunctionModel(raising_response))

    row = db_session.get(SalesBriefingRow, briefing_id)
    assert row.status == SalesBriefingStatus.FAILED
    assert "Simulierter Plattformfehler" in row.error_message


def test_generate_sales_briefing_missing_row_is_noop(db_session):
    run_seed()
    engagement_id = _make_engagement_with_finding(db_session)
    # Sollte nicht crashen, auch wenn die briefing_id nicht existiert.
    generate_sales_briefing(db_session, engagement_id, 999999)
