#!/bin/bash

# Frontend Stop Script

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🎨 Stopping Frontend Services..."
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
        fi
    fi
}

kill_processes "webpack serve" "Webpack Dev Server"
kill_processes "webpack.*development" "Webpack Development Build"
kill_processes "npm start" "NPM Development Server"
kill_processes "serve -s dist" "Production Static Server"
kill_processes "python.*http.server.*3000" "Production Python Server"
kill_processes "python.*SimpleHTTPServer.*3000" "Production Python Server"
kill_processes "Adalatai_ground_zero.*react-scripts" "React Scripts"
kill_processes "webpack" "Webpack Processes"
kill_processes "node.*webpack" "Node Webpack Processes"
kill_processes "node.*Adalatai_ground_zero" "Project Node.js Processes"
kill_processes "babel-node" "Babel Node"
kill_processes "nodemon" "Nodemon"
kill_processes "npm.*$PROJECT_ROOT" "Project NPM Processes"
kill_by_port 3000 "Frontend (prod dev-server / legacy)"
kill_by_port 3001 "Frontend (dev server)"
kill_by_port 8080 "Frontend (alt port)"

# Clean cache
if [ -d "$PROJECT_ROOT/frontend_webpack/node_modules/.cache" ]; then
    rm -rf "$PROJECT_ROOT/frontend_webpack/node_modules/.cache" 2>/dev/null || true
    echo "✅ Webpack cache cleaned"
fi
if [ -f "$PROJECT_ROOT/frontend_webpack/.eslintcache" ]; then
    rm -f "$PROJECT_ROOT/frontend_webpack/.eslintcache" 2>/dev/null || true
    echo "✅ ESLint cache cleaned"
fi

echo "✅ Frontend services stopped"
exit 0
