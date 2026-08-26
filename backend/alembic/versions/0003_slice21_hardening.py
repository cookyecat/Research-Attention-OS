"""Slice 2.1: stage provenance, identity uniqueness, source spans, AttentionPlan scheduling metadata, unbounded embeddings.

Does not rewrite 0001/0002. Kernel node tables are not dropped.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = "0003_slice21_hardening"
down_revision = "0002_analysis_run_pgvector"
branch_labels = None
depends_on = None


def _has_table(insp, name: str) -> bool:
    return name in insp.get_table_names()


def _has_column(insp, table: str, column: str) -> bool:
    if not _has_table(insp, table):
        return False
    return column in {c["name"] for c in insp.get_columns(table)}


def _has_index(insp, table: str, name: str) -> bool:
    if not _has_table(insp, table):
        return False
    return name in {i["name"] for i in insp.get_indexes(table)}


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    is_pg = bind.dialect.name == "postgresql"

    if _has_table(insp, "analysis_runs"):
        if not _has_column(insp, "analysis_runs", "stage_provenance"):
            op.add_column("analysis_runs", sa.Column("stage_provenance", sa.JSON(), nullable=True))
        if not _has_column(insp, "analysis_runs", "attempt"):
            op.add_column("analysis_runs", sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"))
        if not _has_index(insp, "analysis_runs", "uq_analysis_identity_live"):
            op.execute(
                text(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_analysis_identity_live
                    ON analysis_runs (identity_key)
                    WHERE status IN ('RUNNING', 'COMPLETED')
                    """
                )
            )

    insp = inspect(bind)
    for table in ("claims", "observations"):
        if not _has_table(insp, table):
            continue
        if not _has_column(insp, table, "source_span_text"):
            op.add_column(table, sa.Column("source_span_text", sa.Text(), nullable=True))
        if not _has_column(insp, table, "source_start_offset"):
            op.add_column(table, sa.Column("source_start_offset", sa.Integer(), nullable=True))
        if not _has_column(insp, table, "source_end_offset"):
            op.add_column(table, sa.Column("source_end_offset", sa.Integer(), nullable=True))
        if not _has_column(insp, table, "chunk_id"):
            op.add_column(table, sa.Column("chunk_id", sa.String(), nullable=True))
        insp = inspect(bind)

    insp = inspect(bind)
    if _has_table(insp, "attention_plans"):
        if not _has_column(insp, "attention_plans", "attention_policy_version"):
            op.add_column("attention_plans", sa.Column("attention_policy_version", sa.String(), nullable=True))
        if not _has_column(insp, "attention_plans", "runtime_context_id"):
            op.add_column("attention_plans", sa.Column("runtime_context_id", sa.Uuid(), nullable=True))
        if not _has_column(insp, "attention_plans", "runtime_snapshot"):
            op.add_column("attention_plans", sa.Column("runtime_snapshot", sa.JSON(), nullable=True))

    if is_pg:
        op.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        insp = inspect(bind)
        if not _has_table(insp, "kernel_embeddings"):
            op.execute(
                text(
                    """
                    CREATE TABLE kernel_embeddings (
                        kernel_node_id UUID PRIMARY KEY REFERENCES kernel_nodes(id),
                        embedding JSON,
                        embedding_model TEXT NOT NULL DEFAULT 'none',
                        dimensions INTEGER,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                    """
                )
            )
        else:
            op.execute(
                text(
                    """
                    DO $$
                    BEGIN
                      IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'kernel_embeddings'
                          AND column_name = 'model_version'
                      ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'kernel_embeddings'
                          AND column_name = 'embedding_model'
                      ) THEN
                        ALTER TABLE kernel_embeddings RENAME COLUMN model_version TO embedding_model;
                      END IF;
                      IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'kernel_embeddings'
                          AND column_name = 'embedding'
                          AND udt_name = 'vector'
                      ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'kernel_embeddings'
                          AND column_name = 'embedding_vec'
                      ) THEN
                        ALTER TABLE kernel_embeddings RENAME COLUMN embedding TO embedding_vec;
                      END IF;
                    END $$;
                    """
                )
            )
            op.execute(text("ALTER TABLE kernel_embeddings ADD COLUMN IF NOT EXISTS embedding JSON"))
            op.execute(text("ALTER TABLE kernel_embeddings ADD COLUMN IF NOT EXISTS embedding_model TEXT"))
            op.execute(text("ALTER TABLE kernel_embeddings ADD COLUMN IF NOT EXISTS dimensions INTEGER"))
            op.execute(text("ALTER TABLE kernel_embeddings ALTER COLUMN embedding_model SET DEFAULT 'none'"))
            # Unbounded vector: drop the 1536 typmod if present.
            op.execute(
                text(
                    """
                    DO $$
                    BEGIN
                      IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'kernel_embeddings' AND column_name = 'embedding_vec'
                      ) THEN
                        ALTER TABLE kernel_embeddings ALTER COLUMN embedding_vec TYPE vector;
                      ELSE
                        ALTER TABLE kernel_embeddings ADD COLUMN embedding_vec vector;
                      END IF;
                    END $$;
                    """
                )
            )
    else:
        insp = inspect(bind)
        if not _has_table(insp, "kernel_embeddings"):
            op.create_table(
                "kernel_embeddings",
                sa.Column("kernel_node_id", sa.Uuid(), sa.ForeignKey("kernel_nodes.id"), primary_key=True),
                sa.Column("embedding", sa.JSON(), nullable=True),
                sa.Column("embedding_model", sa.String(), nullable=False, server_default="none"),
                sa.Column("dimensions", sa.Integer(), nullable=True),
                sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            )


def downgrade() -> None:
    bind = op.get_bind()
    op.execute(text("DROP INDEX IF EXISTS uq_analysis_identity_live"))
    # Keep Kernel tables and embeddings. Slice 2.1 columns can remain.
    _ = bind
