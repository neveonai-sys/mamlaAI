#!/bin/bash

# eCourts FastAPI Scraper Start Script
# Starts the unified DC + HC scraper on 127.0.0.1:PORT
# Usage: ./start_scrapper.sh [dev|prod]
# Default: prod (port 8002) | dev (port 8003)

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LEGALENV_PATH="$PROJECT_ROOT/Legalv1/legalenv"

# Determine mode and port
MODE="${1:-prod}"
if [ "$MODE" = "dev" ]; then
    SCRAPER_PORT=8003
    LOG_DIR="$PROJECT_ROOT/logs/dev"
else
    SCRAPER_PORT=8002
    LOG_DIR="$PROJECT_ROOT/logs"
fi

mkdir -p "$LOG_DIR"

if [ ! -f "$LEGALENV_PATH" ]; then
    echo "Error: missing env file at $LEGALENV_PATH"
    exit 1
fi

# Rotate existing log before starting fresh
FASTAPI_LOG="$LOG_DIR/scraper.log"
if [ -s "$FASTAPI_LOG" ]; then
    mv "$FASTAPI_LOG" "$LOG_DIR/scraper.prev.log"
fi

UVICORN_BIN="/home/pronoys/miniconda3/envs/py312/bin/uvicorn"
FASTAPI_MODULE="main"
FASTAPI_SCRAPER_DIR="$PROJECT_ROOT/scrapping_codes_ecourt"

# Load CAPSOLVER_API_KEY from legalenv
CAPSOLVER_KEY=$(grep '^CAPSOLVER_API=' "$LEGALENV_PATH" | cut -d= -f2-)

echo "Starting Unified eCourts FastAPI scraper (DC + HC) on 127.0.0.1:$SCRAPER_PORT ($MODE mode)..."

# Kill any existing instance on the target port
lsof -ti:$SCRAPER_PORT 2>/dev/null | xargs kill -9 2>/dev/null
sleep 1

if [ ! -x "$UVICORN_BIN" ]; then
    echo "  ⚠️  Warning: uvicorn not found at $UVICORN_BIN — eCourts scraper unavailable"
elif [ -z "$CAPSOLVER_KEY" ]; then
    echo "  ⚠️  Warning: CAPSOLVER_API not set in legalenv — eCourts scraper unavailable"
else
    cd "$FASTAPI_SCRAPER_DIR"
    nohup env CAPSOLVER_API_KEY="$CAPSOLVER_KEY" \
        "$UVICORN_BIN" "${FASTAPI_MODULE}:app" \
        --host 127.0.0.1 --port $SCRAPER_PORT \
        --workers 2 \
        > "$FASTAPI_LOG" 2>&1 &
    sleep 2
    if lsof -ti:$SCRAPER_PORT >/dev/null 2>&1; then
        echo "  ✅ Unified scraper running on 127.0.0.1:$SCRAPER_PORT  (DC → /dc  |  HC → /hc)"
    else
        echo "  ❌ Unified scraper failed to start — check $FASTAPI_LOG"
    fi
    cd "$PROJECT_ROOT"
fi

echo "  📋 Log: $FASTAPI_LOG"
exit 0
