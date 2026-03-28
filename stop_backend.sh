#!/bin/bash

# Backend Stop Script (Django + Celery + Redis Monitor)

PROJECT_ROOT="/home/pronoys/products/sessioned_AiAdalat/Adalatai_ground_zero"

echo "🔧 Stopping Backend Services..."
echo "--------------------------------"

kill_processes() {
    local pattern=$1
    local name=$2
    local pids
    if pids=$(pgrep -f "$pattern" 2>/dev/null); then
        echo "🔄 Stopping $name..."
        kill -9 $pids 2>/dev/null || true
        for pid in $pids; do
            while kill -0 "$pid" 2>/dev/null; do sleep 0.5; done
        done
        echo "✅ $name stopped"
    else
        echo "ℹ️  No $name processes found"
    fi
}

kill_by_port() {
    local port=$1
    local name=$2
    if command -v lsof >/dev/null 2>&1; then
        local pids=$(lsof -ti:$port 2>/dev/null)
        if [ -n "$pids" ]; then
            echo "🔄 Stopping $name on port $port..."
            kill -9 $pids 2>/dev/null || true
            echo "✅ $name on port $port stopped"
        else
            echo "ℹ️  No $name processes found on port $port"
        fi
    fi
}

# Stop Redis Monitor first
if [ -f "$PROJECT_ROOT/Legalv1/scripts/stop_redis_monitor.sh" ]; then
    echo "🔄 Stopping Redis Monitor..."
    "$PROJECT_ROOT/Legalv1/scripts/stop_redis_monitor.sh" >/dev/null 2>&1 || true
    echo "✅ Redis Monitor stopped"
fi

kill_processes "python.*manage.py runserver" "Django Development Server"
kill_processes "gunicorn.*Legalv1.wsgi" "Gunicorn Production Server"
kill_by_port 8000 "Backend Services"

echo ""
echo "🔄 Stopping Celery Services..."
echo "------------------------------"
kill_processes "celery.*worker" "Celery Worker"
kill_processes "celery.*beat" "Celery Beat"

echo "✅ Backend services stopped"
exit 0
