#!/bin/bash

# Backend Stop Script (Django + Celery + Redis Monitor)
# Usage: ./stop_backend.sh [dev|prod]
# Default: stops BOTH modes safely (used by orchestrator stop.sh)
#
# Isolation: each mode owns named Celery workers + a specific port.
# Stopping dev does NOT touch prod (port 8000 / prod_worker) and vice-versa.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$PROJECT_ROOT/.deploy-mode" ]; then
    DEFAULT_MODE="$(cat "$PROJECT_ROOT/.deploy-mode")"
else
    DEFAULT_MODE="both"
fi

MODE="${1:-$DEFAULT_MODE}"  # dev | prod | both (default)

if [[ "$MODE" != "dev" && "$MODE" != "prod" && "$MODE" != "both" ]]; then
    echo "Usage: $0 [dev|prod|both]"
    exit 1
fi

echo "🔧 Stopping Backend Services ($MODE)..."
echo "--------------------------------"

kill_by_port() {
    local port=$1
    local name=$2
    if command -v lsof >/dev/null 2>&1; then
        local pids
        pids=$(lsof -ti:"$port" 2>/dev/null)
        if [ -n "$pids" ]; then
            echo "🔄 Stopping $name on port $port..."
            kill -9 $pids 2>/dev/null || true
            echo "✅ $name on port $port stopped"
        else
            echo "ℹ️  No $name processes found on port $port"
        fi
    fi
}

kill_pattern() {
    local pattern=$1
    local name=$2
    local pids
    if pids=$(pgrep -f "$pattern" 2>/dev/null); then
        echo "🔄 Stopping $name..."
        kill -9 $pids 2>/dev/null || true
        echo "✅ $name stopped"
    else
        echo "ℹ️  No $name processes found"
    fi
}

# ── Prod ──────────────────────────────────────────────────────────────────
if [[ "$MODE" == "prod" || "$MODE" == "both" ]]; then
    kill_by_port 8000 "Prod Backend (Gunicorn)"
    kill_pattern "celery.*-n prod_worker@" "Prod Celery Worker (prod_worker)"
    kill_pattern "celery.*-n prod_ecourts@" "Prod Celery eCourts (prod_ecourts)"
    kill_pattern "celery.*beat.*Legalv1" "Celery Beat"

    # Redis Monitor — only stop in prod/both (single shared monitor)
    if [ -f "$PROJECT_ROOT/Legalv1/scripts/stop_redis_monitor.sh" ]; then
        echo "🔄 Stopping Redis Monitor..."
        "$PROJECT_ROOT/Legalv1/scripts/stop_redis_monitor.sh" >/dev/null 2>&1 || true
        echo "✅ Redis Monitor stopped"
    fi
fi

# ── Dev ───────────────────────────────────────────────────────────────────
if [[ "$MODE" == "dev" || "$MODE" == "both" ]]; then
    kill_by_port 8100 "Dev Backend (runserver)"
    kill_pattern "celery.*-n dev_worker@" "Dev Celery Worker (dev_worker)"
    kill_pattern "celery.*-n dev_ecourts@" "Dev Celery eCourts (dev_ecourts)"
fi

echo ""
echo "✅ Backend services stopped ($MODE)"
exit 0
