-- Initialize databases for AI Agent Framework

-- Create Keycloak database
CREATE DATABASE keycloak;

-- Create Superset database
CREATE DATABASE superset;

-- Create additional databases if needed
-- CREATE DATABASE ai_agent_framework_test;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE ai_agent_framework TO postgres;
GRANT ALL PRIVILEGES ON DATABASE keycloak TO postgres;
GRANT ALL PRIVILEGES ON DATABASE superset TO postgres;