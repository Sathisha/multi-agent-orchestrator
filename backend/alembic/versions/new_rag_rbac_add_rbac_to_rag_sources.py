"""Add RBAC fields to RAG sources

Revision ID: new_rag_rbac
Revises: afa6dbcedbc4
Create Date: 2026-01-21 22:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'new_rag_rbac'
down_revision = 'afa6dbcedbc4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_public column to rag_sources
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('rag_sources')]
    
    if 'is_public' not in columns:
        op.add_column('rag_sources', sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'))
        op.create_index(op.f('ix_rag_sources_is_public'), 'rag_sources', ['is_public'], unique=False)
    
    # Create rag_source_roles table
    existing_tables = inspector.get_table_names()
    if 'rag_source_roles' not in existing_tables:
        op.create_table('rag_source_roles',
            sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
            sa.Column('rag_source_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('access_type', sa.String(length=50), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.ForeignKeyConstraint(['rag_source_id'], ['rag_sources.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_rag_source_roles_rag_source_id'), 'rag_source_roles', ['rag_source_id'], unique=False)
        op.create_index(op.f('ix_rag_source_roles_role_id'), 'rag_source_roles', ['role_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_rag_source_roles_role_id'), table_name='rag_source_roles')
    op.drop_index(op.f('ix_rag_source_roles_rag_source_id'), table_name='rag_source_roles')
    op.drop_table('rag_source_roles')
    op.drop_index(op.f('ix_rag_sources_is_public'), table_name='rag_sources')
    op.drop_column('rag_sources', 'is_public')
