#!/bin/bash

# Orchestrator Start Script — starts all services
# Usage: ./start.sh [dev|prod]
# Default: prod (production mode)
#
# Individual scripts:
#   ./start_backend.sh [dev|prod]   — Django + Celery + Redis Monitor
#   ./start_scrapper.sh             — eCourts FastAPI Scraper (port 8001)
#   ./start_frontend.sh [dev|prod]  — webpack dev server or production build

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse command line arguments — check .deploy-mode file first, then argument, then default
if [ -f "$PROJECT_ROOT/.deploy-mode" ]; then
    MODE="$(cat "$PROJECT_ROOT/.deploy-mode")"
elif [ -n "$1" ]; then
    MODE="$1"
else
    MODE="prod"
fi

if [[ "$MODE" != "dev" && "$MODE" != "prod" ]]; then
    echo "Usage: $0 [dev|prod]  or set .deploy-mode file"
    echo "  dev  - Development mode (HMR, source maps, webpack dev server)"
    echo "  prod - Production mode (optimized build, static serving)"
    exit 1
fi

# RAM guard check
AVAIL_MB=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
if [ "$AVAIL_MB" -lt 400 ]; then
    echo "⚠️  WARNING: Only ${AVAIL_MB}MB RAM available — starting services may trigger OOM."
    echo "   Try: ./stop.sh $([[ "$MODE" == "dev" ]] && echo "dev" || echo "prod")"
    read -p "Continue anyway? [y/N] " ans
    [[ "$ans" =~ ^[Yy]$ ]] || exit 1
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
"$PROJECT_ROOT/start_scrapper.sh" "$MODE"
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
