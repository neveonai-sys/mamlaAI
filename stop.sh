#!/bin/bash

# Orchestrator Stop Script — stops all services
# Usage: ./stop.sh [dev|prod|both]
# Default: both (stops ALL environments safely)
#
# Pass a mode to only stop one environment without touching the other:
#   ./stop.sh dev   — stop only dev (ports 8100, 3001, dev Celery workers)
#   ./stop.sh prod  — stop only prod (port 8000, prod Celery workers, beat, Redis monitor)
#   ./stop.sh both  — stop everything (default)
#
# Individual scripts can also be run standalone:
#   ./stop_backend.sh [dev|prod|both]
#   ./stop_scrapper.sh
#   ./stop_frontend.sh

PROJECT_ROOT="/home/pronoys/products/sessioned_AiAdalat/Adalatai_ground_zero"

MODE="${1:-both}"

if [[ "$MODE" != "dev" && "$MODE" != "prod" && "$MODE" != "both" ]]; then
    echo "Usage: $0 [dev|prod|both]"
    echo "  dev   — stop only dev services"
    echo "  prod  — stop only prod services"
    echo "  both  — stop all services (default)"
    exit 1
fi

echo "🛑 Stopping all services ($MODE)..."
echo "================================================"

cd "$PROJECT_ROOT"

# Frontend — always stop both ports (webpack-dev-server is stateless)
echo "── Frontend ────────────────────────────────────"
"$PROJECT_ROOT/stop_frontend.sh"
echo ""

# eCourts scraper — stop only when prod or both (scraper serves prod on port 8001)
if [[ "$MODE" == "prod" || "$MODE" == "both" ]]; then
    echo "── eCourts FastAPI Scraper ─────────────────────"
    "$PROJECT_ROOT/stop_scrapper.sh"
    echo ""
fi

echo "── Backend (Django + Celery) ───────────────────"
"$PROJECT_ROOT/stop_backend.sh" "$MODE"
echo ""

echo "================================================"
echo "✅ Services stopped ($MODE)"
echo "📁 Logs: $PROJECT_ROOT/logs/"
echo "💡 To start: ./start.sh [dev|prod]"
echo "💡 Individually: stop_backend.sh [dev|prod|both] | stop_scrapper.sh | stop_frontend.sh"
echo "================================================"

exit 0
