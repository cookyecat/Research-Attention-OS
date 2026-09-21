"""Frozen initial schema from commit c57af066 (2026-08-26).

IMPORTANT: this migration is a historical schema snapshot. It must never import
current ORM models or call Base.metadata.create_all()/drop_all(). Later schema
changes belong in later explicit migrations.
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('attention_plans',
    sa.Column('candidate_type', sa.String(), nullable=False),
    sa.Column('candidate_id', sa.Uuid(), nullable=False),
    sa.Column('attention_state', sa.String(), nullable=False),
    sa.Column('processing_modes', sa.JSON(), nullable=False),
    sa.Column('urgency', sa.String(), nullable=False),
    sa.Column('cognitive_budget_minutes', sa.Integer(), nullable=True),
    sa.Column('kernel_target_ids', sa.JSON(), nullable=False),
    sa.Column('expected_output', sa.String(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('watch_after_processing', sa.Boolean(), nullable=False),
    sa.Column('scheduler_version', sa.Text(), nullable=False),
    sa.Column('score_debug', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_attention_plans_candidate_id'), 'attention_plans', ['candidate_id'], unique=False)
    op.create_table('events',
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('event_type', sa.Text(), nullable=True),
    sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('location', sa.Text(), nullable=True),
    sa.Column('summary', sa.Text(), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('evidence_links',
    sa.Column('source_object_type', sa.String(), nullable=False),
    sa.Column('source_object_id', sa.Uuid(), nullable=False),
    sa.Column('target_object_type', sa.String(), nullable=False),
    sa.Column('target_object_id', sa.Uuid(), nullable=False),
    sa.Column('stance', sa.String(), nullable=False),
    sa.Column('strength', sa.String(), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('scope', sa.Text(), nullable=True),
    sa.Column('proposed_by', sa.String(), nullable=False),
    sa.Column('accepted_by_user', sa.Boolean(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evidence_links_source_object_id'), 'evidence_links', ['source_object_id'], unique=False)
    op.create_index(op.f('ix_evidence_links_source_object_type'), 'evidence_links', ['source_object_type'], unique=False)
    op.create_index(op.f('ix_evidence_links_stance'), 'evidence_links', ['stance'], unique=False)
    op.create_index(op.f('ix_evidence_links_target_object_id'), 'evidence_links', ['target_object_id'], unique=False)
    op.create_index(op.f('ix_evidence_links_target_object_type'), 'evidence_links', ['target_object_type'], unique=False)
    op.create_table('inferences',
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('author_type', sa.String(), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('scope', sa.Text(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('ingestion_jobs',
    sa.Column('connector_type', sa.String(), nullable=False),
    sa.Column('input_ref', sa.Text(), nullable=True),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('attempt_count', sa.Integer(), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('kernel_nodes',
    sa.Column('node_type', sa.String(), nullable=False),
    sa.Column('title', sa.Text(), nullable=True),
    sa.Column('current_version', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('payload', sa.JSON(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_kernel_nodes_node_type'), 'kernel_nodes', ['node_type'], unique=False)
    op.create_table('kernel_patches',
    sa.Column('target_object_type', sa.String(), nullable=False),
    sa.Column('target_object_id', sa.Uuid(), nullable=True),
    sa.Column('change_type', sa.String(), nullable=False),
    sa.Column('current_state', sa.JSON(), nullable=True),
    sa.Column('proposed_state', sa.JSON(), nullable=False),
    sa.Column('evidence_link_ids', sa.JSON(), nullable=False),
    sa.Column('reasoning', sa.Text(), nullable=False),
    sa.Column('suggested_confidence_change', sa.JSON(), nullable=True),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('proposed_by', sa.String(), nullable=False),
    sa.Column('reviewed_by_user_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_kernel_patches_status'), 'kernel_patches', ['status'], unique=False)
    op.create_index(op.f('ix_kernel_patches_target_object_id'), 'kernel_patches', ['target_object_id'], unique=False)
    op.create_table('runtime_contexts',
    sa.Column('current_task', sa.Text(), nullable=True),
    sa.Column('session_topic', sa.Text(), nullable=True),
    sa.Column('available_attention_minutes', sa.Integer(), nullable=True),
    sa.Column('interruptibility', sa.String(), nullable=True),
    sa.Column('cognitive_capacity', sa.String(), nullable=True),
    sa.Column('deadline_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('captured_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('sources',
    sa.Column('source_type', sa.String(), nullable=False),
    sa.Column('title', sa.Text(), nullable=True),
    sa.Column('canonical_url', sa.Text(), nullable=True),
    sa.Column('content_text', sa.Text(), nullable=True),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('ingested_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('publisher', sa.Text(), nullable=True),
    sa.Column('language', sa.String(), nullable=True),
    sa.Column('fingerprint', sa.Text(), nullable=False),
    sa.Column('content_hash', sa.Text(), nullable=True),
    sa.Column('ingestion_method', sa.Text(), nullable=False),
    sa.Column('raw_metadata', sa.JSON(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sources_content_hash'), 'sources', ['content_hash'], unique=False)
    op.create_index(op.f('ix_sources_fingerprint'), 'sources', ['fingerprint'], unique=False)
    op.create_table('temporal_policies',
    sa.Column('freshness_window_seconds', sa.Integer(), nullable=True),
    sa.Column('relevance_decay', sa.String(), nullable=False),
    sa.Column('validity_review_seconds', sa.Integer(), nullable=True),
    sa.Column('review_triggers', sa.JSON(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('watches',
    sa.Column('target_type', sa.String(), nullable=False),
    sa.Column('target_ref', sa.Text(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('created_reason', sa.Text(), nullable=False),
    sa.Column('kernel_target_ids', sa.JSON(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('attention_feedback',
    sa.Column('attention_plan_id', sa.Uuid(), nullable=False),
    sa.Column('system_attention_state', sa.String(), nullable=True),
    sa.Column('user_attention_state', sa.String(), nullable=True),
    sa.Column('system_modes', sa.JSON(), nullable=True),
    sa.Column('user_modes', sa.JSON(), nullable=True),
    sa.Column('opened', sa.Boolean(), nullable=True),
    sa.Column('engaged_seconds', sa.Integer(), nullable=True),
    sa.Column('created_kernel_patch', sa.Boolean(), nullable=True),
    sa.Column('created_decision', sa.Boolean(), nullable=True),
    sa.Column('created_experiment', sa.Boolean(), nullable=True),
    sa.Column('feedback_text', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['attention_plan_id'], ['attention_plans.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('claims',
    sa.Column('source_id', sa.Uuid(), nullable=False),
    sa.Column('event_id', sa.Uuid(), nullable=True),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('normalized_text', sa.Text(), nullable=True),
    sa.Column('claim_type', sa.String(), nullable=False),
    sa.Column('attributed_to', sa.Text(), nullable=True),
    sa.Column('attribution_type', sa.String(), nullable=True),
    sa.Column('scope', sa.Text(), nullable=True),
    sa.Column('confidence_extraction', sa.Float(), nullable=True),
    sa.Column('credibility_estimate', sa.Float(), nullable=True),
    sa.Column('temporal_policy_id', sa.Uuid(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
    sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_claims_source_id'), 'claims', ['source_id'], unique=False)
    op.create_table('event_sources',
    sa.Column('event_id', sa.Uuid(), nullable=False),
    sa.Column('source_id', sa.Uuid(), nullable=False),
    sa.Column('relationship', sa.String(), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
    sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ),
    sa.PrimaryKeyConstraint('event_id', 'source_id')
    )
    op.create_table('inference_sources',
    sa.Column('inference_id', sa.Uuid(), nullable=False),
    sa.Column('source_object_type', sa.String(), nullable=False),
    sa.Column('source_object_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['inference_id'], ['inferences.id'], ),
    sa.PrimaryKeyConstraint('inference_id', 'source_object_type', 'source_object_id')
    )
    op.create_table('kernel_edges',
    sa.Column('source_node_id', sa.Uuid(), nullable=False),
    sa.Column('target_node_id', sa.Uuid(), nullable=False),
    sa.Column('relationship', sa.String(), nullable=False),
    sa.Column('metadata', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['source_node_id'], ['kernel_nodes.id'], ),
    sa.ForeignKeyConstraint(['target_node_id'], ['kernel_nodes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('kernel_versions',
    sa.Column('kernel_node_id', sa.Uuid(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('snapshot', sa.JSON(), nullable=False),
    sa.Column('patch_id', sa.Uuid(), nullable=True),
    sa.Column('committed_by', sa.String(), nullable=False),
    sa.Column('committed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['kernel_node_id'], ['kernel_nodes.id'], ),
    sa.ForeignKeyConstraint(['patch_id'], ['kernel_patches.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('kernel_node_id', 'version', name='uq_kernel_node_version')
    )
    op.create_table('observations',
    sa.Column('source_id', sa.Uuid(), nullable=True),
    sa.Column('event_id', sa.Uuid(), nullable=True),
    sa.Column('observer_type', sa.String(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('observation_type', sa.String(), nullable=False),
    sa.Column('measured_values', sa.JSON(), nullable=True),
    sa.Column('scope', sa.Text(), nullable=True),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('temporal_policy_id', sa.Uuid(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
    sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_observations_source_id'), 'observations', ['source_id'], unique=False)
    op.create_table('parser_runs',
    sa.Column('source_id', sa.Uuid(), nullable=False),
    sa.Column('parser_name', sa.Text(), nullable=False),
    sa.Column('parser_version', sa.Text(), nullable=False),
    sa.Column('output_metadata', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('source_authors',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('source_id', sa.Uuid(), nullable=False),
    sa.Column('author_name', sa.Text(), nullable=False),
    sa.Column('author_type', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('source_edges',
    sa.Column('source_id', sa.Uuid(), nullable=False),
    sa.Column('target_id', sa.Uuid(), nullable=False),
    sa.Column('relationship', sa.String(), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('detected_by', sa.String(), nullable=False),
    sa.Column('evidence', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ),
    sa.ForeignKeyConstraint(['target_id'], ['sources.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_source_edges_source_id'), 'source_edges', ['source_id'], unique=False)
    op.create_index(op.f('ix_source_edges_target_id'), 'source_edges', ['target_id'], unique=False)
    op.create_table('watch_triggers',
    sa.Column('watch_id', sa.Uuid(), nullable=False),
    sa.Column('trigger_type', sa.String(), nullable=False),
    sa.Column('trigger_config', sa.JSON(), nullable=False),
    sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['watch_id'], ['watches.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('watch_triggers')
    op.drop_index(op.f('ix_source_edges_target_id'), table_name='source_edges')
    op.drop_index(op.f('ix_source_edges_source_id'), table_name='source_edges')
    op.drop_table('source_edges')
    op.drop_table('source_authors')
    op.drop_table('parser_runs')
    op.drop_index(op.f('ix_observations_source_id'), table_name='observations')
    op.drop_table('observations')
    op.drop_table('kernel_versions')
    op.drop_table('kernel_edges')
    op.drop_table('inference_sources')
    op.drop_table('event_sources')
    op.drop_index(op.f('ix_claims_source_id'), table_name='claims')
    op.drop_table('claims')
    op.drop_table('attention_feedback')
    op.drop_table('watches')
    op.drop_table('temporal_policies')
    op.drop_index(op.f('ix_sources_fingerprint'), table_name='sources')
    op.drop_index(op.f('ix_sources_content_hash'), table_name='sources')
    op.drop_table('sources')
    op.drop_table('runtime_contexts')
    op.drop_index(op.f('ix_kernel_patches_target_object_id'), table_name='kernel_patches')
    op.drop_index(op.f('ix_kernel_patches_status'), table_name='kernel_patches')
    op.drop_table('kernel_patches')
    op.drop_index(op.f('ix_kernel_nodes_node_type'), table_name='kernel_nodes')
    op.drop_table('kernel_nodes')
    op.drop_table('ingestion_jobs')
    op.drop_table('inferences')
    op.drop_index(op.f('ix_evidence_links_target_object_type'), table_name='evidence_links')
    op.drop_index(op.f('ix_evidence_links_target_object_id'), table_name='evidence_links')
    op.drop_index(op.f('ix_evidence_links_stance'), table_name='evidence_links')
    op.drop_index(op.f('ix_evidence_links_source_object_type'), table_name='evidence_links')
    op.drop_index(op.f('ix_evidence_links_source_object_id'), table_name='evidence_links')
    op.drop_table('evidence_links')
    op.drop_table('events')
    op.drop_index(op.f('ix_attention_plans_candidate_id'), table_name='attention_plans')
    op.drop_table('attention_plans')
