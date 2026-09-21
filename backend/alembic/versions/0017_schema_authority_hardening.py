"""Harden schema authority and align Alembic head with ORM structural metadata.

This migration repairs historical drift that was previously masked by application
startup Base.metadata.create_all(). It is intentionally structural only.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0017_schema_authority_hardening"
down_revision = "0016_event_processor_v1"
branch_labels = None
depends_on = None


def _fk_exists(insp, table: str, local: str, remote_table: str, remote: str = "id") -> bool:
    for fk in insp.get_foreign_keys(table):
        if (
            list(fk.get("constrained_columns") or []) == [local]
            and fk.get("referred_table") == remote_table
            and list(fk.get("referred_columns") or []) == [remote]
        ):
            return True
    return False


def _index_names(insp, table: str) -> set[str]:
    return {str(row.get("name")) for row in insp.get_indexes(table) if row.get("name")}


def _unique_names(insp, table: str) -> set[str]:
    return {str(row.get("name")) for row in insp.get_unique_constraints(table) if row.get("name")}


def _add_fk_if_missing(table: str, local: str, remote_table: str, name: str) -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if _fk_exists(insp, table, local, remote_table):
        return
    with op.batch_alter_table(table) as batch:
        batch.create_foreign_key(name, remote_table, [local], ["id"])


def _set_not_null_if_needed(table: str, column: str, existing_type) -> None:
    bind = op.get_bind()
    cols = {row["name"]: row for row in inspect(bind).get_columns(table)}
    row = cols.get(column)
    if row is None or row.get("nullable") is False:
        return
    with op.batch_alter_table(table) as batch:
        batch.alter_column(column, existing_type=existing_type, nullable=False)


def upgrade() -> None:
    # Historical migrations created these timestamp columns nullable on SQLite,
    # while the ORM contract has always treated them as required.
    for table, column in (
        ("analysis_runs", "created_at"),
        ("event_evidence_frames", "created_at"),
        ("event_lineage", "created_at"),
        ("event_membership_assertions", "created_at"),
        ("event_revisions", "created_at"),
        ("impact_replays", "created_at"),
        ("kernel_embeddings", "updated_at"),
        ("representation_audit_runs", "created_at"),
        ("watch_delegations", "created_at"),
        ("watch_delegations", "updated_at"),
    ):
        _set_not_null_if_needed(table, column, sa.DateTime(timezone=True))

    # Foreign keys omitted by early SQLite-oriented add_column migrations.
    for table, local, remote_table, name in (
        ("attention_feedback", "analysis_run_id", "analysis_runs", "fk_attention_feedback_analysis_run_id"),
        ("attention_plans", "runtime_context_id", "runtime_contexts", "fk_attention_plans_runtime_context_id"),
        ("attention_plans", "analysis_run_id", "analysis_runs", "fk_attention_plans_analysis_run_id"),
        ("claims", "analysis_run_id", "analysis_runs", "fk_claims_analysis_run_id"),
        ("evidence_links", "analysis_run_id", "analysis_runs", "fk_evidence_links_analysis_run_id"),
        ("inferences", "analysis_run_id", "analysis_runs", "fk_inferences_analysis_run_id"),
        ("kernel_patches", "analysis_run_id", "analysis_runs", "fk_kernel_patches_analysis_run_id"),
        ("kernel_patches", "attention_plan_id", "attention_plans", "fk_kernel_patches_attention_plan_id"),
        ("observations", "analysis_run_id", "analysis_runs", "fk_observations_analysis_run_id"),
        ("watches", "analysis_run_id", "analysis_runs", "fk_watches_analysis_run_id"),
        ("watches", "attention_plan_id", "attention_plans", "fk_watches_attention_plan_id"),
    ):
        _add_fk_if_missing(table, local, remote_table, name)

    # Align index identity with current ORM metadata so future autogeneration is
    # stable instead of proposing endless semantic no-op renames.
    bind = op.get_bind()
    insp = inspect(bind)
    indexes = _index_names(insp, "attention_feedback")
    with op.batch_alter_table("attention_feedback") as batch:
        if "ix_attention_feedback_plan_id" in indexes:
            batch.drop_index("ix_attention_feedback_plan_id")
        if "ix_attention_feedback_attention_plan_id" not in indexes:
            batch.create_index("ix_attention_feedback_attention_plan_id", ["attention_plan_id"], unique=False)
        if "ix_attention_feedback_run_id" in indexes:
            batch.drop_index("ix_attention_feedback_run_id")
        if "ix_attention_feedback_analysis_run_id" not in indexes:
            batch.create_index("ix_attention_feedback_analysis_run_id", ["analysis_run_id"], unique=False)

    insp = inspect(bind)
    indexes = _index_names(insp, "watch_delegations")
    with op.batch_alter_table("watch_delegations") as batch:
        if "ix_watch_delegations_actor_id" in indexes:
            batch.drop_index("ix_watch_delegations_actor_id")
        if "ix_watch_delegations_declared_actor_id" not in indexes:
            batch.create_index("ix_watch_delegations_declared_actor_id", ["declared_actor_id"], unique=False)

    # ORM declares these as unique indexed columns. Earlier migrations produced
    # a separate UNIQUE constraint plus non-unique index; normalize to one
    # unique index to make reflected schema match the declared contract.
    for table, column, uq_name, ix_name in (
        (
            "delivery_envelopes",
            "attention_plan_id",
            "uq_delivery_envelopes_attention_plan_id",
            "ix_delivery_envelopes_attention_plan_id",
        ),
        (
            "external_information_items",
            "identity_key",
            "uq_external_information_items_identity_key",
            "ix_external_information_items_identity_key",
        ),
    ):
        insp = inspect(bind)
        unique_names = _unique_names(insp, table)
        index_rows = {str(row.get("name")): row for row in insp.get_indexes(table) if row.get("name")}
        with op.batch_alter_table(table) as batch:
            if uq_name in unique_names:
                batch.drop_constraint(uq_name, type_="unique")
            current = index_rows.get(ix_name)
            if current is not None and not bool(current.get("unique")):
                batch.drop_index(ix_name)
                current = None
            if current is None:
                batch.create_index(ix_name, [column], unique=True)


def downgrade() -> None:
    # This migration repairs historical integrity. Downgrading constraints would
    # reintroduce a known-invalid schema contract, so downgrade is intentionally
    # non-destructive.
    pass
