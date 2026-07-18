#!/bin/bash

# Frontend Start Script
# Usage: ./start_frontend.sh [dev|prod]
# Default: prod (production mode)

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_ROOT="$PROJECT_ROOT/new_frontend"

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

echo "🎨 Setting up Frontend ($MODE mode)..."
mkdir -p "$PROJECT_ROOT/logs"
mkdir -p "$PROJECT_ROOT/logs/dev"

if ! command -v node &>/dev/null || ! command -v npm &>/dev/null; then
    echo "Error: Node.js and npm are required but not installed."
    exit 1
fi

cd "$FRONTEND_ROOT"

if [ "$MODE" = "dev" ]; then
    export NODE_ENV=development
    export BABEL_ENV=development
    export DEV_PORT=3001
    export DEV_BACKEND_PORT=8100
else
    export NODE_ENV=production
    export BABEL_ENV=production
fi

if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install || exit 1
fi

if [ "$MODE" = "dev" ]; then
    echo "🔥 Starting Development Server..."
    echo "📍 Frontend will be available at: http://localhost:3001"
    echo "🔄 Hot Module Replacement: ENABLED"
    echo "🐛 Source Maps: ENABLED"
    echo "🔗 API proxy: /api → http://localhost:8100"
    kill -9 $(ps -fu $USER | grep -v grep | grep 'webpack serve' | awk '{print $2}') 2>/dev/null
    kill -9 $(ps -fu $USER | grep -v grep | grep webpack | awk '{print $2}') 2>/dev/null
    DEV_LOG="$PROJECT_ROOT/logs/dev/frontend.log"
    [ -s "$DEV_LOG" ] && mv "$DEV_LOG" "$PROJECT_ROOT/logs/dev/frontend.$(date +%Y-%m-%d).log"
    nohup npm start > "$DEV_LOG" 2>&1 &
    echo "  ✅ Dev server starting — logs: $DEV_LOG"
else
    echo "🏭 Building Production Bundle..."
    echo "⚡ Minification: ENABLED | 📦 Code Splitting: ENABLED | 🔒 Source Maps: DISABLED"
    npm run build || exit 1
    kill -9 $(ps -fu $USER | grep -v grep | grep 'new_frontend' | grep webpack | awk '{print $2}') 2>/dev/null
    kill -9 $(ps -fu $USER | grep -v grep | grep 'webpack serve' | awk '{print $2}') 2>/dev/null
    lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null
    echo "  ✅ Production build complete — served by Nginx"
    echo "  📁 Static files: $FRONTEND_ROOT/dist"
fi

exit 0
