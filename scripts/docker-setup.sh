#!/bin/bash

# AI Agent Framework Docker Setup Script

set -e

echo "🚀 Setting up AI Agent Framework with Docker..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ Created .env file. You may want to customize it for your environment."
fi

# Build Docker images
echo "🔨 Building Docker images..."
docker-compose build

# Start core services
echo "🚀 Starting core services (PostgreSQL, Redis)..."
docker-compose up -d postgres redis

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 15

# Run database migrations
echo "🗄️ Running database migrations..."
docker-compose exec -T backend alembic upgrade head

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Start the API server: make api"
echo "2. Run tests: make test"
echo "3. View API documentation: http://localhost:8000/docs"
echo ""
echo "Available commands:"
echo "- make help          # Show all available commands"
echo "- make start-all     # Start all services"
echo "- make test          # Run tests"
echo "- make logs          # View backend logs"
echo "- make shell         # Open shell in backend container"