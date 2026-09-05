"""Nullable AttentionPlan ownership on KernelPatch and Watch."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0006_plan_artifact_ownership"
down_revision = "0005_impact_replay_v01"
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
    if _has_table(insp, "kernel_patches") and not _has_column(insp, "kernel_patches", "attention_plan_id"):
        op.add_column("kernel_patches", sa.Column("attention_plan_id", sa.Uuid(), nullable=True))
        op.create_index("ix_kernel_patches_attention_plan_id", "kernel_patches", ["attention_plan_id"])
    if _has_table(insp, "watches"):
        if not _has_column(insp, "watches", "analysis_run_id"):
            op.add_column("watches", sa.Column("analysis_run_id", sa.Uuid(), nullable=True))
            op.create_index("ix_watches_analysis_run_id", "watches", ["analysis_run_id"])
        if not _has_column(insp, "watches", "attention_plan_id"):
            op.add_column("watches", sa.Column("attention_plan_id", sa.Uuid(), nullable=True))
            op.create_index("ix_watches_attention_plan_id", "watches", ["attention_plan_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if _has_column(insp, "watches", "attention_plan_id"):
        op.drop_index("ix_watches_attention_plan_id", table_name="watches")
        op.drop_column("watches", "attention_plan_id")
    if _has_column(insp, "watches", "analysis_run_id"):
        op.drop_index("ix_watches_analysis_run_id", table_name="watches")
        op.drop_column("watches", "analysis_run_id")
    if _has_column(insp, "kernel_patches", "attention_plan_id"):
        op.drop_index("ix_kernel_patches_attention_plan_id", table_name="kernel_patches")
        op.drop_column("kernel_patches", "attention_plan_id")
