from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db import Base
from app.models.base import UUIDPrimaryKeyMixin


class AnalysisRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "analysis_runs"
    __table_args__ = (
        Index(
            "uq_analysis_identity_live",
            "identity_key",
            unique=True,
            sqlite_where=text("status IN ('RUNNING', 'COMPLETED')"),
            postgresql_where=text("status IN ('RUNNING', 'COMPLETED')"),
        ),
    )

    source_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    extra_source_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    identity_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    extractor_version: Mapped[str] = mapped_column(String, nullable=False)
    matcher_version: Mapped[str] = mapped_column(String, nullable=False)
    evidence_reasoner_version: Mapped[str] = mapped_column(String, nullable=False)
    delta_version: Mapped[str] = mapped_column(String, nullable=False)
    scheduler_version: Mapped[str] = mapped_column(String, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String, nullable=False)
    provider_version: Mapped[str] = mapped_column(String, nullable=False)
    embedding_model_version: Mapped[str] = mapped_column(String, nullable=False, default="none")
    pipeline_version: Mapped[str] = mapped_column(String, nullable=False)

    provider_type: Mapped[str] = mapped_column(String, nullable=False)
    model_name: Mapped[str | None] = mapped_column(String, nullable=True)
    input_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    kernel_snapshot_hash: Mapped[str] = mapped_column(String(128), nullable=False)

    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    fallback_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    result_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    stage_provenance: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
