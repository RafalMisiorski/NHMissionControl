"""Add interactive session support (EPOCH 9)

Revision ID: 002_interactive_sessions
Revises: 001_initial_pipeline
Create Date: 2026-01-16

Adds:
- CCSessionMode enum (headless/interactive)
- CCEventType enum for granular event tracking
- AWAITING_INPUT status to CCSessionStatus
- mode column to cc_sessions table
- cc_session_events table for tool call tracking
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_interactive_sessions'
down_revision = '001_initial_pipeline'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # Create New Enums
    # ==========================================================================

    # CC Session Mode enum
    cc_session_mode_enum = postgresql.ENUM(
        'headless', 'interactive',
        name='ccsessionmode',
        create_type=False,
    )
    cc_session_mode_enum.create(op.get_bind(), checkfirst=True)

    # CC Event Type enum
    cc_event_type_enum = postgresql.ENUM(
        'tool_call_start', 'tool_call_end', 'thinking', 'decision',
        'error', 'prompt_sent', 'response_start', 'response_end',
        'file_read', 'file_write', 'bash_command',
        name='cceventtype',
        create_type=False,
    )
    cc_event_type_enum.create(op.get_bind(), checkfirst=True)

    # ==========================================================================
    # Update CCSessionStatus enum (add AWAITING_INPUT)
    # ==========================================================================
    # Note: SQLite doesn't support ALTER TYPE, so we handle this gracefully
    # For PostgreSQL, we would use:
    # op.execute("ALTER TYPE ccsessionstatus ADD VALUE IF NOT EXISTS 'awaiting_input'")
    # For SQLite, the enum values are stored as strings, so no migration needed

    # ==========================================================================
    # Add mode column to cc_sessions table
    # ==========================================================================
    op.add_column(
        'cc_sessions',
        sa.Column(
            'mode',
            sa.String(20),  # Use String for SQLite compatibility
            nullable=False,
            server_default='headless',
        )
    )

    # ==========================================================================
    # Create cc_session_events table
    # ==========================================================================
    op.create_table(
        'cc_session_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(30), nullable=False),  # String for SQLite
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('tool_name', sa.String(length=100), nullable=True),
        sa.Column('tool_input', sa.JSON(), nullable=True),
        sa.Column('tool_output', sa.Text(), nullable=True),
        sa.Column('tool_duration_ms', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('is_error', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('error_type', sa.String(length=100), nullable=True),
        sa.Column('parent_event_id', sa.UUID(), nullable=True),
        sa.Column('output_line_start', sa.Integer(), nullable=True),
        sa.Column('output_line_end', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['cc_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_event_id'], ['cc_session_events.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_cc_session_events_session_id', 'cc_session_events', ['session_id'], unique=False)
    op.create_index('ix_cc_session_events_event_type', 'cc_session_events', ['event_type'], unique=False)


def downgrade() -> None:
    # Drop cc_session_events table
    op.drop_index('ix_cc_session_events_event_type', table_name='cc_session_events')
    op.drop_index('ix_cc_session_events_session_id', table_name='cc_session_events')
    op.drop_table('cc_session_events')

    # Drop mode column from cc_sessions
    op.drop_column('cc_sessions', 'mode')

    # Drop enums (PostgreSQL only)
    op.execute("DROP TYPE IF EXISTS cceventtype")
    op.execute("DROP TYPE IF EXISTS ccsessionmode")
