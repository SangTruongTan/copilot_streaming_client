#!/bin/bash
# Quick start script for the Copilot Streaming Web Demo

set -e

echo "🚀 Starting Copilot Streaming Web Demo..."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or later."
    exit 1
fi

# Check if copilot CLI is installed
if ! command -v copilot &> /dev/null; then
    echo "❌ Copilot CLI is not installed. Please install it first:"
    echo "   https://github.com/github/copilot.vim#installation"
    exit 1
fi

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✓ Python $python_version"

# Check if dependencies are installed
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo ""
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

echo ""
echo "✓ All dependencies installed"
echo ""
echo "🌐 Starting web server..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   Open your browser to: http://localhost:8000"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start the app
python3 app.py
