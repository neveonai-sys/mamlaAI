#!/bin/bash

# Enhanced Start Script with Development and Production Modes
# Usage: ./start.sh [dev|prod]
# Default: prod (production mode)

# Get the project root directory
PROJECT_ROOT="/home/pronoys/products/sessioned_AiAdalat/Adalatai_ground_zero"

# Parse command line arguments
MODE="prod"  # Default to production
if [ "$1" = "dev" ]; then
    MODE="dev"
elif [ "$1" = "prod" ]; then
    MODE="prod"
elif [ -n "$1" ]; then
    echo "Usage: $0 [dev|prod]"
    echo "  dev  - Development mode (HMR, source maps, webpack dev server)"
    echo "  prod - Production mode (optimized build, static serving)"
    exit 1
fi

echo "🚀 Starting services in $MODE mode..."
echo "================================================"

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/logs"

PYTHON_BIN="${PYTHON_BIN:-/home/pronoys/miniconda3/envs/py312/bin/python}"
if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN=$(command -v python3 || command -v python)
fi

LEGALENV_PATH="$PROJECT_ROOT/Legalv1/legalenv"

# if ! "$PYTHON_BIN" -c "import django, celery" >/dev/null 2>&1; then
#     echo "Error: Python environment '$PYTHON_BIN' does not have required Django/Celery modules."
#     exit 1
# fi


if [ ! -f "$LEGALENV_PATH" ]; then
    echo "Error: missing env file at $LEGALENV_PATH"
    exit 1
fi

# if ! validate_backend_env; then
#     exit 1
# fi



# Stop any running services first
# if [ -f "$PROJECT_ROOT/stop.sh" ]; then
#     echo "Stopping any running services..."
#     "$PROJECT_ROOT/stop.sh"
# fi
# ── eCourts FastAPI Scraper (port 8001, localhost only) ──────────────────────
echo "Starting eCourts FastAPI scraper..."
LOG_DATE=$(date +%d-%m-%Y)
UVICORN_BIN="/home/pronoys/miniconda3/envs/py312/bin/uvicorn"
FASTAPI_MODULE="ecourts_fastapi_scrapper_cnr_and_causelist_casestatus_and_courtstatus"
FASTAPI_SCRAPER_DIR="$PROJECT_ROOT/scrapping_codes_ecourt"
FASTAPI_LOG="$PROJECT_ROOT/logs/${LOG_DATE}_ecourts_scraper.log"

# Kill any existing instance on port 8001
lsof -ti:8001 2>/dev/null | xargs kill -9 2>/dev/null
sleep 1

# Load CAPSOLVER_API_KEY from legalenv (FastAPI reads CAPSOLVER_API_KEY)
CAPSOLVER_KEY=$(grep '^CAPSOLVER_API=' "$LEGALENV_PATH" | cut -d= -f2-)

if [ ! -x "$UVICORN_BIN" ]; then
    echo "  ⚠️  Warning: uvicorn not found at $UVICORN_BIN — eCourts case search unavailable"
elif [ -z "$CAPSOLVER_KEY" ]; then
    echo "  ⚠️  Warning: CAPSOLVER_API not set in legalenv — eCourts case search unavailable"
else
    cd "$FASTAPI_SCRAPER_DIR"
    nohup env CAPSOLVER_API_KEY="$CAPSOLVER_KEY" \
        "$UVICORN_BIN" "${FASTAPI_MODULE}:app" \
        --host 127.0.0.1 --port 8001 \
        --workers 2 \
        > "$FASTAPI_LOG" 2>&1 &
    sleep 2
    if lsof -ti:8001 >/dev/null 2>&1; then
        echo "  ✅ eCourts FastAPI scraper running on 127.0.0.1:8001"
    else
        echo "  ❌ eCourts FastAPI scraper failed to start — check $FASTAPI_LOG"
    fi
    cd "$PROJECT_ROOT"
fi


echo "   - eCourts Scraper: $PROJECT_ROOT/logs/$(date +%d-%m-%Y)_ecourts_scraper.log"
echo ""
echo "   📁 All logs: $PROJECT_ROOT/logs/"
echo "   🧹 Cleanup script: ./cleanup_logs.sh (keeps 3 days)"
echo "================================================"

exit 0
