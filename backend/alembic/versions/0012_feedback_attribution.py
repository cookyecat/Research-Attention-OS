"""Phase 12A causal attribution metadata for append-only AttentionFeedback."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0012_feedback_attribution"
down_revision = "0011_delivery_plane"
branch_labels = None
depends_on = None


def _has_column(insp, table: str, column: str) -> bool:
    if table not in insp.get_table_names():
        return False
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if not _has_column(insp, "attention_feedback", "attribution"):
        op.add_column(
            "attention_feedback",
            sa.Column("attribution", sa.JSON(), nullable=False, server_default="{}"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if _has_column(insp, "attention_feedback", "attribution"):
        op.drop_column("attention_feedback", "attribution")
