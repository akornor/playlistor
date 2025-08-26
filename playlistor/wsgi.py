from gevent import monkey

monkey.patch_all()


import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "playlistor.prod_settings")

application = get_wsgi_application()
