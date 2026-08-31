from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://breakpoint:breakpoint@localhost:5432/breakpoint"

    # Interne LLM-Plattform (Abschnitt 7/10d) — Annahme: OpenAI-kompatible API.
    # Offene Frage 1 (Abschnitt 12) ist ungeklärt; ohne base_url schlägt die
    # Sales-Briefing-Generierung mit einer klaren Fehlermeldung fehl statt
    # still auf einen externen Anbieter auszuweichen (Abschnitt 2).
    llm_platform_base_url: str | None = None
    llm_platform_api_key: str | None = None
    llm_platform_model_name: str = "gpt-4o-mini"

    # Frontend läuft auf einer anderen Origin (Vite-Dev-Server) als das
    # Backend — bewusst eine enge Allowlist statt Wildcard "*" (Abschnitt 8).
    cors_allow_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]


settings = Settings()
