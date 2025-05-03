import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from spotipy.exceptions import SpotifyException

from .base_settings import *


def before_send(event, hint):
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]

        if isinstance(exc_value, SpotifyException):
            if hasattr(exc_value, "http_status") and exc_value.http_status == 404:
                return None

    return event


sentry_sdk.init(
    dsn=get_secret("SENTRY_DSN"),
    integrations=[DjangoIntegration(), CeleryIntegration(), RedisIntegration()],
    before_send=before_send,
)

STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

STATIC_ROOT = os.path.join(BASE_DIR, "static")

DEBUG = False

SECURE_SSL_REDIRECT = True

ALLOWED_HOSTS = ["www.playlistor.io", "playlistor.io"]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}
