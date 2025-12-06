#!/bin/bash
# Development Environment Setup Script
# Sets up linting, formatting, and pre-commit hooks

set -e

echo "🚀 Setting up FilmFind development environment..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Please create one first:"
    echo "   python -m venv venv"
    echo "   source venv/bin/activate  # On Windows: venv\\Scripts\\activate"
    exit 1
fi

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not activated. Please activate it first:"
    echo "   source venv/bin/activate  # On Windows: venv\\Scripts\\activate"
    exit 1
fi

echo "📦 Installing development dependencies..."
pip install -q ruff mypy pre-commit detect-secrets

echo "🔧 Setting up pre-commit hooks..."
pre-commit install

echo "🔍 Creating secrets baseline..."
detect-secrets scan --baseline .secrets.baseline

echo "✨ Running initial code formatting..."
ruff format app/

echo "🔎 Running linter..."
ruff check app/ --fix || true

echo ""
echo "✅ Development environment setup complete!"
echo ""
echo "📝 Available commands:"
echo "  ruff check app/          - Run linter"
echo "  ruff format app/         - Format code"
echo "  mypy app/                - Type check"
echo "  pre-commit run --all-files  - Run all hooks"
echo ""
echo "💡 Pre-commit hooks will now run automatically before each commit!"
