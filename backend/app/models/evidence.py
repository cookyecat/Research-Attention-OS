from uuid import UUID

from sqlalchemy import Boolean, Float, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class EvidenceLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "evidence_links"

    source_object_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_object_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    target_object_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    target_object_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    stance: Mapped[str] = mapped_column(String, nullable=False, index=True)
    strength: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_by: Mapped[str] = mapped_column(String, nullable=False)
    accepted_by_user: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    analysis_run_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("analysis_runs.id"), nullable=True, index=True)


class TemporalPolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "temporal_policies"

    freshness_window_seconds: Mapped[int | None] = mapped_column(nullable=True)
    relevance_decay: Mapped[str] = mapped_column(String, nullable=False)
    validity_review_seconds: Mapped[int | None] = mapped_column(nullable=True)
    review_triggers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
