"""Add comprehensive audit system

Revision ID: 003
Revises: 002_add_tool_mcp_tables
Create Date: 2024-12-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002_add_tool_mcp_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add comprehensive audit system tables and indexes."""
    
    # Create audit_logs table if it doesn't exist
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            
            -- Event identification
            event_type VARCHAR(100) NOT NULL,
            event_id VARCHAR(255) NOT NULL UNIQUE,
            correlation_id VARCHAR(255),
            
            -- Event timing
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            
            -- Actor information
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            username VARCHAR(255),
            session_id VARCHAR(255),
            
            -- Source information
            source_ip INET,
            user_agent TEXT,
            source_service VARCHAR(255),
            
            -- Target information
            resource_type VARCHAR(100),
            resource_id UUID,
            resource_name VARCHAR(255),
            
            -- Action details
            action VARCHAR(100) NOT NULL,
            outcome VARCHAR(20) NOT NULL,
            severity VARCHAR(20) DEFAULT 'low' NOT NULL,
            
            -- Event description
            message TEXT NOT NULL,
            details JSONB DEFAULT '{}',
            
            -- Request/Response data
            request_data JSONB DEFAULT '{}',
            response_data JSONB DEFAULT '{}',
            
            -- Error information
            error_code VARCHAR(50),
            error_message TEXT,
            
            -- Compliance and retention
            retention_date TIMESTAMP WITH TIME ZONE,
            compliance_tags JSONB DEFAULT '[]',
            
            -- Integrity verification
            checksum VARCHAR(64),
            signature TEXT,
            
            -- Timestamps
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
        );
    """)
    
    # Create indexes for performance
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_audit_logs_tenant_id ON audit_logs(tenant_id);
        CREATE INDEX IF NOT EXISTS ix_audit_logs_event_type ON audit_logs(event_type);
        CREATE INDEX IF NOT EXISTS ix_audit_logs_event_id ON audit_logs(event_id);
        CREATE INDEX IF NOT EXISTS ix_audit_logs_correlation_id ON audit_logs(correlation_id);
        CREATE INDEX IF NOT EXISTS ix_audit_logs_timestamp ON audit_logs(timestamp);
        CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id ON audit_logs(user_id);
        CREATE INDEX IF NOT EXISTS ix_audit_logs_username ON audit_logs(username);
        CREATE INDEX IF NOT EXISTS ix_audit_logs_session_id ON audit_logs(session_id);
        CREATE INDEX IF NOT EXISTS ix_audit_logs_source_ip ON audit_logs(source_ip);
        CREATE INDEX IF NOT EXISTS ix_audit_logs_source_service ON audit_logs(source_service);
        CREATE INDEX IF NOT EXISTS ix_audit_logs_resource_type ON audit_logs(resource_type);
        CREATE INDEX IF NOT EXISTS ix_audit_logs_resource_id ON audit_logs(resource_id);
        CREATE INDEX IF NOT EXISTS ix_audit_logs_resource_name ON audit_logs(resource_name);
        CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs(action);
        CREATE INDEX IF NOT EXISTS ix_audit_logs_outcome ON audit_logs(outcome);
        CREATE INDEX IF NOT EXISTS ix_audit_logs_severity ON audit_logs(severity);
        CREATE INDEX IF NOT EXISTS ix_audit_logs_retention_date ON audit_logs(retention_date);
    """)
    
    # Create composite indexes for common query patterns
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_audit_timestamp_event_type ON audit_logs(timestamp, event_type);
        CREATE INDEX IF NOT EXISTS ix_audit_user_timestamp ON audit_logs(user_id, timestamp);
        CREATE INDEX IF NOT EXISTS ix_audit_resource_action ON audit_logs(resource_type, action);
        CREATE INDEX IF NOT EXISTS ix_audit_outcome_severity ON audit_logs(outcome, severity);
        CREATE INDEX IF NOT EXISTS ix_audit_source_ip_timestamp ON audit_logs(source_ip, timestamp);
    """)
    
    # Create GIN indexes for JSONB columns
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_audit_compliance_tags ON audit_logs USING GIN(compliance_tags);
        CREATE INDEX IF NOT EXISTS ix_audit_details ON audit_logs USING GIN(details);
    """)
    
    # Add updated_at trigger
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        
        DROP TRIGGER IF EXISTS update_audit_logs_updated_at ON audit_logs;
        CREATE TRIGGER update_audit_logs_updated_at
            BEFORE UPDATE ON audit_logs
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    """Remove audit system tables and indexes."""
    
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_audit_logs_updated_at ON audit_logs;")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
    
    # Drop table (indexes will be dropped automatically)
    op.execute("DROP TABLE IF EXISTS audit_logs;")