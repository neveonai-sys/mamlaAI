#!/bin/bash

# Enhanced Stop Script for Development and Production Modes
# This script stops all services regardless of mode (dev/prod)

# Get the project root directory
PROJECT_ROOT="/home/pronoys/products/sessioned_AiAdalat/Adalatai_ground_zero"

echo "🛑 Stopping all services..."
echo "================================================"

# Function to kill processes with a pattern
kill_processes() {
    local pattern=$1
    local name=$2
    local pids
    
    # Find all matching processes
    if pids=$(pgrep -f "$pattern" 2>/dev/null); then
        echo "🔄 Stopping $name..."
        # Kill processes and suppress 'no such process' errors
        kill -9 $pids 2>/dev/null || true
        # Wait for processes to terminate
        for pid in $pids; do
            while kill -0 "$pid" 2>/dev/null; do
                sleep 0.5
            done
        done
        echo "✅ $name stopped"
    else
        echo "ℹ️  No $name processes found"
    fi
}

# Function to kill processes by port
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

echo "[$(date)] Stopping services..."

# Stop Redis Monitor first (if exists)
if [ -f "$PROJECT_ROOT/Legalv1/scripts/stop_redis_monitor.sh" ]; then
    echo "🔄 Stopping Redis Monitor..."
    "$PROJECT_ROOT/Legalv1/scripts/stop_redis_monitor.sh" >/dev/null 2>&1 || true
    echo "✅ Redis Monitor stopped"
fi

# Stop Frontend processes (both dev and prod modes)
echo ""
echo "🎨 Stopping Frontend Services..."
echo "--------------------------------"

# Development mode processes
kill_processes "webpack serve" "Webpack Dev Server"
kill_processes "webpack.*development" "Webpack Development Build"
kill_processes "npm start" "NPM Development Server"

# Production mode processes  
kill_processes "serve -s dist" "Production Static Server (serve)"
kill_processes "python.*http.server.*3000" "Production Python Server (port 3000)"
kill_processes "python.*SimpleHTTPServer.*3000" "Production Python Server (port 3000)"

# General webpack and react processes
kill_processes "Adalatai_ground_zero.*react-scripts" "React Scripts"
kill_processes "webpack" "Webpack Processes"
kill_processes "node.*webpack" "Node Webpack Processes"

# Kill by ports (frontend)
kill_by_port 3000 "Frontend Services"
kill_by_port 8080 "Alternative Frontend Port"

# Stop Backend processes
echo ""
echo "🔧 Stopping Backend Services..."
echo "-------------------------------"
kill_processes "python.*manage.py runserver" "Django Development Server"
kill_processes "gunicorn.*Legalv1.wsgi" "Gunicorn Production Server"
kill_by_port 8000 "Backend Services"

# Stop Celery processes
echo ""
echo "🔄 Stopping Celery Services..."
echo "------------------------------"
kill_processes "celery.*worker" "Celery Worker"
kill_processes "celery.*beat" "Celery Beat"

# Kill any remaining project-related node processes
echo ""
echo "🧹 Cleaning up remaining processes..."
echo "------------------------------------"
kill_processes "node.*$PROJECT_ROOT" "Project Node.js Processes"
kill_processes "node.*Adalatai_ground_zero" "Project Node.js Processes (by name)"

# Additional cleanup for any webpack or babel processes
kill_processes "babel-node" "Babel Node Processes"
kill_processes "nodemon" "Nodemon Processes"

# Clean up any npm processes related to the project
kill_processes "npm.*$PROJECT_ROOT" "Project NPM Processes"

# Optional: Clean cache and temporary files
echo ""
echo "🧹 Cleaning temporary files..."
echo "------------------------------"

# Clean webpack cache
if [ -d "$PROJECT_ROOT/frontend_webpack/node_modules/.cache" ]; then
    echo "🔄 Cleaning webpack cache..."
    rm -rf "$PROJECT_ROOT/frontend_webpack/node_modules/.cache" 2>/dev/null || true
    echo "✅ Webpack cache cleaned"
fi

# Clean ESLint cache
if [ -f "$PROJECT_ROOT/frontend_webpack/.eslintcache" ]; then
    echo "🔄 Cleaning ESLint cache..."
    rm -f "$PROJECT_ROOT/frontend_webpack/.eslintcache" 2>/dev/null || true
    echo "✅ ESLint cache cleaned"
fi

# Show final status
echo ""
echo "✅ All services have been stopped successfully!"
echo "================================================"
echo "📋 Summary:"
echo "   - Frontend services (dev & prod modes) stopped"
echo "   - Backend services stopped"
echo "   - Celery services stopped"
echo "   - Redis monitor stopped"
echo "   - Temporary files cleaned"
echo "================================================"
echo "📁 Logs are still available in: $PROJECT_ROOT/logs/"
echo ""
echo "💡 To start services again:"
echo "   Development: ./start.sh dev"
echo "   Production:  ./start.sh prod"
echo "================================================"

exit 0
