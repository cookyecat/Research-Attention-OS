from alembic import op
import sqlalchemy as sa

revision = "0011_delivery_plane"
down_revision = "0010_attention_signal_samples"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "delivery_envelopes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("attention_plan_id", sa.Uuid(), sa.ForeignKey("attention_plans.id"), nullable=False),
        sa.Column("candidate_type", sa.String(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("disposition", sa.String(), nullable=False),
        sa.Column("urgency", sa.String(), nullable=False),
        sa.Column("delivery_class", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("channels", sa.JSON(), nullable=False),
        sa.Column("channel_status", sa.JSON(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("policy_version", sa.Text(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_outcome", sa.String(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("attention_plan_id", name="uq_delivery_envelopes_attention_plan_id"),
    )
    op.create_index("ix_delivery_envelopes_attention_plan_id", "delivery_envelopes", ["attention_plan_id"])
    op.create_index("ix_delivery_envelopes_candidate_id", "delivery_envelopes", ["candidate_id"])
    op.create_index("ix_delivery_envelopes_disposition", "delivery_envelopes", ["disposition"])
    op.create_index("ix_delivery_envelopes_delivery_class", "delivery_envelopes", ["delivery_class"])
    op.create_index("ix_delivery_envelopes_state", "delivery_envelopes", ["state"])


def downgrade() -> None:
    op.drop_index("ix_delivery_envelopes_state", table_name="delivery_envelopes")
    op.drop_index("ix_delivery_envelopes_delivery_class", table_name="delivery_envelopes")
    op.drop_index("ix_delivery_envelopes_disposition", table_name="delivery_envelopes")
    op.drop_index("ix_delivery_envelopes_candidate_id", table_name="delivery_envelopes")
    op.drop_index("ix_delivery_envelopes_attention_plan_id", table_name="delivery_envelopes")
    op.drop_table("delivery_envelopes")
