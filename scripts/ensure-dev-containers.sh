#!/bin/bash
# Ensure development containers are running before running tests

set -e

echo "🔍 Checking if development containers are running..."

# Check if postgres container is running
if ! docker ps --format "table {{.Names}}" | grep -q "ai-agent-framework-postgres"; then
    echo "⚠️  PostgreSQL container not running. Starting development containers..."
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d postgres redis
    echo "⏳ Waiting for containers to be healthy..."
    sleep 15
else
    echo "✅ PostgreSQL container is running"
fi

# Check if redis container is running
if ! docker ps --format "table {{.Names}}" | grep -q "ai-agent-framework-redis"; then
    echo "⚠️  Redis container not running. Starting development containers..."
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d postgres redis
    echo "⏳ Waiting for containers to be healthy..."
    sleep 15
else
    echo "✅ Redis container is running"
fi

# Check if backend container is running (needed for tests)
if ! docker ps --format "table {{.Names}}" | grep -q "ai-agent-framework-backend"; then
    echo "⚠️  Backend container not running. Starting backend with auto DB initialization..."
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d backend
    echo "⏳ Waiting for backend to initialize database and be ready..."
    sleep 20
else
    echo "✅ Backend container is running"
fi

echo "✅ Development containers are ready for testing"