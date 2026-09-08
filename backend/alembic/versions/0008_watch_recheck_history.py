from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0008_watch_recheck_history"
down_revision = "0007_runtime_threat_authority"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "watch_checks" in insp.get_table_names():
        return
    op.create_table(
        "watch_checks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("watch_id", sa.Uuid(), sa.ForeignKey("watches.id"), nullable=False),
        sa.Column("trigger_id", sa.Uuid(), sa.ForeignKey("watch_triggers.id"), nullable=True),
        sa.Column("new_source_id", sa.Uuid(), sa.ForeignKey("sources.id"), nullable=True),
        sa.Column("analysis_run_id", sa.Uuid(), sa.ForeignKey("analysis_runs.id"), nullable=True),
        sa.Column("attention_plan_id", sa.Uuid(), sa.ForeignKey("attention_plans.id"), nullable=True),
        sa.Column("disposition", sa.String(), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_watch_checks_watch_id", "watch_checks", ["watch_id"])
    op.create_index("ix_watch_checks_analysis_run_id", "watch_checks", ["analysis_run_id"])
    op.create_index("ix_watch_checks_attention_plan_id", "watch_checks", ["attention_plan_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "watch_checks" not in insp.get_table_names():
        return
    op.drop_index("ix_watch_checks_attention_plan_id", table_name="watch_checks")
    op.drop_index("ix_watch_checks_analysis_run_id", table_name="watch_checks")
    op.drop_index("ix_watch_checks_watch_id", table_name="watch_checks")
    op.drop_table("watch_checks")
