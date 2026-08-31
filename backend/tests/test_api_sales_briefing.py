from fastapi.testclient import TestClient

from app.main import app
from scripts.seed import run as run_seed


def _create_engagement_with_finding(client: TestClient) -> int:
    engagement_id = client.post("/api/engagements", json={"name": "Sales-Test"}).json()["id"]
    client.post(f"/api/engagements/{engagement_id}/findings", json={"codes": "T1078"})
    return engagement_id


def _patch_build_agent_to_test_model(monkeypatch) -> None:
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel

    from app.schemas.sales_briefing import SalesBriefing as SalesBriefingContent
    from app.services.sales_briefing import SYSTEM_PROMPT

    def fake_build_agent(model=None):
        return Agent(TestModel(), output_type=SalesBriefingContent, system_prompt=SYSTEM_PROMPT)

    monkeypatch.setattr("app.services.sales_briefing.build_agent", fake_build_agent)


def _patch_build_agent_to_leaky_model(monkeypatch) -> None:
    from pydantic_ai import Agent
    from pydantic_ai.messages import ModelResponse, TextPart
    from pydantic_ai.models.function import FunctionModel

    from app.schemas.sales_briefing import SalesBriefing as SalesBriefingContent
    from app.services.sales_briefing import SYSTEM_PROMPT

    def leaky_response(messages, info):
        content = SalesBriefingContent(
            executive_summary="Enthält versehentlich T1078.",
            top_massnahmen=[],
            naechster_schritt="Weiter.",
        )
        return ModelResponse(parts=[TextPart(content.model_dump_json())])

    def fake_build_agent(model=None):
        return Agent(FunctionModel(leaky_response), output_type=SalesBriefingContent, system_prompt=SYSTEM_PROMPT)

    monkeypatch.setattr("app.services.sales_briefing.build_agent", fake_build_agent)


def test_post_sales_briefing_unknown_engagement_returns_404(db_session):
    run_seed()
    client = TestClient(app)
    response = client.post("/api/engagements/999999/sales-briefing")
    assert response.status_code == 404


def test_get_latest_sales_briefing_404_when_none_exists(db_session):
    run_seed()
    client = TestClient(app)
    engagement_id = _create_engagement_with_finding(client)
    response = client.get(f"/api/engagements/{engagement_id}/sales-briefing")
    assert response.status_code == 404


def test_sales_briefing_lifecycle_reaches_ready(db_session, monkeypatch):
    _patch_build_agent_to_test_model(monkeypatch)
    run_seed()
    client = TestClient(app)
    engagement_id = _create_engagement_with_finding(client)

    post_resp = client.post(f"/api/engagements/{engagement_id}/sales-briefing")
    assert post_resp.status_code == 202
    assert post_resp.json()["status"] == "pending"

    get_resp = client.get(f"/api/engagements/{engagement_id}/sales-briefing")
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["status"] == "ready"
    assert body["content"]["executive_summary"]
    assert body["model_version"]
    assert body["generated_at"] is not None


def test_sales_briefing_flagged_for_review_when_technique_id_leaks(db_session, monkeypatch):
    _patch_build_agent_to_leaky_model(monkeypatch)
    run_seed()
    client = TestClient(app)
    engagement_id = _create_engagement_with_finding(client)

    client.post(f"/api/engagements/{engagement_id}/sales-briefing")
    body = client.get(f"/api/engagements/{engagement_id}/sales-briefing").json()
    assert body["status"] == "flagged_for_review"


def test_sales_briefing_failed_without_configured_llm_platform(db_session, monkeypatch):
    monkeypatch.setattr("app.services.sales_briefing.settings.llm_platform_base_url", None)
    run_seed()
    client = TestClient(app)
    engagement_id = _create_engagement_with_finding(client)

    client.post(f"/api/engagements/{engagement_id}/sales-briefing")
    body = client.get(f"/api/engagements/{engagement_id}/sales-briefing").json()
    assert body["status"] == "failed"
    assert "LLM_PLATFORM_BASE_URL" in body["error_message"]


def test_sales_briefing_history_is_append_only(db_session, monkeypatch):
    _patch_build_agent_to_test_model(monkeypatch)
    run_seed()
    client = TestClient(app)
    engagement_id = _create_engagement_with_finding(client)

    client.post(f"/api/engagements/{engagement_id}/sales-briefing")
    client.post(f"/api/engagements/{engagement_id}/sales-briefing")

    history = client.get(f"/api/engagements/{engagement_id}/sales-briefings").json()
    assert len(history) == 2
    # neueste zuerst
    assert history[0]["id"] > history[1]["id"]


def test_list_sales_briefings_unknown_engagement_returns_404(db_session):
    run_seed()
    client = TestClient(app)
    response = client.get("/api/engagements/999999/sales-briefings")
    assert response.status_code == 404


def test_mark_reviewed_sets_reviewer_and_timestamp(db_session, monkeypatch):
    _patch_build_agent_to_test_model(monkeypatch)
    run_seed()
    client = TestClient(app)
    engagement_id = _create_engagement_with_finding(client)
    client.post(f"/api/engagements/{engagement_id}/sales-briefing")
    briefing_id = client.get(f"/api/engagements/{engagement_id}/sales-briefing").json()["id"]

    response = client.post(
        f"/api/sales-briefings/{briefing_id}/mark-reviewed", json={"reviewed_by": "Alex"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["reviewed_by"] == "Alex"
    assert body["reviewed_at"] is not None


def test_mark_reviewed_unknown_id_returns_404(db_session):
    run_seed()
    client = TestClient(app)
    response = client.post("/api/sales-briefings/999999/mark-reviewed", json={})
    assert response.status_code == 404
