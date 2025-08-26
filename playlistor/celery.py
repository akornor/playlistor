from gevent import monkey

monkey.patch_all()

import os

from celery import Celery
from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "playlistor.dev_settings")

app = Celery(
    "playlistor",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    broker_connection_retry_on_startup=True,
)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

if __name__ == "__main__":
    app.start()
