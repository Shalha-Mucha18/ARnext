#!/bin/bash

# ArNext-Intelligence - Quick Start Script
# This script starts both backend and frontend servers

echo "🚀 Starting ArNext-Intelligence..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Redis is running
echo "📡 Checking Redis..."
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis is running${NC}"
else
    echo -e "${RED}✗ Redis is not running. Starting Redis...${NC}"
    sudo systemctl start redis-server
    sleep 2
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Redis started successfully${NC}"
    else
        echo -e "${RED}✗ Failed to start Redis. Please start it manually.${NC}"
        exit 1
    fi
fi

echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Start Backend
echo -e "${BLUE}🔧 Starting Backend Server...${NC}"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${RED}✗ Virtual environment not found. Creating...${NC}"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r backend/requirements.txt
else
    source .venv/bin/activate
fi

# Start backend in background
nohup uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"
echo "  Logs: $SCRIPT_DIR/backend.log"
echo "  URL: http://localhost:8000"
echo ""

# Wait for backend to start
echo "⏳ Waiting for backend to initialize..."
sleep 3

# Check if backend is running
if curl -s http://localhost:8000/v1/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is healthy${NC}"
else
    echo -e "${RED}⚠ Backend may not be ready yet. Check backend.log for details.${NC}"
fi

echo ""

# Start Frontend
echo -e "${BLUE}🎨 Starting Frontend Server...${NC}"
cd "$SCRIPT_DIR/frontend"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${RED}✗ Node modules not found. Installing...${NC}"
    npm install
fi

# Start frontend in background
nohup npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"
echo "  Logs: $SCRIPT_DIR/frontend.log"
echo "  URL: http://localhost:3000"
echo ""

# Save PIDs for stop script
echo "$BACKEND_PID" > "$SCRIPT_DIR/.backend.pid"
echo "$FRONTEND_PID" > "$SCRIPT_DIR/.frontend.pid"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ ArNext-Intelligence is running!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Dashboard:  http://localhost:3000"
echo "🔌 Backend:    http://localhost:8000"
echo "📚 API Docs:   http://localhost:8000/docs"
echo ""
echo "To stop the servers, run: ./stop.sh"
echo "To view logs:"
echo "  Backend:  tail -f backend.log"
echo "  Frontend: tail -f frontend.log"
echo ""
