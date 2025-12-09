#!/bin/bash

# AI SRE Agent Setup Script
# Handles virtual environment logic and Python 3.11 requirement.

set -e

echo "🚀 Setting up AI SRE Agent Environment..."

# 1. Check for Python 3.11
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD=python3.11
    echo "✅ Found Python 3.11: $(which python3.11)"
else
    echo "❌ Error: Python 3.11 is required but not found."
    echo "   Please install it (e.g., 'brew install python@3.11' on macOS)."
    exit 1
fi

# 2. Upgrade npm dependencies (MCP Server)
if [ -d "node_modules" ]; then
    echo "📦 Node modules found."
else
    echo "📦 Installing Node dependencies (MCP Server)..."
    npm install kubernetes-mcp-server
fi

# 3. Create Virtual Environment
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment in $VENV_DIR..."
    $PYTHON_CMD -m venv $VENV_DIR
else
    echo "✅ Virtual environment exists."
fi

# 4. Activate and Install
echo "🔌 Activating .venv..."
source $VENV_DIR/bin/activate

echo "⬇️  Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 5. Check Environment Variables
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating one from .env.example..."
    cp .env.example .env
    echo "❗ ACTION REQUIRED: Please edit .env and add your OPENAI_API_KEY."
else
    # Check if API key is the placeholder
    if grep -q "sk-..." ".env"; then
        echo "❗ WARNING: It looks like .env still has the placeholder API key."
        echo "   Please edit .env and add your actual OpenAI API Key."
    else
        echo "✅ .env file found."
    fi
fi

# 6. Final Instructions
echo ""
echo "🎉 Setup Complete!"
echo ""
echo "To run the agent:"
echo "  source .venv/bin/activate"
echo "  python main.py daemon"
echo ""
echo "Or use the shortcut:"
echo "  ./setup.sh --run"
echo ""

if [ "$1" == "--run" ]; then
    echo "🚀 Launching Agent..."
    python main.py daemon
fi
