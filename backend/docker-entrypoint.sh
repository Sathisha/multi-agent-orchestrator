#!/bin/bash
set -e

echo "🚀 Starting AI Agent Framework Backend..."

# Function to wait for database to be ready
wait_for_db() {
    echo "⏳ Waiting for PostgreSQL to be ready..."
    
    # Extract database connection details from DATABASE_URL
    # Format: postgresql://user:password@host:port/database
    DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    DB_USER=$(echo $DATABASE_URL | sed -n 's/.*\/\/\([^:]*\):.*/\1/p')
    DB_NAME=$(echo $DATABASE_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')
    
    # Default values if extraction fails
    DB_HOST=${DB_HOST:-postgres}
    DB_PORT=${DB_PORT:-5432}
    DB_USER=${DB_USER:-postgres}
    DB_NAME=${DB_NAME:-ai_agent_framework}
    
    echo "📡 Checking database connection: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
    
    # Wait for PostgreSQL to be ready (max 60 seconds)
    for i in {1..60}; do
        if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
            echo "✅ PostgreSQL is ready!"
            return 0
        fi
        echo "⏳ Waiting for PostgreSQL... (attempt $i/60)"
        sleep 1
    done
    
    echo "❌ PostgreSQL is not ready after 60 seconds"
    exit 1
}

# Function to initialize database
init_database() {
    echo "🔄 Initializing database..."
    
    # Check if we should recreate the database
    if [ "$RECREATE_DB" = "true" ] || [ "$RECREATE_DB" = "1" ]; then
        echo "🗑️  Recreating database tables..."
        python3 init_db.py --recreate
    else
        echo "📋 Creating database tables if they don't exist..."
        python3 init_db.py
    fi
    
    if [ $? -eq 0 ]; then
        echo "✅ Database initialization completed successfully"
    else
        echo "❌ Database initialization failed"
        exit 1
    fi
}

# Function to run database migrations (if needed in future)
run_migrations() {
    # This is a placeholder for future Alembic migrations
    # Currently disabled during development phase
    if [ "$ENABLE_MIGRATIONS" = "true" ]; then
        echo "🔄 Running database migrations..."
        # alembic upgrade head
        echo "⚠️  Migrations are disabled during development phase"
    fi
}

# Main execution flow
main() {
    echo "🏗️  Environment: ${ENVIRONMENT:-development}"
    echo "🐛 Debug mode: ${DEBUG:-false}"
    
    # Wait for database to be ready
    wait_for_db
    
    # Initialize database
    init_database
    
    # Run migrations if enabled
    run_migrations
    
    echo "🎯 Starting application with command: $@"
    
    # Execute the main command
    exec "$@"
}

# Handle signals for graceful shutdown
trap 'echo "🛑 Received shutdown signal, stopping..."; exit 0' SIGTERM SIGINT

# Run main function with all arguments
main "$@"