#!/bin/bash

# Stop Script for eCourts FastAPI Scraper only
# Usage: ./stop_scrapper.sh

echo "🛑 Stopping Unified eCourts FastAPI scraper..."

# Kill by process pattern (matches main:app launched by start_scrapper.sh)
PIDS=$(pgrep -f "uvicorn.*main" 2>/dev/null)
if [ -n "$PIDS" ]; then
    echo "🔄 Killing uvicorn process(es): $PIDS"
    kill -9 $PIDS 2>/dev/null || true
fi

# Kill by port as fallback
PORT_PIDS=$(lsof -ti:8002 2>/dev/null)
if [ -n "$PORT_PIDS" ]; then
    echo "🔄 Killing process(es) on port 8002: $PORT_PIDS"
    kill -9 $PORT_PIDS 2>/dev/null || true
fi

sleep 1
if lsof -ti:8002 >/dev/null 2>&1; then
    echo "❌ Port 8002 still occupied — manual intervention may be needed"
else
    echo "✅ Unified eCourts FastAPI scraper stopped"
fi

exit 0
