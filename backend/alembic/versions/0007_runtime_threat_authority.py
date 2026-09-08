from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0007_runtime_threat_authority"
down_revision = "0006_plan_artifact_ownership"
branch_labels = None
depends_on = None


def _has_column(insp, table: str, column: str) -> bool:
    if table not in insp.get_table_names():
        return False
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if not _has_column(insp, "runtime_contexts", "threatens_active_work"):
        op.add_column("runtime_contexts", sa.Column("threatens_active_work", sa.Boolean(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if _has_column(insp, "runtime_contexts", "threatens_active_work"):
        op.drop_column("runtime_contexts", "threatens_active_work")
