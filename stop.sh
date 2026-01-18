#!/bin/bash

# ArNext-Intelligence - Stop Script
# This script stops both backend and frontend servers

echo "🛑 Stopping ArNext-Intelligence..."
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Stop Backend
if [ -f "$SCRIPT_DIR/.backend.pid" ]; then
    BACKEND_PID=$(cat "$SCRIPT_DIR/.backend.pid")
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        kill $BACKEND_PID
        echo -e "${GREEN}✓ Backend stopped (PID: $BACKEND_PID)${NC}"
    else
        echo -e "${RED}⚠ Backend process not found${NC}"
    fi
    rm "$SCRIPT_DIR/.backend.pid"
else
    echo "⚠ No backend PID file found. Attempting to kill all uvicorn processes..."
    pkill -f "uvicorn backend.app.main:app"
fi

# Stop Frontend
if [ -f "$SCRIPT_DIR/.frontend.pid" ]; then
    FRONTEND_PID=$(cat "$SCRIPT_DIR/.frontend.pid")
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        kill $FRONTEND_PID
        echo -e "${GREEN}✓ Frontend stopped (PID: $FRONTEND_PID)${NC}"
    else
        echo -e "${RED}⚠ Frontend process not found${NC}"
    fi
    rm "$SCRIPT_DIR/.frontend.pid"
else
    echo "⚠ No frontend PID file found. Attempting to kill all next processes..."
    pkill -f "next dev"
fi

echo ""
echo -e "${GREEN}✅ ArNext-Intelligence stopped${NC}"
echo ""
