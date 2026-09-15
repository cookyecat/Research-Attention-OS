from alembic import op
import sqlalchemy as sa

revision = "0010_attention_signal_samples"
down_revision = "0009_acquisition_plane_v01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attention_signal_samples",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_definition_id", sa.Uuid(), sa.ForeignKey("acquisition_sources.id"), nullable=False),
        sa.Column("external_item_id", sa.Uuid(), sa.ForeignKey("external_information_items.id"), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("first_observed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("signal_hash", sa.Text(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("signal_context", sa.JSON(), nullable=False),
        sa.Column("quality", sa.String(), nullable=False),
        sa.Column("contamination", sa.JSON(), nullable=False),
    )
    op.create_index("ix_attention_signal_samples_source_definition_id", "attention_signal_samples", ["source_definition_id"])
    op.create_index("ix_attention_signal_samples_external_item_id", "attention_signal_samples", ["external_item_id"])
    op.create_index("ix_attention_signal_samples_platform", "attention_signal_samples", ["platform"])
    op.create_index("ix_attention_signal_samples_signal_hash", "attention_signal_samples", ["signal_hash"])
    op.create_index(
        "ix_attention_signal_samples_platform_item_first",
        "attention_signal_samples",
        ["platform", "external_item_id", "first_observed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_attention_signal_samples_platform_item_first", table_name="attention_signal_samples")
    op.drop_index("ix_attention_signal_samples_signal_hash", table_name="attention_signal_samples")
    op.drop_index("ix_attention_signal_samples_platform", table_name="attention_signal_samples")
    op.drop_index("ix_attention_signal_samples_external_item_id", table_name="attention_signal_samples")
    op.drop_index("ix_attention_signal_samples_source_definition_id", table_name="attention_signal_samples")
    op.drop_table("attention_signal_samples")
