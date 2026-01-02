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
            
            # Additional check: verify we can actually connect and query
            if PGPASSWORD=$POSTGRES_PASSWORD psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" >/dev/null 2>&1; then
                echo "✅ Database connection verified!"
                return 0
            fi
        fi
        echo "⏳ Waiting for PostgreSQL... (attempt $i/60)"
        sleep 1
    done
    
    echo "❌ PostgreSQL is not ready after 60 seconds"
    exit 1
}

# Function to initialize database
init_database() {
    echo "🔄 Initializing database tables..."
    
    python3 init_db.py
    
    if [ $? -eq 0 ]; then
        echo "✅ Database initialization completed successfully"
    else
        echo "❌ Database initialization failed"
        exit 1
    fi
}

# Function to verify tables exist
verify_tables() {
    echo "🔍 Verifying database tables exist..."
    
    # Use Python to check if tables exist
    python3 -c "
import asyncio
from shared.database.connection import async_engine
from sqlalchemy import text

async def check_tables():
    async with async_engine.connect() as conn:
        result = await conn.execute(text(\"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'\"))
        count = result.scalar()
        return count > 0

result = asyncio.run(check_tables())
exit(0 if result else 1)
" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "✅ Database tables verified"
        return 0
    else
        echo "⚠️  Could not verify tables (may not exist yet)"
        return 1
    fi
}

# Main execution flow
main() {
    echo "🏗️  Environment: ${ENVIRONMENT:-development}"
    echo "🐛 Debug mode: ${DEBUG:-false}"
    echo "🔄 Recreate DB: ${RECREATE_DB:-false}"
    
    # Wait for database to be ready
    wait_for_db
    
    # Give database a moment to fully initialize
    echo "⏳ Waiting 2 seconds for database to fully initialize..."
    sleep 2
    
    # Initialize database tables
    init_database
    
    # Verify tables exist before seeding
    if verify_tables; then
        # Seed data if RECREATE_DB is true (or always in dev)
        if [ "$RECREATE_DB" = "true" ] || [ "$ENVIRONMENT" = "development" ]; then
            echo "🌱 Seeding database..."
            python3 /app/seed_data.py
            
            if [ $? -eq 0 ]; then
                echo "✅ Database seeding completed successfully"
            else
                echo "⚠️  Database seeding failed (continuing anyway)"
                # Don't exit on seeding failure - let the app start
            fi
        else
            echo "ℹ️  Skipping database seeding (RECREATE_DB=false and ENVIRONMENT!=development)"
        fi
    else
        echo "⚠️  Skipping seeding - tables not verified"
    fi
    
    echo "🛡️  Running pre-flight check..."
    if ! python3 -c "import main"; then
        echo "❌ Pre-flight check failed! Application code has errors."
        exit 1
    fi
    echo "✅ Pre-flight check passed"

    echo "🎯 Starting application with command: $@"
    
    # Execute the main command
    exec "$@"
}


# Handle signals for graceful shutdown
trap 'echo "🛑 Received shutdown signal, stopping..."; exit 0' SIGTERM SIGINT

# Run main function with all arguments
main "$@"