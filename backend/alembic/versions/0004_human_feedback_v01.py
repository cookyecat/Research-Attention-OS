"""Human Feedback Loop v0.1 — structured Confirm/Correct on AttentionPlan."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0004_human_feedback_v01"
down_revision = "0003_slice21_hardening"
branch_labels = None
depends_on = None


def _has_table(insp, name: str) -> bool:
    return name in insp.get_table_names()


def _has_column(insp, table: str, column: str) -> bool:
    if not _has_table(insp, table):
        return False
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if not _has_table(insp, "attention_feedback"):
        op.create_table(
            "attention_feedback",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("attention_plan_id", sa.Uuid(), nullable=False),
            sa.Column("analysis_run_id", sa.Uuid(), nullable=True),
            sa.Column("feedback_kind", sa.String(), nullable=False, server_default="CONFIRM"),
            sa.Column("system_prediction", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("user_correction", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("corrected_fields", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("system_attention_state", sa.String(), nullable=True),
            sa.Column("user_attention_state", sa.String(), nullable=True),
            sa.Column("system_modes", sa.JSON(), nullable=True),
            sa.Column("user_modes", sa.JSON(), nullable=True),
            sa.Column("opened", sa.Boolean(), nullable=True),
            sa.Column("engaged_seconds", sa.Integer(), nullable=True),
            sa.Column("created_kernel_patch", sa.Boolean(), nullable=True),
            sa.Column("created_decision", sa.Boolean(), nullable=True),
            sa.Column("created_experiment", sa.Boolean(), nullable=True),
            sa.Column("feedback_text", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["attention_plan_id"], ["attention_plans.id"]),
            sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_attention_feedback_plan_id", "attention_feedback", ["attention_plan_id"])
        op.create_index("ix_attention_feedback_run_id", "attention_feedback", ["analysis_run_id"])
        return

    if not _has_column(insp, "attention_feedback", "feedback_kind"):
        op.add_column("attention_feedback", sa.Column("feedback_kind", sa.String(), nullable=False, server_default="CONFIRM"))
    if not _has_column(insp, "attention_feedback", "analysis_run_id"):
        op.add_column("attention_feedback", sa.Column("analysis_run_id", sa.Uuid(), nullable=True))
    if not _has_column(insp, "attention_feedback", "system_prediction"):
        op.add_column("attention_feedback", sa.Column("system_prediction", sa.JSON(), nullable=False, server_default="{}"))
    if not _has_column(insp, "attention_feedback", "user_correction"):
        op.add_column("attention_feedback", sa.Column("user_correction", sa.JSON(), nullable=False, server_default="{}"))
    if not _has_column(insp, "attention_feedback", "corrected_fields"):
        op.add_column("attention_feedback", sa.Column("corrected_fields", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if not _has_table(insp, "attention_feedback"):
        return
    for col in ("corrected_fields", "user_correction", "system_prediction", "analysis_run_id", "feedback_kind"):
        if _has_column(insp, "attention_feedback", col):
            op.drop_column("attention_feedback", col)
