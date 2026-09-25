from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db import Base
from app.models.base import UUIDPrimaryKeyMixin


LOCAL_OWNER_KEY = "local-default"


class SourceSurfaceProjection(Base):
    """Disposable current human-readable Source projection.

    Presentation state only. It carries no epistemic, topology, cognition,
    Attention, Watch, Kernel, or Delivery authority.
    """

    __tablename__ = "source_surface_projections"
    __table_args__ = (
        Index("ix_source_surface_seq_desc", "surface_seq"),
        Index("ix_source_surface_event", "current_event_id"),
        Index("ix_source_surface_ingested_at", "ingested_at"),
    )

    source_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("sources.id"),
        primary_key=True,
    )
    surface_seq: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    publisher: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    ingestion_method: Mapped[str | None] = mapped_column(String, nullable=True)
    origin_label: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    hero_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    reading_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    presentation_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    current_event_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    projected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class UserAttentionProjection(UUIDPrimaryKeyMixin, Base):
    """Disposable current Attention read model for one owner scope.

    owner_key is deliberately not an authenticated user identity yet. The
    current deployment remains SINGLE_USER_DOGFOOD.
    """

    __tablename__ = "user_attention_projections"
    __table_args__ = (
        UniqueConstraint(
            "owner_key",
            "candidate_type",
            "candidate_id",
            name="uq_user_attention_owner_candidate",
        ),
        UniqueConstraint(
            "owner_key",
            "attention_seq",
            name="uq_user_attention_owner_seq",
        ),
        Index(
            "ix_user_attention_owner_disposition_seq",
            "owner_key",
            "disposition",
            "attention_seq",
        ),
        Index(
            "ix_user_attention_owner_seq",
            "owner_key",
            "attention_seq",
        ),
        Index(
            "ix_user_attention_owner_created_at",
            "owner_key",
            "created_at",
        ),
    )

    owner_key: Mapped[str] = mapped_column(String, nullable=False, default=LOCAL_OWNER_KEY)
    candidate_type: Mapped[str] = mapped_column(String, nullable=False)
    candidate_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    event_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    attention_plan_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("attention_plans.id"),
        nullable=False,
        index=True,
    )
    attention_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    disposition: Mapped[str] = mapped_column(String, nullable=False)
    representative_source_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("sources.id"),
        nullable=True,
        index=True,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    urgency: Mapped[str | None] = mapped_column(String, nullable=True)
    cognitive_budget_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    projected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class UserSourceAttentionProjection(UUIDPrimaryKeyMixin, Base):
    """Disposable Event-Attention to Source presentation bridge."""

    __tablename__ = "user_source_attention_projections"
    __table_args__ = (
        UniqueConstraint(
            "owner_key",
            "source_id",
            name="uq_user_source_attention_owner_source",
        ),
        Index(
            "ix_user_source_attention_owner_event",
            "owner_key",
            "event_id",
        ),
        Index(
            "ix_user_source_attention_owner_disposition",
            "owner_key",
            "disposition",
        ),
    )

    owner_key: Mapped[str] = mapped_column(String, nullable=False, default=LOCAL_OWNER_KEY)
    source_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("sources.id"),
        nullable=False,
        index=True,
    )
    event_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    attention_plan_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("attention_plans.id"),
        nullable=True,
        index=True,
    )
    disposition: Mapped[str | None] = mapped_column(String, nullable=True)
    attention_seq: Mapped[int | None] = mapped_column(Integer, nullable=True)
    projected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class ProjectionOutbox(Base):
    """Transactional projection change log.

    Rows are appended in the same transaction as canonical mutations. The
    projector checkpoint advances only after derived read-model updates commit.
    """

    __tablename__ = "projection_outbox"
    __table_args__ = (
        Index("ix_projection_outbox_created_at", "created_at"),
    )

    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    change_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )


class ProjectionCheckpoint(Base):
    """Single-consumer durable cursor for an idempotent projector."""

    __tablename__ = "projection_checkpoints"

    name: Mapped[str] = mapped_column(String, primary_key=True)
    last_outbox_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
