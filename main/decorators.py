import os
from django.conf import settings
from django.contrib.auth.decorators import user_passes_test

TOKEN = os.path.join(settings.BASE_DIR, 'token.json')

def login_required(function=None, redirect_field_name=None, login_url=None):
    """
    Decorator for views that checks that access token is present, redirecting
    to the log-in page if necessary.
    """
    actual_decorator = user_passes_test(
        lambda u: os.path.exists(TOKEN),
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator