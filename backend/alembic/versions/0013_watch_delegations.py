"""Phase 12D multi-actor WATCH delegation provenance."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0013_watch_delegations"
down_revision = "0012_feedback_attribution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "watch_delegations" in insp.get_table_names():
        return
    op.create_table(
        "watch_delegations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("watch_id", sa.Uuid(), nullable=False),
        sa.Column("declared_actor_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column("request_context", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_reason", sa.Text(), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["watch_id"], ["watches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_watch_delegations_watch_id", "watch_delegations", ["watch_id"])
    op.create_index("ix_watch_delegations_actor_id", "watch_delegations", ["declared_actor_id"])
    op.create_index("ix_watch_delegations_status", "watch_delegations", ["status"])


def downgrade() -> None:
    bind = op.get_bind()
    if "watch_delegations" not in inspect(bind).get_table_names():
        return
    op.drop_table("watch_delegations")
