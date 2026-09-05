from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship
from sqlalchemy.types import JSON

from app.db import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class KernelNode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "kernel_nodes"

    node_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    versions: Mapped[list["KernelVersion"]] = orm_relationship(back_populates="node")


class KernelEdge(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "kernel_edges"

    source_node_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("kernel_nodes.id"), nullable=False)
    target_node_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("kernel_nodes.id"), nullable=False)
    relationship: Mapped[str] = mapped_column(String, nullable=False)
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KernelVersion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "kernel_versions"
    __table_args__ = (UniqueConstraint("kernel_node_id", "version", name="uq_kernel_node_version"),)

    kernel_node_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("kernel_nodes.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    patch_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("kernel_patches.id"), nullable=True)
    committed_by: Mapped[str] = mapped_column(String, nullable=False)
    committed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    node: Mapped[KernelNode] = orm_relationship(back_populates="versions")


class KernelEmbedding(Base):
    """Portable embedding store. JSON vector everywhere; Postgres also has unbounded embedding_vec."""

    __tablename__ = "kernel_embeddings"

    kernel_node_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("kernel_nodes.id"), primary_key=True)
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    embedding_model: Mapped[str] = mapped_column(String, nullable=False, default="none")
    dimensions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class KernelPatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "kernel_patches"

    target_object_type: Mapped[str] = mapped_column(String, nullable=False)
    target_object_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    change_type: Mapped[str] = mapped_column(String, nullable=False)
    current_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    proposed_state: Mapped[dict] = mapped_column(JSON, nullable=False)
    evidence_link_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_confidence_change: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PROPOSED", index=True)
    proposed_by: Mapped[str] = mapped_column(String, nullable=False)
    reviewed_by_user_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    analysis_run_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("analysis_runs.id"), nullable=True, index=True)
    attention_plan_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("attention_plans.id"), nullable=True, index=True)
