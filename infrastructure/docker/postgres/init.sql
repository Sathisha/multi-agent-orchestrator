-- Initialize databases for AI Agent Framework

-- Create Keycloak database
CREATE DATABASE keycloak;

-- Create Superset database
CREATE DATABASE superset;

-- Create additional databases if needed
-- CREATE DATABASE ai_agent_framework_test;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================================
-- Chain Orchestration Tables
-- ============================================================================

-- Main chains table
CREATE TABLE IF NOT EXISTS chains (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    version VARCHAR(50) NOT NULL DEFAULT '1.0.0',
    category VARCHAR(255),
    tags JSONB DEFAULT '[]'::jsonb,
    input_schema JSONB DEFAULT '{}'::jsonb,
    output_schema JSONB DEFAULT '{}'::jsonb,
    execution_count INTEGER NOT NULL DEFAULT 0,
    last_executed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    is_deleted BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_chains_name ON chains(name);
CREATE INDEX IF NOT EXISTS ix_chains_status ON chains(status);
CREATE INDEX IF NOT EXISTS ix_chains_category ON chains(category);

-- Chain nodes table
CREATE TABLE IF NOT EXISTS chain_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chain_id UUID NOT NULL REFERENCES chains(id) ON DELETE CASCADE,
    node_id VARCHAR(255) NOT NULL,
    node_type VARCHAR(50) NOT NULL DEFAULT 'agent',
    agent_id UUID,
    label VARCHAR(255) NOT NULL,
    position_x FLOAT NOT NULL DEFAULT 0,
    position_y FLOAT NOT NULL DEFAULT 0,
    config JSONB DEFAULT '{}'::jsonb,
    order_index INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    is_deleted BOOLEAN DEFAULT FALSE,
    UNIQUE(chain_id, node_id)
);

CREATE INDEX IF NOT EXISTS ix_chain_nodes_chain_id ON chain_nodes(chain_id);
CREATE INDEX IF NOT EXISTS ix_chain_nodes_agent_id ON chain_nodes(agent_id);

-- Chain edges table
CREATE TABLE IF NOT EXISTS chain_edges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chain_id UUID NOT NULL REFERENCES chains(id) ON DELETE CASCADE,
    edge_id VARCHAR(255) NOT NULL,
    source_node_id VARCHAR(255) NOT NULL,
    target_node_id VARCHAR(255) NOT NULL,
    condition JSONB DEFAULT '{}'::jsonb,
    label VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    is_deleted BOOLEAN DEFAULT FALSE,
    UNIQUE(chain_id, edge_id)
);

CREATE INDEX IF NOT EXISTS ix_chain_edges_chain_id ON chain_edges(chain_id);

-- Chain executions table
CREATE TABLE IF NOT EXISTS chain_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chain_id UUID NOT NULL REFERENCES chains(id),
    execution_name VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    input_data JSONB DEFAULT '{}'::jsonb,
    output_data JSONB DEFAULT '{}'::jsonb,
    variables JSONB DEFAULT '{}'::jsonb,
    node_results JSONB DEFAULT '{}'::jsonb,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    current_node_id VARCHAR(255),
    completed_nodes JSONB DEFAULT '[]'::jsonb,
    error_message TEXT,
    error_details JSONB DEFAULT '{}'::jsonb,
    triggered_by UUID,
    correlation_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    is_deleted BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_chain_executions_chain_id ON chain_executions(chain_id);
CREATE INDEX IF NOT EXISTS ix_chain_executions_status ON chain_executions(status);

-- Chain execution logs table
CREATE TABLE IF NOT EXISTS chain_execution_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id UUID NOT NULL REFERENCES chain_executions(id) ON DELETE CASCADE,
    node_id VARCHAR(255),
    event_type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    level VARCHAR(20) NOT NULL DEFAULT 'INFO',
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    is_deleted BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_chain_execution_logs_execution_id ON chain_execution_logs(execution_id);
CREATE INDEX IF NOT EXISTS ix_chain_execution_logs_timestamp ON chain_execution_logs(timestamp);

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE ai_agent_framework TO postgres;
GRANT ALL PRIVILEGES ON DATABASE keycloak TO postgres;
GRANT ALL PRIVILEGES ON DATABASE superset TO postgres;
```