from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://breakpoint:breakpoint@localhost:5432/breakpoint"

    # Vorbereitet für Schritt 5 (PydanticAI-Anbindung), in Schritt 1 noch ungenutzt.
    llm_platform_base_url: str | None = None


settings = Settings()
