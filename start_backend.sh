#!/bin/bash
# Script to start the backend server

echo "Starting Prachi RAG Workspace Backend..."
echo ""

# Check if port 8000 is already in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "⚠️  Port 8000 is already in use"
    echo "Killing existing process..."
    lsof -ti :8000 | xargs kill -9 2>/dev/null
    sleep 2
fi

# Change to project directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
# Check for macOS venv first, then fall back to others
if [ -d "venv_mac" ]; then
    echo "Activating macOS virtual environment..."
    source venv_mac/bin/activate
elif [ -d "venv" ] && [ -d "venv/bin" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
else
    echo "⚠️  No virtual environment found!"
    echo "   Please create one with: python3 -m venv venv_mac"
    exit 1
fi

# Start the backend
echo "Starting uvicorn server on port 8000..."
echo ""
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

