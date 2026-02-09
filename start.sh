#!/bin/bash

# Kill child processes on exit
trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT

echo "🚀 Starting AI Smart Investment Advisor..."

# Check requirements
if ! command -v npm &> /dev/null; then
    echo "❌ Error: npm is not installed"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed"
    exit 1
fi

# Start Backend
echo "📈 Starting Backend (FastAPI) on port 8000..."

# Find the python/pip executable to use
ROOT_DIR=$(pwd)
if [ -d ".venv" ]; then
    PYTHON_EXEC="$ROOT_DIR/.venv/bin/python3"
    PIP_EXEC="$ROOT_DIR/.venv/bin/pip3"
elif [ -d "backend/venv" ]; then
    PYTHON_EXEC="$ROOT_DIR/backend/venv/bin/python3"
    PIP_EXEC="$ROOT_DIR/backend/venv/bin/pip3"
else
    PYTHON_EXEC="python3"
    PIP_EXEC="pip3"
fi

cd backend
$PIP_EXEC install -r requirements.txt > /dev/null 2>&1
$PYTHON_EXEC -m uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# Start Frontend
echo "💻 Starting Frontend (Next.js) on port 3000..."
cd frontend
npm install > /dev/null 2>&1
npm run dev &
FRONTEND_PID=$!
cd ..

echo "✅ Services are running!"
echo "   - Frontend: http://localhost:3000"
echo "   - Backend:  http://localhost:8000/docs"
echo "Press CTRL+C to stop."

wait
