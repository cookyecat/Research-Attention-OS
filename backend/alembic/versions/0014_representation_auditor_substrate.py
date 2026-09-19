"""Representation Auditor V0.1 append-only substrate."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0014_representation_auditor_substrate"
down_revision = "0013_watch_delegations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())

    if "event_evidence_frames" not in existing:
        op.create_table(
            "event_evidence_frames",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("identity_key", sa.String(length=128), nullable=False),
            sa.Column("workspace_id", sa.String(length=128), nullable=False, server_default="local-default"),
            sa.Column("source_id", sa.Uuid(), nullable=False),
            sa.Column("source_snapshot_id", sa.Uuid(), nullable=True),
            sa.Column("analysis_run_id", sa.Uuid(), nullable=True),
            sa.Column("frame_contract_version", sa.String(length=128), nullable=False),
            sa.Column("semantic_input_digest", sa.String(length=128), nullable=False),
            sa.Column("frame_payload", sa.JSON(), nullable=False),
            sa.Column("frame_digest", sa.String(length=128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"]),
            sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
            sa.ForeignKeyConstraint(["source_snapshot_id"], ["information_snapshots.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("identity_key", name="uq_event_evidence_frames_identity_key"),
        )
        op.create_index("ix_event_evidence_frames_workspace_id", "event_evidence_frames", ["workspace_id"])
        op.create_index("ix_event_evidence_frames_source_id", "event_evidence_frames", ["source_id"])
        op.create_index("ix_event_evidence_frames_source_snapshot_id", "event_evidence_frames", ["source_snapshot_id"])
        op.create_index("ix_event_evidence_frames_analysis_run_id", "event_evidence_frames", ["analysis_run_id"])
        op.create_index("ix_event_evidence_frames_frame_digest", "event_evidence_frames", ["frame_digest"])
        op.create_index("ix_event_evidence_frames_source_created", "event_evidence_frames", ["source_id", "created_at"])

    if "representation_audit_runs" not in existing:
        op.create_table(
            "representation_audit_runs",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("identity_key", sa.String(length=128), nullable=False),
            sa.Column("workspace_id", sa.String(length=128), nullable=False, server_default="local-default"),
            sa.Column("origin_device_id", sa.String(length=256), nullable=True),
            sa.Column("authority_epoch", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("audit_type", sa.String(length=64), nullable=False),
            sa.Column("subject_type", sa.String(length=64), nullable=False),
            sa.Column("subject_id", sa.Uuid(), nullable=False),
            sa.Column("object_type", sa.String(length=64), nullable=False),
            sa.Column("object_id", sa.Uuid(), nullable=False),
            sa.Column("input_evidence_digest", sa.String(length=128), nullable=False),
            sa.Column("input_frame_ids", sa.JSON(), nullable=False),
            sa.Column("evidence_bundle_refs", sa.JSON(), nullable=False),
            sa.Column("auditor_contract_version", sa.String(length=128), nullable=False),
            sa.Column("provider", sa.String(length=128), nullable=True),
            sa.Column("model", sa.String(length=256), nullable=True),
            sa.Column("judgments", sa.JSON(), nullable=False),
            sa.Column("supporting_evidence", sa.JSON(), nullable=False),
            sa.Column("conflicting_evidence", sa.JSON(), nullable=False),
            sa.Column("uncertainty", sa.JSON(), nullable=False),
            sa.Column("proposed_transition", sa.JSON(), nullable=False),
            sa.Column("authority_policy_version", sa.String(length=128), nullable=False, server_default="shadow-none-v0.1"),
            sa.Column("authority_result", sa.String(length=64), nullable=False, server_default="SHADOW_ONLY"),
            sa.Column("authorized_by", sa.String(length=256), nullable=True),
            sa.Column("execution_context_digest", sa.String(length=128), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("identity_key", name="uq_representation_audit_runs_identity_key"),
        )
        op.create_index("ix_representation_audit_runs_workspace_id", "representation_audit_runs", ["workspace_id"])
        op.create_index("ix_representation_audit_subject", "representation_audit_runs", ["subject_type", "subject_id"])
        op.create_index("ix_representation_audit_object", "representation_audit_runs", ["object_type", "object_id"])

    # Refresh because later FKs may target a table created above.
    existing = set(inspect(bind).get_table_names())

    if "event_revisions" not in existing:
        op.create_table(
            "event_revisions",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("workspace_id", sa.String(length=128), nullable=False, server_default="local-default"),
            sa.Column("event_id", sa.Uuid(), nullable=False),
            sa.Column("parent_revision_id", sa.Uuid(), nullable=True),
            sa.Column("revision_payload", sa.JSON(), nullable=False),
            sa.Column("revision_digest", sa.String(length=128), nullable=False),
            sa.Column("audit_run_id", sa.Uuid(), nullable=True),
            sa.Column("authority_epoch", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.ForeignKeyConstraint(["audit_run_id"], ["representation_audit_runs.id"]),
            sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
            sa.ForeignKeyConstraint(["parent_revision_id"], ["event_revisions.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("event_id", "revision_digest", name="uq_event_revisions_event_digest"),
        )
        op.create_index("ix_event_revisions_workspace_id", "event_revisions", ["workspace_id"])
        op.create_index("ix_event_revisions_event_id", "event_revisions", ["event_id"])
        op.create_index("ix_event_revisions_audit_run_id", "event_revisions", ["audit_run_id"])
        op.create_index("ix_event_revisions_event_created", "event_revisions", ["event_id", "created_at"])

    if "event_lineage" not in existing:
        op.create_table(
            "event_lineage",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("workspace_id", sa.String(length=128), nullable=False, server_default="local-default"),
            sa.Column("predecessor_event_id", sa.Uuid(), nullable=False),
            sa.Column("successor_event_id", sa.Uuid(), nullable=False),
            sa.Column("relationship", sa.String(length=64), nullable=False),
            sa.Column("audit_run_id", sa.Uuid(), nullable=True),
            sa.Column("authority_epoch", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.ForeignKeyConstraint(["audit_run_id"], ["representation_audit_runs.id"]),
            sa.ForeignKeyConstraint(["predecessor_event_id"], ["events.id"]),
            sa.ForeignKeyConstraint(["successor_event_id"], ["events.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "predecessor_event_id",
                "successor_event_id",
                "relationship",
                name="uq_event_lineage_relation",
            ),
        )
        op.create_index("ix_event_lineage_workspace_id", "event_lineage", ["workspace_id"])
        op.create_index("ix_event_lineage_predecessor_event_id", "event_lineage", ["predecessor_event_id"])
        op.create_index("ix_event_lineage_successor_event_id", "event_lineage", ["successor_event_id"])
        op.create_index("ix_event_lineage_audit_run_id", "event_lineage", ["audit_run_id"])

    if "event_membership_assertions" not in existing:
        op.create_table(
            "event_membership_assertions",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("workspace_id", sa.String(length=128), nullable=False, server_default="local-default"),
            sa.Column("event_id", sa.Uuid(), nullable=False),
            sa.Column("source_id", sa.Uuid(), nullable=False),
            sa.Column("frame_ids", sa.JSON(), nullable=False),
            sa.Column("action", sa.String(length=32), nullable=False),
            sa.Column("membership", sa.String(length=64), nullable=False),
            sa.Column("contextual_role_fields", sa.JSON(), nullable=False),
            sa.Column("audit_run_id", sa.Uuid(), nullable=True),
            sa.Column("authority_policy_version", sa.String(length=128), nullable=False),
            sa.Column("authority_epoch", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("authority_status", sa.String(length=64), nullable=False),
            sa.Column("supersedes_assertion_id", sa.Uuid(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.ForeignKeyConstraint(["audit_run_id"], ["representation_audit_runs.id"]),
            sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
            sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
            sa.ForeignKeyConstraint(["supersedes_assertion_id"], ["event_membership_assertions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_event_membership_assertions_workspace_id", "event_membership_assertions", ["workspace_id"])
        op.create_index("ix_event_membership_assertions_event_id", "event_membership_assertions", ["event_id"])
        op.create_index("ix_event_membership_assertions_source_id", "event_membership_assertions", ["source_id"])
        op.create_index("ix_event_membership_assertions_audit_run_id", "event_membership_assertions", ["audit_run_id"])
        op.create_index(
            "ix_event_membership_event_source_created",
            "event_membership_assertions",
            ["event_id", "source_id", "created_at"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())
    for name in (
        "event_membership_assertions",
        "event_lineage",
        "event_revisions",
        "representation_audit_runs",
        "event_evidence_frames",
    ):
        if name in existing:
            op.drop_table(name)
