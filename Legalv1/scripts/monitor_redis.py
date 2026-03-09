#!/usr/bin/env python3
"""
Redis Monitor for LegalV1

Monitors Redis server health and performance metrics.
"""

import os
import time
import logging
import argparse
import redis
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.expanduser('~/redis_monitor.log'))
    ]
)
logger = logging.getLogger('redis-monitor')

class RedisMonitor:
    def __init__(self, host='localhost', port=6379, password=None):
        """Initialize Redis connection."""
        self.redis = redis.Redis(
            host=host,
            port=port,
            password=password,
            socket_timeout=5,
            socket_connect_timeout=5,
            decode_responses=True
        )
        self.metrics = {}

    def check_connection(self):
        """Check if Redis is reachable."""
        try:
            return self.redis.ping()
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            return False

    def collect_metrics(self):
        """Collect and log Redis metrics."""
        try:
            info = self.redis.info('all')
            self.metrics = {
                'timestamp': datetime.now().isoformat(),
                'memory': {
                    'used_memory': info.get('used_memory', 0),
                    'used_memory_rss': info.get('used_memory_rss', 0),
                    'used_memory_peak': info.get('used_memory_peak', 0),
                    'mem_fragmentation_ratio': info.get('mem_fragmentation_ratio', 0),
                },
                'clients': {
                    'connected_clients': info.get('connected_clients', 0),
                    'blocked_clients': info.get('blocked_clients', 0),
                },
                'stats': {
                    'total_connections_received': info.get('total_connections_received', 0),
                    'total_commands_processed': info.get('total_commands_processed', 0),
                    'instantaneous_ops_per_sec': info.get('instantaneous_ops_per_sec', 0),
                }
            }
            logger.info(f"Collected metrics: {self.metrics}")
            return True
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Redis Monitor')
    parser.add_argument('--host', default='localhost', help='Redis host')
    parser.add_argument('--port', type=int, default=6379, help='Redis port')
    parser.add_argument('--interval', type=int, default=60, help='Check interval in seconds')
    
    args = parser.parse_args()
    
    monitor = RedisMonitor(host=args.host, port=args.port)
    
    if not monitor.check_connection():
        logger.error("Failed to connect to Redis. Exiting.")
        return 1
    
    logger.info(f"Starting Redis monitor. Checking every {args.interval} seconds.")
    
    try:
        while True:
            monitor.collect_metrics()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        logger.info("Redis monitor stopped by user")
    except Exception as e:
        logger.error(f"Redis monitor failed: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
