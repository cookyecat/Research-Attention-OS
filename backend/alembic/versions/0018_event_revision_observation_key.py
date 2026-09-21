"""Add durable EventRevision observation identity for Phase17 replay."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0018_event_revision_observation_key"
down_revision = "0017_schema_authority_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "event_revisions" not in set(insp.get_table_names()):
        return

    columns = {row["name"] for row in insp.get_columns("event_revisions")}
    uniques = {
        str(row.get("name"))
        for row in insp.get_unique_constraints("event_revisions")
        if row.get("name")
    }

    with op.batch_alter_table("event_revisions") as batch:
        if "observation_key" not in columns:
            batch.add_column(sa.Column("observation_key", sa.String(length=128), nullable=True))
        if "uq_event_revisions_event_observation" not in uniques:
            batch.create_unique_constraint(
                "uq_event_revisions_event_observation",
                ["event_id", "observation_key"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "event_revisions" not in set(insp.get_table_names()):
        return

    columns = {row["name"] for row in insp.get_columns("event_revisions")}
    uniques = {
        str(row.get("name"))
        for row in insp.get_unique_constraints("event_revisions")
        if row.get("name")
    }

    with op.batch_alter_table("event_revisions") as batch:
        if "uq_event_revisions_event_observation" in uniques:
            batch.drop_constraint(
                "uq_event_revisions_event_observation",
                type_="unique",
            )
        if "observation_key" in columns:
            batch.drop_column("observation_key")
