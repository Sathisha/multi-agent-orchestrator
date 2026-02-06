"""add_mcp_server_fields

Revision ID: ae3459876543
Revises: 551e8ec1beee
Create Date: 2026-01-20 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ae3459876543'
down_revision = '551e8ec1beee'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to mcp_servers
    op.add_column('mcp_servers', sa.Column('protocol', sa.String(length=50), server_default='websocket', nullable=True))
    op.add_column('mcp_servers', sa.Column('env_vars', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=True))
    op.add_column('mcp_servers', sa.Column('resources', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=True))
    op.add_column('mcp_servers', sa.Column('prompts', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=True))
    op.add_column('mcp_servers', sa.Column('server_info', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=True))


def downgrade() -> None:
    op.drop_column('mcp_servers', 'server_info')
    op.drop_column('mcp_servers', 'prompts')
    op.drop_column('mcp_servers', 'resources')
    op.drop_column('mcp_servers', 'env_vars')
    op.drop_column('mcp_servers', 'protocol')
