"""Initial pipeline orchestrator tables

Revision ID: 001_initial_pipeline
Revises:
Create Date: 2026-01-15

Creates all tables for:
- EPOCH 7: Pipeline Orchestrator (epochs, pipeline_runs, stage_executions,
           handoff_tokens, guardrail_violations, resource_allocations)
- EPOCH 8: CC Session Manager (cc_sessions)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_pipeline'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # Create Enums
    # ==========================================================================

    # Pipeline stage enum
    pipeline_stage_enum = postgresql.ENUM(
        'queued', 'developing', 'testing', 'verifying',
        'po_review', 'deploying', 'completed', 'failed', 'cancelled',
        name='pipelinestage',
        create_type=False,
    )
    pipeline_stage_enum.create(op.get_bind(), checkfirst=True)

    # Pipeline run status enum
    pipeline_run_status_enum = postgresql.ENUM(
        'running', 'paused', 'completed', 'failed', 'cancelled',
        name='pipelinerunstatus',
        create_type=False,
    )
    pipeline_run_status_enum.create(op.get_bind(), checkfirst=True)

    # Escalation level enum
    escalation_level_enum = postgresql.ENUM(
        'codex', 'sonnet', 'opus', 'human',
        name='escalationlevel',
        create_type=False,
    )
    escalation_level_enum.create(op.get_bind(), checkfirst=True)

    # Guardrail layer enum
    guardrail_layer_enum = postgresql.ENUM(
        'invariant', 'contract', 'policy', 'preference',
        name='guardraillayer',
        create_type=False,
    )
    guardrail_layer_enum.create(op.get_bind(), checkfirst=True)

    # Resource type enum
    resource_type_enum = postgresql.ENUM(
        'frontend_port', 'backend_port', 'database_port', 'redis_port', 'test_port',
        name='resourcetype',
        create_type=False,
    )
    resource_type_enum.create(op.get_bind(), checkfirst=True)

    # Epoch status enum
    epoch_status_enum = postgresql.ENUM(
        'active', 'completed', 'deprecated',
        name='epochstatus',
        create_type=False,
    )
    epoch_status_enum.create(op.get_bind(), checkfirst=True)

    # CC Session status enum
    cc_session_status_enum = postgresql.ENUM(
        'idle', 'starting', 'running', 'stuck',
        'completed', 'failed', 'crashed', 'restarting',
        name='ccsessionstatus',
        create_type=False,
    )
    cc_session_status_enum.create(op.get_bind(), checkfirst=True)

    # CC Session platform enum
    cc_session_platform_enum = postgresql.ENUM(
        'windows', 'linux', 'wsl',
        name='ccsessionplatform',
        create_type=False,
    )
    cc_session_platform_enum.create(op.get_bind(), checkfirst=True)

    # ==========================================================================
    # EPOCH 7: Pipeline Orchestrator Tables
    # ==========================================================================

    # Epochs table
    op.create_table(
        'epochs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('features', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('status', sa.Enum('active', 'completed', 'deprecated', name='epochstatus'), nullable=False, server_default='active'),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    # Pipeline runs table
    op.create_table(
        'pipeline_runs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('task_id', sa.String(length=100), nullable=False),
        sa.Column('task_title', sa.String(length=500), nullable=False),
        sa.Column('task_description', sa.Text(), nullable=True),
        sa.Column('project_name', sa.String(length=255), nullable=True),
        sa.Column('epoch_id', sa.Integer(), nullable=True),
        sa.Column('current_stage', sa.Enum('queued', 'developing', 'testing', 'verifying', 'po_review', 'deploying', 'completed', 'failed', 'cancelled', name='pipelinestage'), nullable=False, server_default='queued'),
        sa.Column('status', sa.Enum('running', 'paused', 'completed', 'failed', 'cancelled', name='pipelinerunstatus'), nullable=False, server_default='running'),
        sa.Column('priority', sa.String(length=20), nullable=False, server_default='normal'),
        sa.Column('escalation_level', sa.Enum('codex', 'sonnet', 'opus', 'human', name='escalationlevel'), nullable=False, server_default='codex'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('final_trust_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('run_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['epoch_id'], ['epochs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_pipeline_runs_task_id', 'pipeline_runs', ['task_id'], unique=False)
    op.create_index('ix_pipeline_runs_current_stage', 'pipeline_runs', ['current_stage'], unique=False)
    op.create_index('ix_pipeline_runs_status', 'pipeline_runs', ['status'], unique=False)

    # Handoff tokens table (create before stage_executions due to FK)
    op.create_table(
        'handoff_tokens',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('pipeline_run_id', sa.UUID(), nullable=False),
        sa.Column('from_stage', sa.Enum('queued', 'developing', 'testing', 'verifying', 'po_review', 'deploying', 'completed', 'failed', 'cancelled', name='pipelinestage'), nullable=False),
        sa.Column('to_stage', sa.Enum('queued', 'developing', 'testing', 'verifying', 'po_review', 'deploying', 'completed', 'failed', 'cancelled', name='pipelinestage'), nullable=False),
        sa.Column('trust_score', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('verification', sa.JSON(), nullable=False),
        sa.Column('tests_score', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0'),
        sa.Column('lint_score', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0'),
        sa.Column('health_score', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0'),
        sa.Column('console_score', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0'),
        sa.Column('signature', sa.String(length=64), nullable=False),
        sa.Column('valid', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('rejected_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['pipeline_run_id'], ['pipeline_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_handoff_tokens_pipeline_run_id', 'handoff_tokens', ['pipeline_run_id'], unique=False)

    # Stage executions table
    op.create_table(
        'stage_executions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('pipeline_run_id', sa.UUID(), nullable=False),
        sa.Column('stage', sa.Enum('queued', 'developing', 'testing', 'verifying', 'po_review', 'deploying', 'completed', 'failed', 'cancelled', name='pipelinestage'), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('output', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('agent_used', sa.String(length=50), nullable=True),
        sa.Column('retry_attempt', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('handoff_token_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['pipeline_run_id'], ['pipeline_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['handoff_token_id'], ['handoff_tokens.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_stage_executions_pipeline_run_id', 'stage_executions', ['pipeline_run_id'], unique=False)

    # Guardrail violations table
    op.create_table(
        'guardrail_violations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('layer', sa.Enum('invariant', 'contract', 'policy', 'preference', name='guardraillayer'), nullable=False),
        sa.Column('rule_name', sa.String(length=100), nullable=False),
        sa.Column('attempted_action', sa.String(length=255), nullable=False),
        sa.Column('blocked', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('override_reason', sa.Text(), nullable=True),
        sa.Column('actor', sa.String(length=100), nullable=True),
        sa.Column('pipeline_run_id', sa.UUID(), nullable=True),
        sa.Column('context', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['pipeline_run_id'], ['pipeline_runs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_guardrail_violations_layer', 'guardrail_violations', ['layer'], unique=False)

    # Resource allocations table
    op.create_table(
        'resource_allocations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('pipeline_run_id', sa.UUID(), nullable=True),
        sa.Column('task_id', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.Enum('frontend_port', 'backend_port', 'database_port', 'redis_port', 'test_port', name='resourcetype'), nullable=False),
        sa.Column('value', sa.Integer(), nullable=False),
        sa.Column('allocated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['pipeline_run_id'], ['pipeline_runs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_resource_allocations_pipeline_run_id', 'resource_allocations', ['pipeline_run_id'], unique=False)
    op.create_index('ix_resource_allocations_task_id', 'resource_allocations', ['task_id'], unique=False)

    # ==========================================================================
    # EPOCH 8: CC Session Manager Tables
    # ==========================================================================

    # CC Sessions table
    op.create_table(
        'cc_sessions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_name', sa.String(length=100), nullable=False),
        sa.Column('platform', sa.Enum('windows', 'linux', 'wsl', name='ccsessionplatform'), nullable=False),
        sa.Column('process_handle', sa.String(length=255), nullable=True),
        sa.Column('working_directory', sa.String(length=1000), nullable=False),
        sa.Column('status', sa.Enum('idle', 'starting', 'running', 'stuck', 'completed', 'failed', 'crashed', 'restarting', name='ccsessionstatus'), nullable=False, server_default='idle'),
        sa.Column('pipeline_run_id', sa.UUID(), nullable=True),
        sa.Column('stage_id', sa.String(length=50), nullable=True),
        sa.Column('task_prompt', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_heartbeat', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_output_line', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('output_file', sa.String(length=500), nullable=True),
        sa.Column('restart_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_restarts', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('parent_session_id', sa.UUID(), nullable=True),
        sa.Column('dangerous_mode', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('max_runtime_minutes', sa.Integer(), nullable=False, server_default='25'),
        sa.Column('heartbeat_timeout_seconds', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('exit_code', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('completion_detected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('context_snapshot', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['pipeline_run_id'], ['pipeline_runs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['parent_session_id'], ['cc_sessions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_name'),
    )
    op.create_index('ix_cc_sessions_session_name', 'cc_sessions', ['session_name'], unique=True)
    op.create_index('ix_cc_sessions_status', 'cc_sessions', ['status'], unique=False)
    op.create_index('ix_cc_sessions_pipeline_run_id', 'cc_sessions', ['pipeline_run_id'], unique=False)

    # CC Session outputs table
    op.create_table(
        'cc_session_outputs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('line_number', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_error', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_completion_marker', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['session_id'], ['cc_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_cc_session_outputs_session_id', 'cc_session_outputs', ['session_id'], unique=False)

    # ==========================================================================
    # Seed initial epoch data
    # ==========================================================================

    op.execute("""
        INSERT INTO epochs (name, version, description, features, status, started_at)
        VALUES
            ('EPOCH_7_PIPELINE', '7.0.0', 'Pipeline Orchestrator - Taśmociąg',
             '["handoff_tokens", "trust_scores", "neural_ralph", "guardrails", "escalation"]'::json,
             'active', now()),
            ('EPOCH_8_CC_SESSIONS', '8.0.0', 'CC Session Manager - Visibility & Reliability',
             '["session_tracking", "heartbeat_monitoring", "auto_restart", "output_streaming"]'::json,
             'active', now())
    """)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('cc_session_outputs')
    op.drop_table('cc_sessions')
    op.drop_table('resource_allocations')
    op.drop_table('guardrail_violations')
    op.drop_table('stage_executions')
    op.drop_table('handoff_tokens')
    op.drop_table('pipeline_runs')
    op.drop_table('epochs')

    # Drop enums
    op.execute("DROP TYPE IF EXISTS ccsessionplatform")
    op.execute("DROP TYPE IF EXISTS ccsessionstatus")
    op.execute("DROP TYPE IF EXISTS epochstatus")
    op.execute("DROP TYPE IF EXISTS resourcetype")
    op.execute("DROP TYPE IF EXISTS guardraillayer")
    op.execute("DROP TYPE IF EXISTS escalationlevel")
    op.execute("DROP TYPE IF EXISTS pipelinerunstatus")
    op.execute("DROP TYPE IF EXISTS pipelinestage")
