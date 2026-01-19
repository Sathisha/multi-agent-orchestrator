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

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE ai_agent_framework TO postgres;
GRANT ALL PRIVILEGES ON DATABASE keycloak TO postgres;
GRANT ALL PRIVILEGES ON DATABASE superset TO postgres;
