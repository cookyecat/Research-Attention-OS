from __future__ import annotations

from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RAOS_", extra="ignore")

    database_url: str = "sqlite:///./raos.db"
    auto_create_tables: bool = True
    cognitive_provider: str = "rule"
    cognitive_contract: str = "legacy"
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
    delivery_poll_seconds: float = 1.0
    delivery_email_to: str | None = None
    delivery_smtp_host: str | None = None
    delivery_smtp_port: int = 587
    delivery_smtp_username: str | None = None
    delivery_smtp_password: str | None = None
    delivery_smtp_from: str | None = None
    delivery_smtp_starttls: bool = True
    delivery_smtp_ssl: bool = False
    delivery_push_webhook_url: str | None = None
    scheduler_version: str = "raos-scheduler-0.5.0"
    attention_policy_version: str = "raos-attention-policy-0.5.0"
    decision_strategy_id: str = "one-delta"
    fingerprint_version: str = "fp-v1"
    cors_origins: str = "http://localhost:3000"
    long_source_chunk_chars: int = 6000
    long_source_chunk_overlap: int = 400
    llm_thinking_protocol: str = "none"
    embedding_query_protocol: str = "auto"
    runtime_profile: str | None = None
    execution_purpose: str = "UNSPECIFIED"
    runtime_install_mode: str = "manual"


def _load_runtime_profile(path_value: str | None) -> tuple[dict | None, str | None]:
    if not path_value:
        return None, None
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    if not path.exists():
        raise RuntimeError(f"RAOS runtime profile not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict) or not raw.get("profile_id"):
        raise RuntimeError(f"Invalid RAOS runtime profile: {path}")
    return raw, str(path)


settings = Settings()
runtime_profile, runtime_profile_path = _load_runtime_profile(settings.runtime_profile)

if runtime_profile is not None:
    authority = dict(runtime_profile.get("authority") or {})
    # Authority-bearing configuration comes from the versioned profile. Local
    # environment files may provide secrets/operational settings but cannot
    # silently redefine canonical cognition semantics.
    settings.cognitive_provider = str(authority.get("cognition_provider") or settings.cognitive_provider)
    settings.cognitive_contract = str(authority.get("cognition_contract") or settings.cognitive_contract)
    settings.decision_strategy_id = str(authority.get("decision_strategy_id") or settings.decision_strategy_id)
    settings.no_delta_awareness_contract = str(
        authority.get("no_delta_awareness_contract") or settings.no_delta_awareness_contract
    )
    settings.execution_purpose = str(runtime_profile.get("execution_purpose") or "CANONICAL").upper()
