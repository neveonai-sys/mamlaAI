# Redis Monitor for LegalV1

A lightweight monitoring solution for Redis instances used in the LegalV1 application.

## Features

- Monitors Redis server health and performance metrics
- Lightweight and low overhead
- Configurable monitoring intervals and alert thresholds
- Logs metrics to file for analysis
- Easy integration with existing start/stop scripts

## Prerequisites

- Python 3.6+
- Redis server running locally
- Redis Python client: `pip install redis`

## Installation

1. Copy the monitoring scripts to your project:
   ```
   Legalv1/scripts/
   ├── monitor_redis.py     # Main monitoring script
   ├── start_redis_monitor.sh  # Start script
   ├── stop_redis_monitor.sh   # Stop script
   └── setup_redis_monitor.sh  # Setup script (first-time setup)
   ```

2. Run the setup script:
   ```bash
   cd Legalv1/scripts
   chmod +x setup_redis_monitor.sh
   ./setup_redis_monitor.sh
   ```

## Usage

### Start Monitoring
```bash
./Legalv1/scripts/start_redis_monitor.sh
```

### Stop Monitoring
```bash
./Legalv1/scripts/stop_redis_monitor.sh
```

### View Logs
```bash
tail -f logs/redis/redis-monitor.log
```

## Integration with Application

The Redis monitor is automatically integrated with the main application's `start.sh` and `stop.sh` scripts.

## Configuration

Edit `config/redis/redis-monitor.env` to adjust settings:

```ini
# Redis connection
REDIS_HOST=localhost
REDIS_PORT=6379
# REDIS_PASSWORD=your_password

# Monitoring
MONITOR_INTERVAL=60  # seconds
LOG_LEVEL=INFO

# Alert thresholds
MEMORY_USAGE_THRESHOLD_MB=1024
CLIENTS_THRESHOLD=100
LATENCY_THRESHOLD_MS=100
```

## Monitoring Metrics

The following metrics are collected:
- Memory usage
- Connected clients
- Blocked clients
- Operations per second
- Memory fragmentation
- And more...

## Troubleshooting

1. **Monitor not starting**
   - Check if Redis is running: `redis-cli ping`
   - Check logs: `tail -f logs/redis/redis-monitor.log`

2. **Permission issues**
   - Make scripts executable: `chmod +x Legalv1/scripts/*.sh`
   - Ensure write permissions to log directory

3. **High resource usage**
   - Increase the monitoring interval
   - Reduce log verbosity (set LOG_LEVEL=WARNING)

## License

This project is part of the LegalV1 application.
