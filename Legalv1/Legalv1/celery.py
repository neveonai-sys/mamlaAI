from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from kombu import Exchange, Queue

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Legalv1.settings')

# Initialize Celery application
app = Celery('Legalv1')

app.conf.update(
    worker_concurrency=10  # Default; overridden per worker via --concurrency CLI arg
)

# Load task modules from all registered Django app configs.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Autodiscover tasks in apps
app.autodiscover_tasks()

# Define your queues properly using kombu.Queue
app.conf.task_queues = (
    Queue("celery", Exchange("celery"), routing_key="celery"),
    Queue("audio_processing", Exchange("audio_processing"), routing_key="audio_processing"),
    Queue("ecourts_realtime", Exchange("ecourts_realtime"), routing_key="ecourts.realtime"),
    Queue("ecourts_background", Exchange("ecourts_background"), routing_key="ecourts.background"),
)

# Optional defaults
app.conf.task_default_queue = "celery"
app.conf.task_default_exchange = "celery"
app.conf.task_default_routing_key = "celery"

# Optionally define default queue
app.conf.task_default_queue = "celery"

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
