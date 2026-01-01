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
    echo "🔄 Initializing database with Alembic..."
    
    python3 init_db.py
    
    if [ $? -eq 0 ]; then
        echo "✅ Database initialization completed successfully"
    else
        echo "❌ Database initialization failed"
        exit 1
    fi
}

# Function to run database migrations (if needed in future)
run_migrations() {
    echo "🔄 Running Alembic migrations..."
    alembic upgrade head
    if [ $? -eq 0 ]; then
        echo "✅ Alembic migrations completed successfully"
    else
        echo "❌ Alembic migrations failed"
        exit 1
    fi
}

# Main execution flow
main() {
    echo "🏗️  Environment: ${ENVIRONMENT:-development}"
    echo "🐛 Debug mode: ${DEBUG:-false}"
    
    # Wait for database to be ready
    wait_for_db
    
    # Initialize database (now runs Alembic)
    init_database
    
    # Seed data if RECREATE_DB is true (or always in dev)
    if [ "$RECREATE_DB" = "true" ] || [ "$ENVIRONMENT" = "development" ]; then
        echo "🌱 Seeding database..."
        python /app/seed_data.py
        if [ $? -eq 0 ]; then
            echo "✅ Database seeding completed successfully"
        else
            echo "❌ Database seeding failed"
            exit 1
        fi
    fi
    
    echo "🎯 Starting application with command: $@"
    
    # Execute the main command
    exec "$@"
}


# Handle signals for graceful shutdown
trap 'echo "🛑 Received shutdown signal, stopping..."; exit 0' SIGTERM SIGINT

# Run main function with all arguments
main "$@"