from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class SourceDefinition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "acquisition_sources"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    locator: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    poll_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=1800)
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExternalInformationItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "external_information_items"

    identity_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    item_type: Mapped[str] = mapped_column(String, nullable=False, default="ARTICLE")
    canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AcquisitionObservation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "acquisition_observations"
    __table_args__ = (
        UniqueConstraint("source_definition_id", "external_item_id", name="uq_acquisition_observation_source_item"),
    )

    source_definition_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("acquisition_sources.id"), nullable=False, index=True
    )
    external_item_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("external_information_items.id"), nullable=False, index=True
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    external_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    observation_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class InformationSnapshot(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "information_snapshots"
    __table_args__ = (
        UniqueConstraint("external_item_id", "content_hash", name="uq_information_snapshot_item_hash"),
    )

    external_item_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("external_information_items.id"), nullable=False, index=True
    )
    raos_source_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("sources.id"), nullable=False, index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    content_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    snapshot_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
