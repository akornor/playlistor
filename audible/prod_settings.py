from .base import *
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration

sentry_sdk.init(
    dsn="https://64ae31e5d23d451a8ebdf9762ac89b4b@sentry.io/1265770",
    integrations=[DjangoIntegration(), CeleryIntegration(), RedisIntegration()]
)

STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

DEBUG = False

SECURE_SSL_REDIRECT = True

ALLOWED_HOSTS = ['*']