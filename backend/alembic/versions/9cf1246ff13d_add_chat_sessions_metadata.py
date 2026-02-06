"""add_chat_sessions_metadata

Revision ID: 9cf1246ff13d
Revises: 84dd7529fa0f
Create Date: 2026-01-21 09:11:31.098441

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '9cf1246ff13d'
down_revision = '84dd7529fa0f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('chat_sessions', sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=True))


def downgrade() -> None:
    op.drop_column('chat_sessions', 'metadata')