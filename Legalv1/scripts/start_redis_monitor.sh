#!/bin/bash
# Start script for Redis Monitor

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs/redis"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Check if monitor is already running
if pgrep -f "monitor_redis.py" > /dev/null; then
    echo "Redis monitor is already running"
    exit 0
fi

# Start the monitor
nohup python3 "$SCRIPT_DIR/monitor_redis.py" \
    --host localhost \
    --port 6379 \
    --interval 60 >> "$LOG_DIR/redis-monitor.log" 2>&1 &

# Verify it started
sleep 2
if ! pgrep -f "monitor_redis.py" > /dev/null; then
    echo "Failed to start Redis monitor"
    exit 1
fi

echo "Redis monitor started. Logs: $LOG_DIR/redis-monitor.log"
exit 0
