"""
Gunicorn configuration for production deployment
Includes log rotation to prevent disk space issues
"""
import multiprocessing
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = 8  # 2-4 x CPU cores recommended
worker_class = 'gevent'
worker_connections = 1000
max_requests = 1000  # Restart workers after N requests (prevents memory leaks)
max_requests_jitter = 50  # Add randomness to prevent all workers restarting at once
timeout = 300  # 5 minutes for long AI processing tasks
graceful_timeout = 30
keepalive = 2

# Logging
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

now_date_str = datetime.now().strftime('%d-%m-%Y')

# Access log with rotation - simplified format for performance
accesslog = os.path.join(LOG_DIR, f'{now_date_str}_gunicorn-access.log')
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(D)s'  # Minimal format: IP, request, status, bytes, time

# Error log with rotation
errorlog = os.path.join(LOG_DIR, f'{now_date_str}_gunicorn-error.log')
loglevel = 'warning'  # Only warnings and errors (not INFO - reduces log volume)

# Process naming
proc_name = 'mamla_ai_gunicorn'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed - commented out by default)
# keyfile = '/path/to/ssl/key.pem'
# certfile = '/path/to/ssl/cert.pem'

# Log rotation configuration
logconfig_dict = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'generic': {
            'format': '[%(asctime)s] [%(process)d] [%(levelname)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
            'class': 'logging.Formatter'
        },
    },
    'handlers': {
        'error_file': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'generic',
            'filename': os.path.join(LOG_DIR, f'{now_date_str}_gunicorn-error.log'),
            'when': 'midnight',
            'interval': 1,
            'backupCount': 3,  # Keep only 3 days of logs
        },
        'access_file': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'generic',
            'filename': os.path.join(LOG_DIR, f'{now_date_str}_gunicorn-access.log'),
            'when': 'midnight',
            'interval': 1,
            'backupCount': 3,  # Keep only 3 days of logs
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'generic',
        },
    },
    'loggers': {
        'gunicorn.error': {
            'handlers': ['error_file'],  # No console in production (performance)
            'level': 'WARNING',  # Only warnings and errors
            'propagate': False,
        },
        'gunicorn.access': {
            'handlers': ['access_file'],
            'level': 'INFO',  # Keep access logs at INFO (useful for analytics)
            'propagate': False,
        },
    },
}

def on_starting(server):
    """Called just before the master process is initialized."""
    print(f"🚀 Starting Gunicorn with {workers} workers on {bind}")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    print("🔄 Reloading Gunicorn workers...")

def when_ready(server):
    """Called just after the server is started."""
    print("✅ Gunicorn is ready to handle requests")

def worker_int(worker):
    """Called when a worker is interrupted."""
    print(f"⚠️  Worker {worker.pid} interrupted")

def worker_abort(worker):
    """Called when a worker is aborted."""
    print(f"❌ Worker {worker.pid} aborted")
