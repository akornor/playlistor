web: gunicorn audible.wsgi
worker: REMAP_SIGTERM=SIGQUIT celery -A audible worker -l info