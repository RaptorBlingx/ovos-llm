#!/bin/bash
# ============================================================================
# OVOS-EnMS - Zero-Touch Setup Script
# ============================================================================
set -e

echo "============================================================================"
echo "  OVOS-EnMS Voice Assistant Setup"
echo "============================================================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: OVOS connects to EnMS via Docker network"
    echo "   Default: http://enms-analytics:8001/api/v1 (container name)"
    echo "   Both containers must be on 'enms-network'"
    echo ""
else
    echo "✅ .env file already exists"
    echo ""
fi

# Build and start services
echo "🐳 Building Docker images (this may take a few minutes)..."
docker compose build

echo ""
echo "🚀 Starting OVOS services..."
docker compose up -d

echo ""
echo "⏳ Waiting for services to be ready (20 seconds)..."
sleep 20

echo ""
echo "============================================================================"
echo "  ✅ OVOS-EnMS Setup Complete!"
echo "============================================================================"
echo ""
echo "Access the voice assistant:"
echo ""
echo "  🎤 REST Bridge API:  http://localhost:5000"
echo "  📊 Test Endpoint:    http://localhost:5000/test"
echo "  🔍 Health Check:     http://localhost:5000/health"
echo ""
echo "Test voice queries:"
echo ""
echo "  curl -X POST http://localhost:5000/query \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"text\": \"What is the status of Compressor-1?\"}'"
echo ""
echo "Or use the test script:"
echo "  docker compose exec ovos-enms python3 /app/enms-ovos-skill/scripts/test_skill_chat.py \"Your query\""
echo ""
echo "Useful commands:"
echo "  • View logs:         docker compose logs -f"
echo "  • Stop services:     docker compose down"
echo "  • Restart services:  docker compose restart"
echo "  • Check status:      docker compose ps"
echo ""
echo "For more information, see README.md"
echo "============================================================================"
