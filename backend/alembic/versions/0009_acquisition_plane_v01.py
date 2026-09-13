from alembic import op
import sqlalchemy as sa

revision = "0009_acquisition_plane_v01"
down_revision = "0008_watch_recheck_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "acquisition_sources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("locator", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("poll_interval_seconds", sa.Integer(), nullable=False),
        sa.Column("last_polled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "external_information_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("identity_key", sa.Text(), nullable=False),
        sa.Column("item_type", sa.String(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("identity_key", name="uq_external_information_items_identity_key"),
    )
    op.create_index("ix_external_information_items_identity_key", "external_information_items", ["identity_key"])
    op.create_table(
        "acquisition_observations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_definition_id", sa.Uuid(), sa.ForeignKey("acquisition_sources.id"), nullable=False),
        sa.Column("external_item_id", sa.Uuid(), sa.ForeignKey("external_information_items.id"), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("external_ref", sa.Text(), nullable=True),
        sa.Column("observation_metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("source_definition_id", "external_item_id", name="uq_acquisition_observation_source_item"),
    )
    op.create_index("ix_acquisition_observations_source_definition_id", "acquisition_observations", ["source_definition_id"])
    op.create_index("ix_acquisition_observations_external_item_id", "acquisition_observations", ["external_item_id"])
    op.create_table(
        "information_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("external_item_id", sa.Uuid(), sa.ForeignKey("external_information_items.id"), nullable=False),
        sa.Column("raos_source_id", sa.Uuid(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=True),
        sa.Column("snapshot_metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("external_item_id", "content_hash", name="uq_information_snapshot_item_hash"),
    )
    op.create_index("ix_information_snapshots_external_item_id", "information_snapshots", ["external_item_id"])
    op.create_index("ix_information_snapshots_raos_source_id", "information_snapshots", ["raos_source_id"])


def downgrade() -> None:
    op.drop_index("ix_information_snapshots_raos_source_id", table_name="information_snapshots")
    op.drop_index("ix_information_snapshots_external_item_id", table_name="information_snapshots")
    op.drop_table("information_snapshots")
    op.drop_index("ix_acquisition_observations_external_item_id", table_name="acquisition_observations")
    op.drop_index("ix_acquisition_observations_source_definition_id", table_name="acquisition_observations")
    op.drop_table("acquisition_observations")
    op.drop_index("ix_external_information_items_identity_key", table_name="external_information_items")
    op.drop_table("external_information_items")
    op.drop_table("acquisition_sources")
