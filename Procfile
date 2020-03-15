web: gunicorn playlistor.wsgi
worker: REMAP_SIGTERM=SIGQUIT celery -A playlistor worker -l info