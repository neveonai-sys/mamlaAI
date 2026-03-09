#!/bin/bash
# Stop script for Redis Monitor

# Find and kill the monitor process
if pgrep -f "monitor_redis.py" > /dev/null; then
    pkill -f "monitor_redis.py"
    # Wait for the process to terminate
    sleep 1
    if ! pgrep -f "monitor_redis.py" > /dev/null; then
        echo "Redis monitor stopped successfully"
        exit 0
    else
        # If still running, force kill
        pkill -9 -f "monitor_redis.py"
        echo "Redis monitor force stopped"
        exit 0
    fi
else
    echo "Redis monitor is not running"
    exit 0
fi
