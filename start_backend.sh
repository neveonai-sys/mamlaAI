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


# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/logs"

PYTHON_BIN="${PYTHON_BIN:-/home/pronoys/miniconda3/envs/myenv/bin/python}"
if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN=$(command -v python3 || command -v python)
fi

if ! "$PYTHON_BIN" -c "import django, celery" >/dev/null 2>&1; then
    echo "Error: Python environment '$PYTHON_BIN' does not have required Django/Celery modules."
    exit 1
fi

# Function to check if a port is in use
is_port_in_use() {
    local port=$1
    if command -v lsof >/dev/null 2>&1; then
        lsof -i :"$port" >/dev/null 2>&1
    else
        netstat -tuln 2>/dev/null | grep -q ":$port "
    fi
    return $?
}


echo "Restarting Backend"
kill -9 `ps -fu $USER | grep -v grep | grep -E 'runserver|gunicorn' | awk '{print $2}'` 2>/dev/null
cd "$PROJECT_ROOT/Legalv1"

# Start backend based on mode
if [ "$MODE" = "dev" ]; then
    echo "🔧 Starting Django Development Server..."
    nohup "$PYTHON_BIN" manage.py runserver > "$PROJECT_ROOT/logs/backend.log" 2>&1 &
else
    echo "🏭 Starting Gunicorn Production Server..."
    # Use gunicorn_config.py with daily log rotation (keeps 3 days)
    nohup "$PYTHON_BIN" -m gunicorn Legalv1.wsgi:application \
        --config gunicorn_config.py \
        > "$PROJECT_ROOT/logs/backend.log" 2>&1 &
fi

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 5

echo "Restarting Celery"
kill -9 `ps -fu $USER | grep -v grep | grep celery | awk '{print $2}'` 2>/dev/null
cd "$PROJECT_ROOT/Legalv1"

# Use date-based log files for Celery (matching Django's pattern)
LOG_DATE=$(date +%d-%m-%Y)
CELERY_LOGLEVEL="warning"
if [ "$MODE" = "dev" ]; then
    CELERY_LOGLEVEL="info"
fi
nohup "$PYTHON_BIN" -m celery -A Legalv1 worker -P gevent --concurrency=100 --loglevel="$CELERY_LOGLEVEL" -Q celery,audio_processing > "$PROJECT_ROOT/logs/${LOG_DATE}_celery.log" 2>&1 &
nohup "$PYTHON_BIN" -m celery -A Legalv1 worker -P prefork --concurrency=4 --loglevel="$CELERY_LOGLEVEL" -Q ecourts_realtime,ecourts_background -n ecourts_worker@%h > "$PROJECT_ROOT/logs/${LOG_DATE}_celery_ecourts.log" 2>&1 &
nohup "$PYTHON_BIN" -m celery -A Legalv1 beat --loglevel="$CELERY_LOGLEVEL" > "$PROJECT_ROOT/logs/${LOG_DATE}_celery_beat.log" 2>&1 &

echo "Starting Redis Monitor..."
cd "$PROJECT_ROOT/Legalv1/scripts"
./stop_redis_monitor.sh >/dev/null 2>&1  # Ensure no existing monitor is running
nohup ./start_redis_monitor.sh > "$PROJECT_ROOT/logs/redis_monitor_startup.log" 2>&1 &

# Show service status
echo -e "\n✅ Services started successfully in $MODE mode!"
echo "================================================"
echo "🌐 Backend: http://localhost:8000"
# echo "🎨 Frontend: http://localhost:3000"
if [ "$MODE" = "dev" ]; then
    echo "🔥 Development Features:"
    echo "   - Hot Module Replacement (HMR)"
    echo "   - Source Maps for debugging"
    echo "   - React Refresh"
else
    echo "🏭 Production Features:"
    echo "   - Optimized bundle"
    echo "   - Code splitting"
    echo "   - Minification"
fi
echo "================================================"
echo "📋 Logs (auto-rotated daily, 3-day retention):"
echo "   - Django: $PROJECT_ROOT/logs/$(date +%d-%m-%Y)_django.log"
echo "   - Gunicorn Access: $PROJECT_ROOT/logs/$(date +%d-%m-%Y)_gunicorn-access.log"
echo "   - Gunicorn Error: $PROJECT_ROOT/logs/$(date +%d-%m-%Y)_gunicorn-error.log"
echo "   - Celery Worker: $PROJECT_ROOT/logs/$(date +%d-%m-%Y)_celery.log"
echo "   - Celery Beat: $PROJECT_ROOT/logs/$(date +%d-%m-%Y)_celery_beat.log"
# echo "   - Frontend: $PROJECT_ROOT/logs/frontend.log"
echo "   - Redis Monitor: $PROJECT_ROOT/logs/redis/redis-monitor.log"
echo ""
echo "   📁 All logs: $PROJECT_ROOT/logs/"
echo "   🧹 Cleanup script: ./cleanup_logs.sh (keeps 3 days)"
echo "================================================"

exit 0
