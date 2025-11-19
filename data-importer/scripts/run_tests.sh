#!/bin/bash
set -e

echo "🧪 Running Data Importer Tests..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set test database URL (in-memory SQLite for fast tests)
export DATABASE_URL="sqlite+aiosqlite:///:memory:"
export ENVIRONMENT="testing"

echo "📊 Running tests with coverage..."
echo "Test database: In-memory SQLite"
echo "Environment: Testing"
echo ""

# Run tests with coverage
rye run pytest tests/ \
    -v \
    --cov=src/data_importer \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-fail-under=80 \
    --tb=short

echo ""
echo "✅ Tests completed!"
echo "📈 Coverage report generated in htmlcov/index.html"
echo "📝 To view coverage: open htmlcov/index.html"