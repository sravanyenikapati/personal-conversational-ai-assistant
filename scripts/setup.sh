#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# setup.sh — One-shot project setup script
# Run: bash scripts/setup.sh
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

echo "🤖 Personal AI Assistant — Setup"
echo "─────────────────────────────────"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✔ Python $PYTHON_VERSION detected"

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "→ Creating virtual environment..."
    python3 -m venv .venv
    echo "✔ Virtual environment created"
else
    echo "✔ Virtual environment already exists"
fi

# Activate
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip --quiet

# Install dependencies
echo "→ Installing dependencies..."
pip install -r requirements.txt --quiet
echo "✔ Dependencies installed"

# Copy .env if not present
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✔ .env created from .env.example"
    echo ""
    echo "⚠️  ACTION REQUIRED: Open .env and add your OPENAI_API_KEY"
else
    echo "✔ .env already exists"
fi

echo ""
echo "✅ Setup complete! Next steps:"
echo "   1. Activate venv:  source .venv/bin/activate  (Linux/macOS)"
echo "                      .venv\\Scripts\\activate     (Windows)"
echo "   2. Add your API key to .env"
echo "   3. Run: python main.py"
