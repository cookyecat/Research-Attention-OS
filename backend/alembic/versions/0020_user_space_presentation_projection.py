"""Add bounded presentation fields and serving indexes to User Space projection."""

from alembic import op
import sqlalchemy as sa


revision = "0020_user_space_presentation_projection"
down_revision = "0019_user_space_materialized_projection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("source_surface_projections") as batch:
        batch.add_column(sa.Column("ingestion_method", sa.String(), nullable=True))
        batch.add_column(sa.Column("origin_label", sa.Text(), nullable=True))
        batch.add_column(sa.Column("reading_minutes", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("presentation_metadata", sa.JSON(), nullable=True))

    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE source_surface_projections "
            "SET presentation_metadata = '{}' "
            "WHERE presentation_metadata IS NULL"
        )
    )

    with op.batch_alter_table("source_surface_projections") as batch:
        batch.alter_column(
            "presentation_metadata",
            existing_type=sa.JSON(),
            nullable=False,
        )
        batch.create_index(
            "ix_source_surface_projections_origin_label",
            ["origin_label"],
            unique=False,
        )
        batch.create_index(
            "ix_source_surface_ingested_at",
            ["ingested_at"],
            unique=False,
        )

    with op.batch_alter_table("user_attention_projections") as batch:
        batch.create_index(
            "ix_user_attention_owner_created_at",
            ["owner_key", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("user_attention_projections") as batch:
        batch.drop_index("ix_user_attention_owner_created_at")

    with op.batch_alter_table("source_surface_projections") as batch:
        batch.drop_index("ix_source_surface_ingested_at")
        batch.drop_index("ix_source_surface_projections_origin_label")
        batch.drop_column("presentation_metadata")
        batch.drop_column("reading_minutes")
        batch.drop_column("origin_label")
        batch.drop_column("ingestion_method")
