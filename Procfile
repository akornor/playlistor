web: python3 manage.py runserver
worker: REMAP_SIGTERM=SIGQUIT celery -A playlistor worker -l info -P gevent -c 50
redis: redis-server
