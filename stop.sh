#!/bin/bash

# Orchestrator Stop Script — stops all services
# Individual scripts can also be run standalone:
#   ./stop_backend.sh    — Django + Celery + Redis Monitor
#   ./stop_scrapper.sh   — eCourts FastAPI Scraper (port 8001)
#   ./stop_frontend.sh   — webpack / npm / port 3000

PROJECT_ROOT="/home/pronoys/products/sessioned_AiAdalat/Adalatai_ground_zero"

echo "🛑 Stopping all services..."
echo "================================================"

cd "$PROJECT_ROOT"

echo "── Frontend ────────────────────────────────────"
"$PROJECT_ROOT/stop_frontend.sh"
echo ""

echo "── eCourts FastAPI Scraper ─────────────────────"
"$PROJECT_ROOT/stop_scrapper.sh"
echo ""

echo "── Backend (Django + Celery) ───────────────────"
"$PROJECT_ROOT/stop_backend.sh"
echo ""

echo "================================================"
echo "✅ All services stopped"
echo "📁 Logs: $PROJECT_ROOT/logs/"
echo "💡 To start: ./start.sh [dev|prod]"
echo "💡 Individually: stop_backend.sh | stop_scrapper.sh | stop_frontend.sh"
echo "================================================"

exit 0
