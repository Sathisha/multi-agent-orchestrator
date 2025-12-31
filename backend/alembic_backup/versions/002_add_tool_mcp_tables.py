"""Add tool and MCP server tables

Revision ID: 002_add_tool_mcp_tables
Revises: 001_complete_schema
Create Date: 2024-12-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_add_tool_mcp_tables'
down_revision = '001_complete_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add tool and MCP server tables."""
    
    # Create enums for tools and MCP servers
    tool_type_enum = postgresql.ENUM(
        'custom', 'mcp_server', 'builtin',
        name='tooltype',
        create_type=False
    )
    tool_type_enum.create(op.get_bind(), checkfirst=True)
    
    tool_status_enum = postgresql.ENUM(
        'draft', 'active', 'inactive', 'deprecated', 'error',
        name='toolstatus',
        create_type=False
    )
    tool_status_enum.create(op.get_bind(), checkfirst=True)
    
    mcp_server_status_enum = postgresql.ENUM(
        'disconnected', 'connecting', 'connected', 'error', 'authentication_failed',
        name='mcpserverstatus',
        create_type=False
    )
    mcp_server_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Create MCP servers table
    op.create_table('mcp_servers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Basic server information
        sa.Column('name', sa.String(length=255), nullable=False, index=True),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.String(length=50), nullable=True),
        
        # Connection configuration
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('protocol', sa.String(length=50), nullable=False, default='http'),
        sa.Column('port', sa.Integer(), nullable=True),
        
        # Authentication configuration
        sa.Column('auth_type', sa.String(length=50), nullable=True),
        sa.Column('auth_config', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        
        # Server status and health
        sa.Column('status', mcp_server_status_enum, nullable=False, default='disconnected'),
        sa.Column('last_connected_at', sa.DateTime(), nullable=True),
        sa.Column('last_health_check_at', sa.DateTime(), nullable=True),
        sa.Column('health_check_interval', sa.Integer(), nullable=False, default=300),
        
        # Server capabilities
        sa.Column('supported_protocols', postgresql.JSONB(), nullable=True, default=sa.text("'[]'::jsonb")),
        sa.Column('server_info', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        sa.Column('capabilities', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        
        # Connection settings
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, default=30),
        sa.Column('max_retries', sa.Integer(), nullable=False, default=3),
        sa.Column('retry_delay', sa.Integer(), nullable=False, default=5),
        
        # Server metadata
        sa.Column('tags', postgresql.JSONB(), nullable=True, default=sa.text("'[]'::jsonb")),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('vendor', sa.String(length=255), nullable=True),
        sa.Column('documentation_url', sa.String(length=500), nullable=True),
        
        # Error tracking
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('error_count', sa.Integer(), nullable=False, default=0),
        sa.Column('last_error_at', sa.DateTime(), nullable=True),
        
        # Usage statistics
        sa.Column('total_requests', sa.Integer(), nullable=False, default=0),
        sa.Column('successful_requests', sa.Integer(), nullable=False, default=0),
        sa.Column('failed_requests', sa.Integer(), nullable=False, default=0),
        sa.Column('average_response_time', sa.Integer(), nullable=True),
        
        # Constraints
        sa.UniqueConstraint('name', 'tenant_id', name='uq_mcp_server_name_tenant')
    )
    
    # Create tools table
    op.create_table('tools',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Basic tool information
        sa.Column('name', sa.String(length=255), nullable=False, index=True),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.String(length=50), nullable=False, default='1.0.0'),
        
        # Tool type and status
        sa.Column('tool_type', tool_type_enum, nullable=False, default='custom'),
        sa.Column('status', tool_status_enum, nullable=False, default='draft'),
        
        # Tool implementation
        sa.Column('code', sa.Text(), nullable=True),
        sa.Column('entry_point', sa.String(length=255), nullable=True),
        sa.Column('requirements', postgresql.JSONB(), nullable=True, default=sa.text("'[]'::jsonb")),
        
        # Tool interface definition
        sa.Column('input_schema', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        sa.Column('output_schema', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        sa.Column('parameters', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        
        # Tool metadata
        sa.Column('tags', postgresql.JSONB(), nullable=True, default=sa.text("'[]'::jsonb")),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('author', sa.String(length=255), nullable=True),
        sa.Column('documentation_url', sa.String(length=500), nullable=True),
        
        # Runtime configuration
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, default=30),
        sa.Column('max_retries', sa.Integer(), nullable=False, default=3),
        sa.Column('environment_variables', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        
        # Tool capabilities and permissions
        sa.Column('capabilities', postgresql.JSONB(), nullable=True, default=sa.text("'[]'::jsonb")),
        sa.Column('required_permissions', postgresql.JSONB(), nullable=True, default=sa.text("'[]'::jsonb")),
        
        # MCP server reference
        sa.Column('mcp_server_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('mcp_servers.id'), nullable=True),
        sa.Column('mcp_tool_name', sa.String(length=255), nullable=True),
        
        # Validation and testing
        sa.Column('validation_schema', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        sa.Column('test_cases', postgresql.JSONB(), nullable=True, default=sa.text("'[]'::jsonb")),
        sa.Column('last_validated_at', sa.DateTime(), nullable=True),
        sa.Column('validation_errors', postgresql.JSONB(), nullable=True, default=sa.text("'[]'::jsonb")),
        
        # Usage statistics
        sa.Column('usage_count', sa.Integer(), nullable=False, default=0),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('average_execution_time', sa.Integer(), nullable=True),
        
        # Constraints
        sa.UniqueConstraint('name', 'tenant_id', name='uq_tool_name_tenant')
    )
    
    # Create indexes for better performance
    op.create_index('idx_mcp_servers_status', 'mcp_servers', ['status'])
    op.create_index('idx_mcp_servers_category', 'mcp_servers', ['category'])
    op.create_index('idx_mcp_servers_last_connected', 'mcp_servers', ['last_connected_at'])
    
    op.create_index('idx_tools_type_status', 'tools', ['tool_type', 'status'])
    op.create_index('idx_tools_category', 'tools', ['category'])
    op.create_index('idx_tools_mcp_server', 'tools', ['mcp_server_id'])
    op.create_index('idx_tools_last_used', 'tools', ['last_used_at'])


def downgrade() -> None:
    """Drop tool and MCP server tables."""
    
    # Drop indexes
    op.drop_index('idx_tools_last_used', table_name='tools')
    op.drop_index('idx_tools_mcp_server', table_name='tools')
    op.drop_index('idx_tools_category', table_name='tools')
    op.drop_index('idx_tools_type_status', table_name='tools')
    
    op.drop_index('idx_mcp_servers_last_connected', table_name='mcp_servers')
    op.drop_index('idx_mcp_servers_category', table_name='mcp_servers')
    op.drop_index('idx_mcp_servers_status', table_name='mcp_servers')
    
    # Drop tables
    op.drop_table('tools')
    op.drop_table('mcp_servers')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS mcpserverstatus')
    op.execute('DROP TYPE IF EXISTS toolstatus')
    op.execute('DROP TYPE IF EXISTS tooltype')