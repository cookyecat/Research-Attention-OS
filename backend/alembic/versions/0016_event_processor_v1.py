"""Event Processor V1 coarse Event materialization fields."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0016_event_processor_v1"
down_revision = "0015_event_frame_semantic_input_digest"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "events" not in tables:
        return
    columns = {row["name"] for row in inspect(bind).get_columns("events")}
    additions = [
        ("actors", sa.JSON()),
        ("action", sa.Text()),
        ("object", sa.Text()),
        ("time_context", sa.Text()),
        ("current_state", sa.Text()),
        ("attributes", sa.JSON()),
    ]
    with op.batch_alter_table("events") as batch:
        for name, coltype in additions:
            if name not in columns:
                batch.add_column(sa.Column(name, coltype, nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "events" not in tables:
        return
    columns = {row["name"] for row in inspect(bind).get_columns("events")}
    with op.batch_alter_table("events") as batch:
        for name in ("attributes", "current_state", "time_context", "object", "action", "actors"):
            if name in columns:
                batch.drop_column(name)
