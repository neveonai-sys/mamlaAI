#!/bin/bash

# Stop Script for eCourts FastAPI Scraper only
# Usage: ./stop_scrapper.sh

echo "🛑 Stopping eCourts FastAPI scraper..."

# Kill by process pattern
PIDS=$(pgrep -f "uvicorn.*ecourts_fastapi" 2>/dev/null)
if [ -n "$PIDS" ]; then
    echo "🔄 Killing uvicorn process(es): $PIDS"
    kill -9 $PIDS 2>/dev/null || true
fi

# Kill by port as fallback
PORT_PIDS=$(lsof -ti:8001 2>/dev/null)
if [ -n "$PORT_PIDS" ]; then
    echo "🔄 Killing process(es) on port 8001: $PORT_PIDS"
    kill -9 $PORT_PIDS 2>/dev/null || true
fi

sleep 1
if lsof -ti:8001 >/dev/null 2>&1; then
    echo "❌ Port 8001 still occupied — manual intervention may be needed"
else
    echo "✅ eCourts FastAPI scraper stopped"
fi

exit 0
