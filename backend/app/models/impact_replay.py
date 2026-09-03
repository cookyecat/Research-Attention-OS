from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db import Base
from app.models.base import UUIDPrimaryKeyMixin


class ImpactReplay(UUIDPrimaryKeyMixin, Base):
    """Instrumentation artifact. Not a cognitive ontology entity.

    Stores one Cognitive Impact replay of a frozen AnalysisRun. Never writes back
    to AnalysisRun, Kernel, AttentionPlan, or AttentionFeedback.
    """

    __tablename__ = "impact_replays"

    analysis_run_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("analysis_runs.id"), nullable=False, index=True)
    label: Mapped[str | None] = mapped_column(String, nullable=True)
    input_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    replay_version: Mapped[str] = mapped_column(String, nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    frozen_input: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    stages: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    attribution: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    runtime: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    provenance: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
