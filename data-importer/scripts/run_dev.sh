#!/bin/bash
set -e

echo "🚀 Starting Data Importer Development Server..."

# Load environment variables using python-dotenv
if [ -f .env ]; then
    echo "✅ Loading environment variables from .env"
else
    echo "⚠️ .env file not found. Using default settings."
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Create backups directory if it doesn't exist
mkdir -p backups

# Run database migrations
echo "🗄️ Running database migrations..."
rye run alembic upgrade head

echo "🌐 Starting FastAPI server..."
echo "📊 API Documentation: http://localhost:${PORT:-8000}/docs"
echo "📈 Alternative docs: http://localhost:${PORT:-8000}/redoc"
echo "🔍 Health check: http://localhost:${PORT:-8000}/health"
echo ""
echo "Press Ctrl+C to stop the server"

# Start the development server with auto-reload
rye run uvicorn src.data_importer.main:app \
    --reload \
    --host ${HOST:-0.0.0.0} \
    --port ${PORT:-8000} \
    --log-level ${LOG_LEVEL:-info}