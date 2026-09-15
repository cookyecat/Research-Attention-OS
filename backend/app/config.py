from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RAOS_", extra="ignore")

    database_url: str = "sqlite:///./raos.db"
    auto_create_tables: bool = True
    cognitive_provider: str = "rule"
    # legacy | research-aligned-v1. Dogfood sets research-aligned-v1 explicitly.
    cognitive_contract: str = "legacy"
    # disabled | dsp-v1. No-Delta D/S/P situational-awareness branch.
    no_delta_awareness_contract: str = "disabled"
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_input_cost_per_1m: float | None = None
    llm_output_cost_per_1m: float | None = None
    embedding_base_url: str | None = None
    embedding_api_key: str | None = None
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int | None = None
    max_upload_bytes: int = 20 * 1024 * 1024
    url_fetch_timeout_seconds: float = 15.0
    media_cache_max_bytes: int = 12 * 1024 * 1024
    media_cache_dir: str = "media_cache"
    # Phase 11D delivery transports. External channels are opt-in.
    delivery_poll_seconds: float = 1.0
    delivery_email_to: str | None = None
    delivery_smtp_host: str | None = None
    delivery_smtp_port: int = 587
    delivery_smtp_username: str | None = None
    delivery_smtp_password: str | None = None
    delivery_smtp_from: str | None = None
    delivery_smtp_starttls: bool = True
    delivery_push_webhook_url: str | None = None
    scheduler_version: str = "raos-scheduler-0.5.0"
    attention_policy_version: str = "raos-attention-policy-0.5.0"
    decision_strategy_id: str = "one-delta"
    fingerprint_version: str = "fp-v1"
    cors_origins: str = "http://localhost:3000"
    long_source_chunk_chars: int = 6000
    long_source_chunk_overlap: int = 400
    # none: omit thinking fields (OpenAI-compatible).
    # deepseek: send DeepSeek-compatible thinking / reasoning_effort when a stage requests them.
    llm_thinking_protocol: str = "none"
    # auto: Qwen instruct prefix when the embedding model name contains qwen.
    embedding_query_protocol: str = "auto"


settings = Settings()
