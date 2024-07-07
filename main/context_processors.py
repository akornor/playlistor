from django.conf import settings

from .utils import generate_auth_token, get_version


def default_context(request):
    token = generate_auth_token()
    version = get_version()
    return {"APPLE_DEVELOPER_TOKEN": token, "DEBUG": settings.DEBUG, "VERSION": version}
