#!/bin/bash

# Enhanced Start Script with Development and Production Modes
# Usage: ./start_backend.sh [dev|prod]
# Default: prod (production mode)
#
# Isolation strategy:
#   prod — Gunicorn on port 8000, Redis DB 0, named Celery workers prod_worker/prod_ecourts
#   dev  — Django runserver on port 8100, Redis DB 1, named Celery workers dev_worker/dev_ecourts
#          NO Celery beat in dev (avoids double emails/scheduled triggers)

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
    echo "  dev  - Development mode (Django runserver port 8100, Redis DB 1, reduced workers)"
    echo "  prod - Production mode (Gunicorn port 8000, Redis DB 0, full workers)"
    exit 1
fi

# ── Mode-specific config ───────────────────────────────────────────────────
if [ "$MODE" = "dev" ]; then
    BACKEND_PORT=8100
    CELERY_WORKER_NAME="dev_worker"
    CELERY_ECOURTS_NAME="dev_ecourts"
    CELERY_GEVENT_CONCURRENCY=10
    CELERY_PREFORK_CONCURRENCY=2
    CELERY_LOGLEVEL="info"
    LOG_DIR="$PROJECT_ROOT/logs/dev"
    RUN_BEAT=false
else
    BACKEND_PORT=8000
    CELERY_WORKER_NAME="prod_worker"
    CELERY_ECOURTS_NAME="prod_ecourts"
    CELERY_GEVENT_CONCURRENCY=100
    CELERY_PREFORK_CONCURRENCY=4
    CELERY_LOGLEVEL="warning"
    LOG_DIR="$PROJECT_ROOT/logs"
    RUN_BEAT=true
fi

mkdir -p "$LOG_DIR"

# Rotate a log file before starting a fresh process.
# The previous active log is kept as name.prev.log (one backup per type, no clutter).
rotate_log() {
    local f="$LOG_DIR/$1.log"
    if [ -s "$f" ]; then
        mv "$f" "$LOG_DIR/$1.prev.log"
    fi
}

PYTHON_BIN="${PYTHON_BIN:-/home/pronoys/miniconda3/envs/myenv/bin/python}"
if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN=$(command -v python3 || command -v python)
fi

LEGALENV_PATH="$PROJECT_ROOT/Legalv1/legalenv"

if ! "$PYTHON_BIN" -c "import django, celery" >/dev/null 2>&1; then
    echo "Error: Python environment '$PYTHON_BIN' does not have required Django/Celery modules."
    exit 1
fi

validate_backend_env() {
    "$PYTHON_BIN" - <<PY
from dotenv import dotenv_values
from pathlib import Path
import sys

cfg = dotenv_values(Path(r"$LEGALENV_PATH"))
missing = []

for key in ("SUPABASE_URL", "SUPABASE_SECRET_KEY", "ENCRYPTION_KEY"):
    if not (cfg.get(key) or "").strip():
        missing.append(key)

mongo_uri = (cfg.get("MONGO_URI") or "").strip()
mongo_parts = [
    (cfg.get("MONGO_HOSTNAME") or "").strip(),
    (cfg.get("MONGO_PWD") or "").strip(),
    (cfg.get("MONGO_APPNAME") or "").strip(),
]
if not mongo_uri and not all(mongo_parts):
    missing.append("MONGO_URI (or MONGO_HOSTNAME + MONGO_PWD + MONGO_APPNAME)")

if missing:
    print("Error: backend configuration is incomplete in Legalv1/legalenv.")
    print("Missing or empty values:")
    for item in missing:
        print(f"  - {item}")
    sys.exit(1)
PY
}

if [ "$MODE" = "dev" ]; then
    LEGALENV_PATH="$PROJECT_ROOT/Legalv1/legalenv.dev"
fi

if [ ! -f "$LEGALENV_PATH" ]; then
    echo "Error: missing env file at $LEGALENV_PATH"
    exit 1
fi

if ! validate_backend_env; then
    exit 1
fi

# ── Stop only THIS mode's processes (leave the other mode running) ─────────
echo "Stopping existing $MODE backend processes on port $BACKEND_PORT..."
lsof -ti:"$BACKEND_PORT" 2>/dev/null | xargs kill -9 2>/dev/null || true

echo "Stopping $MODE Celery workers (${CELERY_WORKER_NAME} / ${CELERY_ECOURTS_NAME})..."
pkill -f "celery.*-n ${CELERY_WORKER_NAME}@" 2>/dev/null || true
pkill -f "celery.*-n ${CELERY_ECOURTS_NAME}@" 2>/dev/null || true
if [ "$RUN_BEAT" = "true" ]; then
    # Only kill beat in prod mode
    pkill -f "celery.*beat.*Legalv1" 2>/dev/null || true
