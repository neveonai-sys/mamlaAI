#!/bin/bash

# Orchestrator Start Script — starts all services
# Usage: ./start.sh [dev|prod]
# Default: prod (production mode)
#
# Individual scripts:
#   ./start_backend.sh [dev|prod]   — Django + Celery + Redis Monitor
#   ./start_scrapper.sh             — eCourts FastAPI Scraper (port 8001)
#   ./start_frontend.sh [dev|prod]  — webpack dev server or production build

PROJECT_ROOT="/home/pronoys/products/sessioned_AiAdalat/Adalatai_ground_zero"

MODE="prod"
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

echo "🚀 Starting all services in $MODE mode..."
echo "================================================"

cd "$PROJECT_ROOT"
mkdir -p logs

echo "Stopping any running services first..."
"$PROJECT_ROOT/stop.sh"
echo ""

echo "── Backend (Django + Celery) ──────────────────────"
"$PROJECT_ROOT/start_backend.sh" "$MODE"
echo ""

echo "── eCourts FastAPI Scraper ─────────────────────────"
"$PROJECT_ROOT/start_scrapper.sh"
echo ""

echo "── Frontend ────────────────────────────────────────"
"$PROJECT_ROOT/start_frontend.sh" "$MODE"
echo ""

echo "================================================"
echo "✅ All services started in $MODE mode!"
echo "💡 To stop all:   ./stop.sh"
echo "💡 Individually:  start_backend.sh | start_scrapper.sh | start_frontend.sh"
echo "================================================"

exit 0
