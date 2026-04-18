#!/bin/bash

# Frontend Start Script
# Usage: ./start_frontend.sh [dev|prod]
# Default: prod (production mode)

PROJECT_ROOT="/home/pronoys/products/sessioned_AiAdalat/Adalatai_ground_zero"
FRONTEND_ROOT="/home/pronoys/products/sessioned_AiAdalat/mamlaAI_ground_zero/frontend"

MODE="prod"
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
    [ -s "$DEV_LOG" ] && mv "$DEV_LOG" "$PROJECT_ROOT/logs/dev/frontend.$(date +%Y-%m-%d_%H%M).log"
    nohup npm start > "$DEV_LOG" 2>&1 &
    echo "  ✅ Dev server starting — logs: $DEV_LOG"
else
    echo "🏭 Building Production Bundle..."
    echo "⚡ Minification: ENABLED | 📦 Code Splitting: ENABLED | 🔒 Source Maps: DISABLED"
    npm run build || exit 1
    kill -9 $(ps -fu $USER | grep -v grep | grep mamlaAI_ground_zero/frontend | grep webpack | awk '{print $2}') 2>/dev/null
    kill -9 $(ps -fu $USER | grep -v grep | grep 'webpack serve' | awk '{print $2}') 2>/dev/null
    lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null
    echo "  ✅ Production build complete — served by Nginx at https://mamla.ai"
    echo "  📁 Static files: $FRONTEND_ROOT/dist"
fi

exit 0
