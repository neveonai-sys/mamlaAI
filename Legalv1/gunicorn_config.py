"""
Gunicorn configuration for production deployment
"""
import multiprocessing
import os

# Server socket
# BACKEND_PORT env var set by start_backend.sh (8000 prod, 8100 dev)
bind = f"0.0.0.0:{os.getenv('BACKEND_PORT', '8000')}"
backlog = 2048

# Worker processes
# GUNICORN_WORKERS / GUNICORN_WORKER_CONNECTIONS override via env (useful to limit dev)
workers = int(os.getenv('GUNICORN_WORKERS', '8'))  # 2-4 x CPU cores recommended
worker_class = 'gevent'
worker_connections = int(os.getenv('GUNICORN_WORKER_CONNECTIONS', '1000'))
max_requests = 1000  # Restart workers after N requests (prevents memory leaks)
max_requests_jitter = 50  # Add randomness to prevent all workers restarting at once
timeout = 300  # 5 minutes for long AI processing tasks
graceful_timeout = 30
keepalive = 2

# Logging
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Access log — TimedRotatingFileHandler rotates at midnight, appending .YYYY-MM-DD suffix
accesslog = os.path.join(LOG_DIR, 'gunicorn-access.log')
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(D)s'  # IP, request, status, bytes, time

# Error log — use stderr so errors go to backend.log (captured by nohup in start_backend.sh)
errorlog = '-'
loglevel = 'warning'

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

# Log rotation — TimedRotatingFileHandler rotates access log nightly
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
        # stderr handler — errors bubble here → captured by nohup to backend.log
        'error_console': {
            'class': 'logging.StreamHandler',
            'formatter': 'generic',
            'stream': 'ext://sys.stderr',
        },
        'access_file': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'generic',
            'filename': os.path.join(LOG_DIR, 'gunicorn-access.log'),
            'when': 'midnight',
            'interval': 1,
            'backupCount': 90,
        },
    },
    # Override CONFIG_DEFAULTS root so it doesn't reference the removed 'console' handler.
    # WARNING+ goes to stderr (→ backend.log via nohup redirect).
    'root': {
        'level': 'WARNING',
        'handlers': ['error_console'],
    },
    'loggers': {
        'gunicorn.error': {
            'handlers': [],
            'level': 'WARNING',
            'propagate': True,  # bubbles to root → stderr → backend.log
        },
        'gunicorn.access': {
            'handlers': ['access_file'],
            'level': 'INFO',
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
