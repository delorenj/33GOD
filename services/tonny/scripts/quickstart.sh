#!/bin/bash
# Tonny Agent Quick Start Script

set -e

echo "🤖 Tonny Agent Quick Start"
echo "============================"
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Must run from tonny service directory"
    exit 1
fi

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "📦 Installing dependencies..."
uv sync

echo ""
echo "🔧 Checking environment configuration..."

if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo "✅ Created .env file. Please edit with your API keys:"
    echo "   - OPENAI_API_KEY or ANTHROPIC_API_KEY"
    echo "   - ELEVENLABS_API_KEY"
    echo "   - LETTA_BASE_URL (default: http://localhost:8283)"
    echo ""
    echo "Run: nano .env"
    exit 0
fi

echo "✅ .env file found"
echo ""

# Check RabbitMQ
echo "🐰 Checking RabbitMQ..."
if ! nc -z localhost 5672 2>/dev/null; then
    echo "⚠️  RabbitMQ not running on localhost:5672"
    echo "   Install: sudo apt install rabbitmq-server"
    echo "   Start: sudo systemctl start rabbitmq-server"
else
    echo "✅ RabbitMQ is running"
fi

echo ""

# Check Letta
echo "🧠 Checking Letta server..."
if ! nc -z localhost 8283 2>/dev/null; then
    echo "⚠️  Letta server not running on localhost:8283"
    echo "   Install: pip install letta"
    echo "   Start: letta server"
else
    echo "✅ Letta server is running"
fi

echo ""
echo "🚀 Starting Tonny Agent..."
echo ""

uv run python -m src.main
