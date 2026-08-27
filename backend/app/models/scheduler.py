from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class RuntimeContext(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "runtime_contexts"

    current_task: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_topic: Mapped[str | None] = mapped_column(Text, nullable=True)
    available_attention_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    interruptibility: Mapped[str | None] = mapped_column(String, nullable=True)
    cognitive_capacity: Mapped[str | None] = mapped_column(String, nullable=True)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AttentionPlan(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "attention_plans"

    candidate_type: Mapped[str] = mapped_column(String, nullable=False)
    candidate_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    disposition: Mapped[str] = mapped_column("attention_state", String, nullable=False)
    processing_modes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    urgency: Mapped[str] = mapped_column(String, nullable=False)
    cognitive_budget_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kernel_target_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    expected_output: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    watch_after_processing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scheduler_version: Mapped[str] = mapped_column(Text, nullable=False)
    attention_policy_version: Mapped[str | None] = mapped_column(String, nullable=True)
    runtime_context_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("runtime_contexts.id"), nullable=True)
    runtime_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    score_debug: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    analysis_run_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("analysis_runs.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AttentionFeedback(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "attention_feedback"

    attention_plan_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("attention_plans.id"), nullable=False)
    system_attention_state: Mapped[str | None] = mapped_column(String, nullable=True)
    user_attention_state: Mapped[str | None] = mapped_column(String, nullable=True)
    system_modes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    user_modes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    opened: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    engaged_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_kernel_patch: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_decision: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_experiment: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
