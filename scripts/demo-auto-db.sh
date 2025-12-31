#!/bin/bash
# Demo script showing the new automatic database initialization

set -e

echo "🎯 AI Agent Framework - Automatic Database Initialization Demo"
echo "=============================================================="
echo ""

echo "🧹 Cleaning up any existing containers..."
docker-compose down -v
echo ""

echo "🔨 Building fresh Docker images..."
docker-compose build
echo ""

echo "🚀 Starting development environment with automatic database recreation..."
echo "   This will:"
echo "   1. Start PostgreSQL and Redis"
echo "   2. Start backend service"
echo "   3. Automatically wait for database to be ready"
echo "   4. Recreate database tables (RECREATE_DB=true in dev mode)"
echo "   5. Start the API server"
echo ""

docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

echo ""
echo "⏳ Waiting for services to fully initialize..."
sleep 30

echo ""
echo "📊 Checking service status..."
docker-compose ps

echo ""
echo "🔍 Checking backend logs for database initialization..."
docker-compose logs backend | tail -20

echo ""
echo "✅ Demo completed!"
echo ""
echo "🌐 Services available at:"
echo "   - API Server: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - Health Check: http://localhost:8000/health"
echo ""
echo "🧪 Run tests with: make test"
echo "🛑 Stop services with: docker-compose down"