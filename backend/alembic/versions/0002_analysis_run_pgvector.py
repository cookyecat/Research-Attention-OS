"""AnalysisRun provenance, analysis_run_id FKs, pgvector extension.

Does not drop or recreate existing Kernel tables. 0001 remains historical
(create_all). Subsequent schema changes must stay explicit.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = "0002_analysis_run_pgvector"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

_PROVENANCE_TABLES = (
    "claims",
    "observations",
    "inferences",
    "evidence_links",
    "attention_plans",
    "kernel_patches",
)


def _has_table(insp, name: str) -> bool:
    return name in insp.get_table_names()


def _has_column(insp, table: str, column: str) -> bool:
    if not _has_table(insp, table):
        return False
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    is_pg = bind.dialect.name == "postgresql"

    if is_pg:
        op.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    if not _has_table(insp, "analysis_runs"):
        op.create_table(
            "analysis_runs",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("source_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("extra_source_ids", sa.JSON(), nullable=False),
            sa.Column("identity_key", sa.String(length=128), nullable=False, index=True),
            sa.Column("extractor_version", sa.String(), nullable=False),
            sa.Column("matcher_version", sa.String(), nullable=False),
            sa.Column("evidence_reasoner_version", sa.String(), nullable=False),
            sa.Column("delta_version", sa.String(), nullable=False),
            sa.Column("scheduler_version", sa.String(), nullable=False),
            sa.Column("prompt_version", sa.String(), nullable=False),
            sa.Column("provider_version", sa.String(), nullable=False),
            sa.Column("embedding_model_version", sa.String(), nullable=False, server_default="none"),
            sa.Column("pipeline_version", sa.String(), nullable=False),
            sa.Column("provider_type", sa.String(), nullable=False),
            sa.Column("model_name", sa.String(), nullable=True),
            sa.Column("input_hash", sa.String(length=128), nullable=False),
            sa.Column("kernel_snapshot_hash", sa.String(length=128), nullable=False),
            sa.Column("status", sa.String(), nullable=False, server_default="PENDING"),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("latency_ms", sa.Integer(), nullable=True),
            sa.Column("prompt_tokens", sa.Integer(), nullable=True),
            sa.Column("completion_tokens", sa.Integer(), nullable=True),
            sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
            sa.Column("result_payload", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )

    insp = inspect(bind)
    for table in _PROVENANCE_TABLES:
        if _has_table(insp, table) and not _has_column(insp, table, "analysis_run_id"):
            op.add_column(table, sa.Column("analysis_run_id", sa.Uuid(), nullable=True))
            op.create_index(
                f"ix_{table}_analysis_run_id",
                table,
                ["analysis_run_id"],
                unique=False,
            )
            if is_pg:
                op.create_foreign_key(
                    f"fk_{table}_analysis_run_id",
                    table,
                    "analysis_runs",
                    ["analysis_run_id"],
                    ["id"],
                )

    if is_pg:
        op.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS kernel_embeddings (
                    kernel_node_id UUID PRIMARY KEY REFERENCES kernel_nodes(id),
                    embedding vector(1536),
                    model_version TEXT NOT NULL DEFAULT 'none',
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(text("DROP TABLE IF EXISTS kernel_embeddings"))
    # Do not drop analysis_runs or Kernel tables. Kernel data outlives code.
