#!/bin/bash
# MedWave Ad Tracker — One-click startup
# Just double-click this file or run: bash start.sh

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║       MedWave Ad Tracker             ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# Go to the script's directory
cd "$(dirname "$0")"

# Check Python is installed
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "  Python is not installed."
    echo "  Download it from: https://www.python.org/downloads/"
    echo "  Make sure to check 'Add Python to PATH' during install."
    echo ""
    read -p "  Press Enter to exit..."
    exit 1
fi

# Use whichever python command works
PYTHON=$(command -v python3 || command -v python)

# Install dependencies
echo "  Installing dependencies..."
$PYTHON -m pip install -q -r requirements.txt 2>&1 | tail -1
echo "  Done."
echo ""

# Check .env exists
if [ ! -f .env ]; then
    echo "  No .env file found — copying from .env.example"
    cp .env.example .env
    echo "  Please edit .env with your API keys, then run this again."
    echo ""
    read -p "  Press Enter to exit..."
    exit 1
fi

echo "  Starting dashboard..."
echo "  ────────────────────────────────────────"
echo ""
echo "  Open your browser to: http://localhost:8000"
echo ""
echo "  Press Ctrl+C to stop."
echo "  ────────────────────────────────────────"
echo ""

$PYTHON run.py
