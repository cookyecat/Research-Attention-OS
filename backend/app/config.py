from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RAOS_", extra="ignore")

    database_url: str = "sqlite:///./raos.db"
    auto_create_tables: bool = True
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    max_upload_bytes: int = 20 * 1024 * 1024
    url_fetch_timeout_seconds: float = 15.0
    scheduler_version: str = "raos-scheduler-0.1.0"
    fingerprint_version: str = "fp-v1"
    cors_origins: str = "http://localhost:3000"


settings = Settings()
