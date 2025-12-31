"""Complete schema with all tables

Revision ID: 001_complete_schema
Revises: 
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_complete_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables for the AI Agent Framework."""
    
    # Create enums first
    workflow_status_enum = postgresql.ENUM(
        'draft', 'active', 'inactive', 'archived',
        name='workflowstatus',
        create_type=False
    )
    workflow_status_enum.create(op.get_bind(), checkfirst=True)
    
    execution_status_enum = postgresql.ENUM(
        'pending', 'running', 'paused', 'completed', 'failed', 'cancelled', 'timeout',
        name='executionstatus',
        create_type=False
    )
    execution_status_enum.create(op.get_bind(), checkfirst=True)
    
    execution_priority_enum = postgresql.ENUM(
        'low', 'normal', 'high', 'critical',
        name='executionpriority',
        create_type=False
    )
    execution_priority_enum.create(op.get_bind(), checkfirst=True)
    
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_is_active', 'users', ['is_active'])

    # Create tenants table
    op.create_table('tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('primary_email', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, default='active'),
        sa.Column('plan', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        sa.Column('resource_limits', postgresql.JSONB(), nullable=False, default=sa.text("'{}'::jsonb")),
        sa.Column('branding', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        sa.Column('compliance_settings', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        sa.Column('subscription_starts_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('subscription_ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trial_ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.UniqueConstraint('slug')
    )
    op.create_index('ix_tenants_status', 'tenants', ['status'])
    op.create_index('ix_tenants_slug', 'tenants', ['slug'], unique=True)

    # Create tenant_users table
    op.create_table('tenant_users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(length=100), nullable=False, default='member'),
        sa.Column('status', sa.String(length=50), nullable=False, default='active'),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('invited_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id']),
        sa.UniqueConstraint('tenant_id', 'user_id', name='uq_tenant_user')
    )
    op.create_index('ix_tenant_users_tenant_id', 'tenant_users', ['tenant_id'])
    op.create_index('ix_tenant_users_user_id', 'tenant_users', ['user_id'])

    # Create permissions table
    op.create_table('permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('resource', sa.String(length=100), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('conditions', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.UniqueConstraint('name')
    )

    # Create roles table
    op.create_table('roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_system_role', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_default', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'])
    )
    op.create_index('ix_roles_tenant_id', 'roles', ['tenant_id'])

    # Create role_permissions association table
    op.create_table('role_permissions',
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id']),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id']),
        sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )

    # Create user_roles association table
    op.create_table('user_roles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id']),
        sa.PrimaryKeyConstraint('user_id', 'role_id')
    )

    # Create agents table
    op.create_table('agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(length=255), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('type', sa.String(length=50), nullable=False, default='conversational', index=True),
        sa.Column('status', sa.String(length=50), nullable=False, default='draft', index=True),
        sa.Column('version', sa.String(length=50), nullable=False, default='1.0'),
        sa.Column('config', postgresql.JSONB(), nullable=False, default=sa.text("'{}'::jsonb")),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('model_config', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        sa.Column('available_tools', postgresql.JSONB(), nullable=True, default=sa.text("'[]'::jsonb")),
        sa.Column('capabilities', postgresql.JSONB(), nullable=True, default=sa.text("'[]'::jsonb")),
        sa.Column('tags', postgresql.JSONB(), nullable=True, default=sa.text("'[]'::jsonb")),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'])
    )

    # Create workflows table
    op.create_table('workflows',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('tenant_id', sa.String(), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Basic workflow information
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.String(50), nullable=False, default='1.0.0'),
        
        # BPMN definition
        sa.Column('bpmn_xml', sa.Text(), nullable=False),
        sa.Column('process_definition_key', sa.String(255), nullable=False, index=True),
        
        # Workflow metadata
        sa.Column('status', workflow_status_enum, default='draft', nullable=False, index=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True, default=sa.text("'[]'::jsonb")),
        sa.Column('category', sa.String(255), nullable=True, index=True),
        
        # Configuration and variables
        sa.Column('input_schema', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        sa.Column('output_schema', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        sa.Column('default_variables', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        
        # Execution settings
        sa.Column('timeout_minutes', sa.Integer(), nullable=True),
        sa.Column('max_concurrent_executions', sa.Integer(), default=10, nullable=False),
        sa.Column('retry_policy', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        
        # Dependencies and requirements
        sa.Column('required_agents', postgresql.JSONB(), nullable=True, default=sa.text("'[]'::jsonb")),
        sa.Column('required_tools', postgresql.JSONB(), nullable=True, default=sa.text("'[]'::jsonb")),
        sa.Column('required_mcp_servers', postgresql.JSONB(), nullable=True, default=sa.text("'[]'::jsonb"))
    )
    
    # Create indexes for workflows
    op.create_index('ix_workflow_status_category', 'workflows', ['status', 'category'])
    op.create_index('ix_workflow_process_key_version', 'workflows', ['process_definition_key', 'version'])
    
    # Create workflow_executions table
    op.create_table('workflow_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('tenant_id', sa.String(), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Execution identification
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workflows.id'), nullable=False, index=True),
        sa.Column('execution_name', sa.String(255), nullable=True),
        
        # Execution status and timing
        sa.Column('status', execution_status_enum, default='pending', nullable=False, index=True),
        sa.Column('priority', execution_priority_enum, default='normal', nullable=False),
        
        sa.Column('started_at', sa.DateTime(), nullable=True, index=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        
        # Execution context
        sa.Column('input_data', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        sa.Column('output_data', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        sa.Column('variables', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        
        # Execution state and progress
        sa.Column('current_node_id', sa.String(255), nullable=True, index=True),
        sa.Column('completed_nodes', postgresql.JSONB(), nullable=True, default=sa.text("'[]'::jsonb")),
        sa.Column('active_nodes', postgresql.JSONB(), nullable=True, default=sa.text("'[]'::jsonb")),
        
        # Error handling and debugging
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        sa.Column('retry_count', sa.Integer(), default=0, nullable=False),
        
        # Execution metadata
        sa.Column('triggered_by', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('trigger_type', sa.String(50), nullable=True),
        sa.Column('correlation_id', sa.String(255), nullable=True, index=True)
    )
    
    # Create indexes for workflow_executions
    op.create_index('ix_execution_status_started', 'workflow_executions', ['status', 'started_at'])
    op.create_index('ix_execution_workflow_status', 'workflow_executions', ['workflow_id', 'status'])
    op.create_index('ix_execution_correlation_id', 'workflow_executions', ['correlation_id'])
    
    # Create execution_logs table
    op.create_table('execution_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('tenant_id', sa.String(), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Log identification
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workflow_executions.id'), nullable=False, index=True),
        sa.Column('node_id', sa.String(255), nullable=False, index=True),
        
        # Log entry details
        sa.Column('event_type', sa.String(50), nullable=False, index=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('level', sa.String(20), default='INFO', nullable=False),
        
        # Timing information
        sa.Column('timestamp', sa.DateTime(), default=sa.text('CURRENT_TIMESTAMP'), nullable=False, index=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        
        # Contextual data
        sa.Column('input_data', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        sa.Column('output_data', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        sa.Column('variables', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        
        # Agent and tool information
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('tool_name', sa.String(255), nullable=True, index=True),
        
        # Error information
        sa.Column('error_code', sa.String(50), nullable=True),
        sa.Column('error_details', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        sa.Column('stack_trace', sa.Text(), nullable=True)
    )
    
    # Create indexes for execution_logs
    op.create_index('ix_log_execution_timestamp', 'execution_logs', ['execution_id', 'timestamp'])
    op.create_index('ix_log_node_event_type', 'execution_logs', ['node_id', 'event_type'])
    op.create_index('ix_log_level_timestamp', 'execution_logs', ['level', 'timestamp'])

    # Create audit_logs table
    op.create_table('audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=False),
        sa.Column('resource_id', sa.String(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('old_values', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        sa.Column('new_values', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, default=sa.text("'{}'::jsonb")),
        sa.Column('success', sa.Boolean(), nullable=False, default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'])
    )
    op.create_index('ix_audit_logs_tenant_id', 'audit_logs', ['tenant_id'])
    op.create_index('ix_audit_logs_event_type', 'audit_logs', ['event_type'])
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])


def downgrade() -> None:
    """Drop all tables."""
    
    # Drop tables in reverse order
    op.drop_index('ix_audit_logs_timestamp', table_name='audit_logs')
    op.drop_index('ix_audit_logs_event_type', table_name='audit_logs')
    op.drop_index('ix_audit_logs_tenant_id', table_name='audit_logs')
    op.drop_table('audit_logs')
    
    op.drop_index('ix_log_level_timestamp', table_name='execution_logs')
    op.drop_index('ix_log_node_event_type', table_name='execution_logs')
    op.drop_index('ix_log_execution_timestamp', table_name='execution_logs')
    op.drop_table('execution_logs')
    
    op.drop_index('ix_execution_correlation_id', table_name='workflow_executions')
    op.drop_index('ix_execution_workflow_status', table_name='workflow_executions')
    op.drop_index('ix_execution_status_started', table_name='workflow_executions')
    op.drop_table('workflow_executions')
    
    op.drop_index('ix_workflow_process_key_version', table_name='workflows')
    op.drop_index('ix_workflow_status_category', table_name='workflows')
    op.drop_table('workflows')
    
    op.drop_table('agents')
    
    op.drop_table('user_roles')
    op.drop_table('role_permissions')
    
    op.drop_index('ix_roles_tenant_id', table_name='roles')
    op.drop_table('roles')
    
    op.drop_table('permissions')
    
    op.drop_index('ix_tenant_users_user_id', table_name='tenant_users')
    op.drop_index('ix_tenant_users_tenant_id', table_name='tenant_users')
    op.drop_table('tenant_users')
    
    op.drop_index('ix_tenants_slug', table_name='tenants')
    op.drop_index('ix_tenants_status', table_name='tenants')
    op.drop_table('tenants')
    
    op.drop_index('ix_users_is_active', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS executionpriority')
    op.execute('DROP TYPE IF EXISTS executionstatus')
    op.execute('DROP TYPE IF EXISTS workflowstatus')