fi
sleep 2

# ── Export DJANGO_MODE so settings.py picks the right env file ──────────────
export DJANGO_MODE="$MODE"
export BACKEND_PORT="$BACKEND_PORT"

cd "$PROJECT_ROOT/Legalv1"

# ── Start backend ──────────────────────────────────────────────────────────
rotate_log backend
if [ "$MODE" = "dev" ]; then
    echo "🔧 Starting Django Development Server on port $BACKEND_PORT..."
    nohup "$PYTHON_BIN" manage.py runserver "0.0.0.0:${BACKEND_PORT}" > "$LOG_DIR/backend.log" 2>&1 &
else
    echo "🏭 Starting Gunicorn Production Server on port $BACKEND_PORT..."
    nohup "$PYTHON_BIN" -m gunicorn Legalv1.wsgi:application \
        --config gunicorn_config.py \
        > "$LOG_DIR/backend.log" 2>&1 &
fi

echo "Waiting for backend to start..."
sleep 5

# ── Start Celery workers ───────────────────────────────────────────────────
echo "Starting $MODE Celery workers..."

rotate_log celery
nohup "$PYTHON_BIN" -m celery -A Legalv1 worker \
    -P gevent \
    --concurrency="$CELERY_GEVENT_CONCURRENCY" \
    --loglevel="$CELERY_LOGLEVEL" \
    -Q celery,audio_processing \
    -n "${CELERY_WORKER_NAME}@%h" \
    > "$LOG_DIR/celery.log" 2>&1 &

rotate_log celery_ecourts
nohup "$PYTHON_BIN" -m celery -A Legalv1 worker \
    -P prefork \
    --concurrency="$CELERY_PREFORK_CONCURRENCY" \
    --loglevel="$CELERY_LOGLEVEL" \
    -Q ecourts_realtime,ecourts_background \
    -n "${CELERY_ECOURTS_NAME}@%h" \
    > "$LOG_DIR/celery_ecourts.log" 2>&1 &

if [ "$RUN_BEAT" = "true" ]; then
    echo "Starting Celery Beat (prod only)..."
    rotate_log celery_beat
    nohup "$PYTHON_BIN" -m celery -A Legalv1 beat \
        --loglevel="$CELERY_LOGLEVEL" \
        > "$LOG_DIR/celery_beat.log" 2>&1 &
else
    echo "ℹ️  Celery Beat skipped in dev mode (prevents double email/scheduled triggers)"
fi

# ── Redis Monitor (prod only) ──────────────────────────────────────────────
if [ "$MODE" = "prod" ]; then
    echo "Starting Redis Monitor..."
    cd "$PROJECT_ROOT/Legalv1/scripts"
    ./stop_redis_monitor.sh >/dev/null 2>&1
    nohup ./start_redis_monitor.sh >> "$PROJECT_ROOT/logs/redis_monitor.log" 2>&1 &
fi

# ── Summary ────────────────────────────────────────────────────────────────
echo ""
echo "✅ Backend services started in $MODE mode!"
echo "================================================"
echo "🌐 Backend:  http://localhost:${BACKEND_PORT}"
echo "📦 Redis DB: $([ "$MODE" = "dev" ] && echo "1 (dev)" || echo "0 (prod)")"
if [ "$MODE" = "dev" ]; then
    echo "🔧 Celery:   gevent ×${CELERY_GEVENT_CONCURRENCY}, prefork ×${CELERY_PREFORK_CONCURRENCY} (dev — reduced)"
    echo "🚫 Beat:     disabled in dev"
else
    echo "🏭 Celery:   gevent ×${CELERY_GEVENT_CONCURRENCY}, prefork ×${CELERY_PREFORK_CONCURRENCY} (prod)"
    echo "⏰ Beat:     running"
fi
echo "================================================"
echo "📋 Logs: $LOG_DIR/"
echo "  - Django/Gunicorn:  $LOG_DIR/backend.log"
echo "  - Celery Worker:    $LOG_DIR/celery.log"
echo "  - Celery eCourts:   $LOG_DIR/celery_ecourts.log"
if [ "$RUN_BEAT" = "true" ]; then
    echo "  - Celery Beat:      $LOG_DIR/celery_beat.log"
    echo "  - Gunicorn Access:  $LOG_DIR/gunicorn-access.log"
    echo "  - Redis Monitor:    $PROJECT_ROOT/logs/redis_monitor.log"
fi
echo "  (Archives: name.YYYY-MM-DD_HHMM.log — removed after 3 days by cleanup_logs.sh)"
echo "================================================"

exit 0
