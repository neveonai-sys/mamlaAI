#!/bin/bash
# Setup script for Redis Monitor

set -e

echo "[+] Setting up Redis Monitor..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs/redis"
CONFIG_DIR="$PROJECT_ROOT/config/redis"

# Create required directories
echo "Creating directories..."
mkdir -p "$LOG_DIR"
mkdir -p "$CONFIG_DIR"

# Install required Python packages
echo "Installing Python dependencies..."
pip3 install --user redis psutil

# Make scripts executable
echo "Setting up scripts..."
chmod +x "$SCRIPT_DIR/monitor_redis.py"
chmod +x "$SCRIPT_DIR/start_redis_monitor.sh"
chmod +x "$SCRIPT_DIR/stop_redis_monitor.sh"

# Create a sample configuration if it doesn't exist
if [ ! -f "$CONFIG_DIR/redis-monitor.env" ]; then
    echo "Creating sample configuration..."
    cat > "$CONFIG_DIR/redis-monitor.env" << 'EOL'
# Redis Monitor Configuration

# Redis connection settings
REDIS_HOST=localhost
REDIS_PORT=6379
# REDIS_PASSWORD=your_password  # Uncomment and set if using password

# Monitoring settings
MONITOR_INTERVAL=60  # seconds
LOG_LEVEL=INFO

# Alert thresholds (adjust as needed)
MEMORY_USAGE_THRESHOLD_MB=1024  # Alert if memory usage exceeds this value in MB
CLIENTS_THRESHOLD=100          # Alert if connected clients exceed this number
LATENCY_THRESHOLD_MS=100       # Alert if latency exceeds this value in ms
EOL
    echo "Configuration created: $CONFIG_DIR/redis-monitor.env"
fi

echo -e "\n[+] Redis Monitor setup complete!"
echo "To start monitoring:"
echo "  $SCRIPT_DIR/start_redis_monitor.sh"
echo "To stop monitoring:"
echo "  $SCRIPT_DIR/stop_redis_monitor.sh"
echo "\nLogs will be written to: $LOG_DIR/"

exit 0
