"""Align EventEvidenceFrame semantic digest naming after 0014 rollout."""

from alembic import op
from sqlalchemy import inspect

revision = "0015_event_frame_semantic_input_digest"
down_revision = "0014_representation_auditor_substrate"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "event_evidence_frames" not in tables:
        return
    columns = {row["name"] for row in inspect(bind).get_columns("event_evidence_frames")}
    if "semantic_input_digest" in columns:
        return
    if "semantic_audit_digest" not in columns:
        raise RuntimeError(
            "event_evidence_frames has neither semantic_input_digest nor semantic_audit_digest"
        )
    with op.batch_alter_table("event_evidence_frames") as batch:
        batch.alter_column(
            "semantic_audit_digest",
            new_column_name="semantic_input_digest",
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "event_evidence_frames" not in tables:
        return
    columns = {row["name"] for row in inspect(bind).get_columns("event_evidence_frames")}
    if "semantic_audit_digest" in columns:
        return
    if "semantic_input_digest" not in columns:
        return
    with op.batch_alter_table("event_evidence_frames") as batch:
        batch.alter_column(
            "semantic_input_digest",
            new_column_name="semantic_audit_digest",
        )
