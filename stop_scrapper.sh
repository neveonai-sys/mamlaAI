#!/bin/bash

# Stop Script for eCourts FastAPI Scraper
# Usage: ./stop_scrapper.sh [dev|prod|both]
# Default: both (stops all scraper instances)

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Determine which scraper(s) to stop
MODE="${1:-both}"
if [ "$MODE" = "dev" ]; then
    PORTS="8003"
elif [ "$MODE" = "prod" ]; then
    PORTS="8002"
else
    PORTS="8002 8003"
fi

echo "🛑 Stopping eCourts FastAPI scraper ($MODE mode)..."

# Kill by process pattern (matches main:app launched by start_scrapper.sh)
PIDS=$(pgrep -f "uvicorn.*main" 2>/dev/null)
if [ -n "$PIDS" ]; then
    echo "🔄 Killing uvicorn process(es): $PIDS"
    kill -9 $PIDS 2>/dev/null || true
fi

# Kill by port based on mode
for PORT in $PORTS; do
    PORT_PIDS=$(lsof -ti:$PORT 2>/dev/null)
    if [ -n "$PORT_PIDS" ]; then
        echo "🔄 Killing process(es) on port $PORT: $PORT_PIDS"
        kill -9 $PORT_PIDS 2>/dev/null || true
    fi
done

sleep 1
echo "✅ eCourts FastAPI scraper stopped ($MODE mode)"

exit 0
