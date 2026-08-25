from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship
from sqlalchemy.types import JSON

from app.db import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Source(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sources"

    source_type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    publisher: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String, nullable=True)
    fingerprint: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    content_hash: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    ingestion_method: Mapped[str] = mapped_column(Text, nullable=False)
    raw_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    authors: Mapped[list["SourceAuthor"]] = orm_relationship(back_populates="source", cascade="all, delete-orphan")
    outgoing_edges: Mapped[list["SourceEdge"]] = orm_relationship(
        back_populates="source",
        foreign_keys="SourceEdge.source_id",
        cascade="all, delete-orphan",
    )


class SourceAuthor(Base):
    __tablename__ = "source_authors"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("sources.id"), nullable=False)
    author_name: Mapped[str] = mapped_column(Text, nullable=False)
    author_type: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped[Source] = orm_relationship(back_populates="authors")


class SourceEdge(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "source_edges"

    source_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("sources.id"), nullable=False, index=True)
    target_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("sources.id"), nullable=False, index=True)
    relationship: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    detected_by: Mapped[str] = mapped_column(String, nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source: Mapped[Source] = orm_relationship(back_populates="outgoing_edges", foreign_keys=[source_id])
