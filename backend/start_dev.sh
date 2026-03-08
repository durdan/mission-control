#!/bin/bash

echo "🚀 Starting Mission Control V2 Backend (Development Mode)"
echo "=========================================="
echo ""

# Check Python
echo "📦 Checking Python environment..."
python3 --version

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv venv
fi

echo "📦 Activating virtual environment..."
source venv/bin/activate

echo "📦 Installing dependencies..."
pip install -q -r requirements.txt

# Check if PostgreSQL is needed
echo ""
echo "⚠️  Note: This will use mock data without PostgreSQL"
echo "   For full functionality, start PostgreSQL first:"
echo "   docker-compose up -d postgres redis"
echo ""

# Start the server
echo "🌟 Starting FastAPI server..."
echo "   URL: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo "   Health: http://localhost:8000/health"
echo ""

uvicorn main:app --reload --host 0.0.0.0 --port 8000