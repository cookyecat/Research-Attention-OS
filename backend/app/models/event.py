from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship
from sqlalchemy.types import JSON

from app.db import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Event(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "events"

    title: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    status: Mapped[str] = mapped_column(String, nullable=False, default="CANDIDATE")

    source_links: Mapped[list["EventSource"]] = orm_relationship(back_populates="event", cascade="all, delete-orphan")


class EventSource(Base):
    __tablename__ = "event_sources"

    event_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("events.id"), primary_key=True)
    source_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("sources.id"), primary_key=True)
    relationship: Mapped[str] = mapped_column(String, nullable=False, default="REPORTS")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    event: Mapped[Event] = orm_relationship(back_populates="source_links")


class EventEvidenceFrame(UUIDPrimaryKeyMixin, Base):
    """Immutable Source-grounded evidence for one event proposition.

    V0.1 intentionally stores current extractor output without granting any
    representation authority. One Source may own zero or more frames.
    """

    __tablename__ = "event_evidence_frames"
    __table_args__ = (
        UniqueConstraint("identity_key", name="uq_event_evidence_frames_identity_key"),
        Index("ix_event_evidence_frames_source_created", "source_id", "created_at"),
    )

    identity_key: Mapped[str] = mapped_column(String(128), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False, default="local-default", index=True)
    source_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("sources.id"), nullable=False, index=True)
    source_snapshot_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("information_snapshots.id"), nullable=True, index=True
    )
    analysis_run_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("analysis_runs.id"), nullable=True, index=True
    )
    frame_contract_version: Mapped[str] = mapped_column(String(128), nullable=False)
    semantic_input_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    frame_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    frame_digest: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RepresentationAuditRun(UUIDPrimaryKeyMixin, Base):
    """Immutable semantic relation judgment. Shadow by default in V0.1."""

    __tablename__ = "representation_audit_runs"
    __table_args__ = (
        UniqueConstraint("identity_key", name="uq_representation_audit_runs_identity_key"),
        Index("ix_representation_audit_subject", "subject_type", "subject_id"),
        Index("ix_representation_audit_object", "object_type", "object_id"),
    )

    identity_key: Mapped[str] = mapped_column(String(128), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False, default="local-default", index=True)
    origin_device_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    authority_epoch: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    audit_type: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    object_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    input_evidence_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    input_frame_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidence_bundle_refs: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    auditor_contract_version: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model: Mapped[str | None] = mapped_column(String(256), nullable=True)
    judgments: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    supporting_evidence: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    conflicting_evidence: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    uncertainty: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    proposed_transition: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    authority_policy_version: Mapped[str] = mapped_column(String(128), nullable=False, default="shadow-none-v0.1")
    authority_result: Mapped[str] = mapped_column(String(64), nullable=False, default="SHADOW_ONLY")
    authorized_by: Mapped[str | None] = mapped_column(String(256), nullable=True)
    execution_context_digest: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventRevision(UUIDPrimaryKeyMixin, Base):
    """Immutable description revision of one Event hypothesis."""

    __tablename__ = "event_revisions"
    __table_args__ = (
        UniqueConstraint("event_id", "revision_digest", name="uq_event_revisions_event_digest"),
        Index("ix_event_revisions_event_created", "event_id", "created_at"),
    )

    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False, default="local-default", index=True)
    event_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("events.id"), nullable=False, index=True)
    parent_revision_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("event_revisions.id"), nullable=True)
    revision_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    revision_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    audit_run_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("representation_audit_runs.id"), nullable=True, index=True
    )
    authority_epoch: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventLineage(UUIDPrimaryKeyMixin, Base):
    """Append-only topology between historical Event hypotheses."""

    __tablename__ = "event_lineage"
    __table_args__ = (
        UniqueConstraint(
            "predecessor_event_id",
            "successor_event_id",
            "relationship",
            name="uq_event_lineage_relation",
        ),
    )

    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False, default="local-default", index=True)
    predecessor_event_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("events.id"), nullable=False, index=True)
    successor_event_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("events.id"), nullable=False, index=True)
    relationship: Mapped[str] = mapped_column(String(64), nullable=False)
    audit_run_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("representation_audit_runs.id"), nullable=True, index=True
    )
    authority_epoch: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventMembershipAssertion(UUIDPrimaryKeyMixin, Base):
    """Append-only authority assertion linking Source evidence to an Event hypothesis."""

    __tablename__ = "event_membership_assertions"
    __table_args__ = (
        Index("ix_event_membership_event_source_created", "event_id", "source_id", "created_at"),
    )

    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False, default="local-default", index=True)
    event_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("events.id"), nullable=False, index=True)
    source_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("sources.id"), nullable=False, index=True)
    frame_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    membership: Mapped[str] = mapped_column(String(64), nullable=False)
    contextual_role_fields: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    audit_run_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("representation_audit_runs.id"), nullable=True, index=True
    )
    authority_policy_version: Mapped[str] = mapped_column(String(128), nullable=False)
    authority_epoch: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    authority_status: Mapped[str] = mapped_column(String(64), nullable=False)
    supersedes_assertion_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("event_membership_assertions.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
