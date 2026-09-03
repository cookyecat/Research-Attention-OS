"""Create impact_replays table for Cognitive Impact Replay harness v0.1."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0005_impact_replay_v01"
down_revision = "0004_human_feedback_v01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "impact_replays" in insp.get_table_names():
        return
    op.create_table(
        "impact_replays",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(), nullable=True),
        sa.Column("input_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("replay_version", sa.String(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("frozen_input", sa.JSON(), nullable=False),
        sa.Column("stages", sa.JSON(), nullable=False),
        sa.Column("attribution", sa.JSON(), nullable=False),
        sa.Column("runtime", sa.JSON(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_impact_replays_analysis_run_id", "impact_replays", ["analysis_run_id"])
    op.create_index("ix_impact_replays_input_fingerprint", "impact_replays", ["input_fingerprint"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "impact_replays" not in insp.get_table_names():
        return
    op.drop_index("ix_impact_replays_input_fingerprint", table_name="impact_replays")
    op.drop_index("ix_impact_replays_analysis_run_id", table_name="impact_replays")
    op.drop_table("impact_replays")
