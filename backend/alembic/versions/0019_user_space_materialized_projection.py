"""Add durable User Space materialized read-model tables."""

from alembic import op
import sqlalchemy as sa


revision = "0019_user_space_materialized_projection"
down_revision = "0018_event_revision_observation_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_surface_projections",
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("sources.id"), primary_key=True),
        sa.Column("surface_seq", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("publisher", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("hero_image_url", sa.Text(), nullable=True),
        sa.Column("current_event_id", sa.Uuid(), nullable=True),
        sa.Column("projected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("surface_seq", name="uq_source_surface_projection_seq"),
    )
    op.create_index("ix_source_surface_seq_desc", "source_surface_projections", ["surface_seq"])
    op.create_index("ix_source_surface_event", "source_surface_projections", ["current_event_id"])

    op.create_table(
        "user_attention_projections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_key", sa.String(), nullable=False),
        sa.Column("candidate_type", sa.String(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("attention_plan_id", sa.Uuid(), sa.ForeignKey("attention_plans.id"), nullable=False),
        sa.Column("attention_seq", sa.Integer(), nullable=False),
        sa.Column("disposition", sa.String(), nullable=False),
        sa.Column("representative_source_id", sa.Uuid(), sa.ForeignKey("sources.id"), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("urgency", sa.String(), nullable=True),
        sa.Column("cognitive_budget_minutes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("projected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "owner_key",
            "candidate_type",
            "candidate_id",
            name="uq_user_attention_owner_candidate",
        ),
        sa.UniqueConstraint(
            "owner_key",
            "attention_seq",
            name="uq_user_attention_owner_seq",
        ),
    )
    op.create_index("ix_user_attention_projections_event_id", "user_attention_projections", ["event_id"])
    op.create_index(
        "ix_user_attention_projections_attention_plan_id",
        "user_attention_projections",
        ["attention_plan_id"],
    )
    op.create_index(
        "ix_user_attention_projections_representative_source_id",
        "user_attention_projections",
        ["representative_source_id"],
    )
    op.create_index(
        "ix_user_attention_owner_disposition_seq",
        "user_attention_projections",
        ["owner_key", "disposition", "attention_seq"],
    )
    op.create_index(
        "ix_user_attention_owner_seq",
        "user_attention_projections",
        ["owner_key", "attention_seq"],
    )

    op.create_table(
        "user_source_attention_projections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_key", sa.String(), nullable=False),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("attention_plan_id", sa.Uuid(), sa.ForeignKey("attention_plans.id"), nullable=True),
        sa.Column("disposition", sa.String(), nullable=True),
        sa.Column("attention_seq", sa.Integer(), nullable=True),
        sa.Column("projected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "owner_key",
            "source_id",
            name="uq_user_source_attention_owner_source",
        ),
    )
    op.create_index(
        "ix_user_source_attention_projections_source_id",
        "user_source_attention_projections",
        ["source_id"],
    )
    op.create_index(
        "ix_user_source_attention_projections_event_id",
        "user_source_attention_projections",
        ["event_id"],
    )
    op.create_index(
        "ix_user_source_attention_projections_attention_plan_id",
        "user_source_attention_projections",
        ["attention_plan_id"],
    )
    op.create_index(
        "ix_user_source_attention_owner_event",
        "user_source_attention_projections",
        ["owner_key", "event_id"],
    )
    op.create_index(
        "ix_user_source_attention_owner_disposition",
        "user_source_attention_projections",
        ["owner_key", "disposition"],
    )

    op.create_table(
        "projection_outbox",
        sa.Column("seq", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("change_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_projection_outbox_created_at", "projection_outbox", ["created_at"])
    op.create_index("ix_projection_outbox_processed_at", "projection_outbox", ["processed_at"])

    op.create_table(
        "projection_checkpoints",
        sa.Column("name", sa.String(), primary_key=True),
        sa.Column("last_outbox_seq", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("projection_checkpoints")
    op.drop_index("ix_projection_outbox_processed_at", table_name="projection_outbox")
    op.drop_index("ix_projection_outbox_created_at", table_name="projection_outbox")
    op.drop_table("projection_outbox")

    op.drop_index(
        "ix_user_source_attention_owner_disposition",
        table_name="user_source_attention_projections",
    )
    op.drop_index(
        "ix_user_source_attention_owner_event",
        table_name="user_source_attention_projections",
    )
    op.drop_index(
        "ix_user_source_attention_projections_attention_plan_id",
        table_name="user_source_attention_projections",
    )
    op.drop_index(
        "ix_user_source_attention_projections_event_id",
        table_name="user_source_attention_projections",
    )
    op.drop_index(
        "ix_user_source_attention_projections_source_id",
        table_name="user_source_attention_projections",
    )
    op.drop_table("user_source_attention_projections")

    op.drop_index(
        "ix_user_attention_owner_seq",
        table_name="user_attention_projections",
    )
    op.drop_index(
        "ix_user_attention_owner_disposition_seq",
        table_name="user_attention_projections",
    )
    op.drop_index(
        "ix_user_attention_projections_representative_source_id",
        table_name="user_attention_projections",
    )
    op.drop_index(
        "ix_user_attention_projections_attention_plan_id",
        table_name="user_attention_projections",
    )
    op.drop_index(
        "ix_user_attention_projections_event_id",
        table_name="user_attention_projections",
    )
    op.drop_table("user_attention_projections")

    op.drop_index("ix_source_surface_event", table_name="source_surface_projections")
    op.drop_index("ix_source_surface_seq_desc", table_name="source_surface_projections")
    op.drop_table("source_surface_projections")
