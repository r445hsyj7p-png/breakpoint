from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://breakpoint:breakpoint@localhost:5432/breakpoint"

    # Vorbereitet für Schritt 5 (PydanticAI-Anbindung), in Schritt 1 noch ungenutzt.
    llm_platform_base_url: str | None = None

    # Frontend läuft auf einer anderen Origin (Vite-Dev-Server) als das
    # Backend — bewusst eine enge Allowlist statt Wildcard "*" (Abschnitt 8).
    cors_allow_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]


settings = Settings()
