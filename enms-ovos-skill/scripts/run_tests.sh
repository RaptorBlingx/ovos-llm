#!/bin/bash
# Quick Test Runner for OVOS EnMS Skill
# Week 6 Days 36-37 Unit Testing

set -e

cd "$(dirname "$0")/.."

echo "======================================"
echo "🧪 OVOS EnMS SKILL TEST SUITE"
echo "======================================"
echo ""

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️  Virtual environment not found. Creating..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    pip install pytest pytest-asyncio pytest-cov pytest-mock hypothesis
fi

echo ""
echo "📊 Running test suite..."
echo ""

# Temporarily rename __init__.py to avoid import issues
if [ -f "__init__.py" ]; then
    mv __init__.py __init__.py.skill
fi

# Run tests with coverage
pytest tests/ \
    --cov=lib \
    --cov-report=html \
    --cov-report=term \
    -v \
    -m "not slow" \
    --tb=short

# Restore __init__.py
if [ -f "__init__.py.skill" ]; then
    mv __init__.py.skill __init__.py
fi

echo ""
echo "======================================"
echo "✅ Test suite complete!"
echo "======================================"
echo ""
echo "📄 Coverage report: htmlcov/index.html"
echo ""
echo "Quick stats:"
pytest tests/ --co -q | wc -l | xargs -I {} echo "  Total tests: {}"
echo ""
