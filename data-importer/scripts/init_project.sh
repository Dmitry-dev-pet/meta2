#!/bin/bash
set -e

echo "🚀 Initializing Data Importer Project with Rye..."

# Check if Rye is installed
if ! command -v rye &> /dev/null; then
    echo "❌ Rye is not installed. Please install Rye first:"
    echo "curl -sSf https://rye.astral.sh/get | bash"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ pyproject.toml not found. Please run this script from the project root."
    exit 1
fi

echo "📦 Installing dependencies..."
rye sync

# Create necessary directories if they don't exist
echo "📁 Creating project structure..."
mkdir -p src/data_importer/{config,models,schemas,services,api,db,utils}
mkdir -p src/data_importer/api/endpoints
mkdir -p tests/{test_models,test_services,test_api,test_utils}
mkdir -p backups
mkdir -p logs

# Create .env from .env.example if it doesn't exist
if [ ! -f .env ]; then
    echo "⚙️ Creating .env from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env file with your actual configuration values."
fi

# Initialize Alembic if not already initialized
if [ ! -d "migrations" ]; then
    echo "🗄️ Initializing Alembic migrations..."
    rye run alembic init migrations

    # Configure Alembic to work with our project
    echo "⚙️ Configuring Alembic..."
    # The env.py and alembic.ini should already be configured
fi

# Create initial migration if no migrations exist
if [ ! "$(ls -A migrations/versions)" ]; then
    echo "📋 Creating initial database migration..."
    rye run alembic revision --autogenerate -m "Initial migration"
fi

# Run database migrations
echo "🗄️ Running database migrations..."
rye run alembic upgrade head

# Set up pre-commit hooks
echo "🔧 Setting up pre-commit hooks..."
rye run pre-commit install

echo "✅ Project initialization complete!"
echo ""
echo "🎯 Next steps:"
echo "1. Edit .env file with your actual Google Sheets credentials"
echo "2. Run 'rye run dev' to start the development server"
echo "3. Visit http://localhost:8000/docs for API documentation"
echo "4. Create your first data model in src/data_importer/models/"
echo "5. Generate migration: rye run alembic revision --autogenerate -m 'your message'"
echo "6. Run tests: rye run pytest"